# mobile_api.py
# ─────────────────────────────────────────────────────────────────────────────
# Authenticated API for the Hello Tabeeb Flutter mobile app.
#
# This blueprint is the SERVER-SIDE replacement for the code paths that used to
# live in the Flutter client and required client-held secrets:
#   • Brevo transactional email  (was: brevo_api_key from Remote Config)
#   • Google Drive uploads        (was: service-account key bundled in the app)
#
# Every route requires a valid Firebase ID token (and App Check attestation),
# is rate-limited per user, uses a FIXED sender + FIXED templates, and never
# returns any secret. It is NOT a generic email/file relay.
#
# All secrets (BREVO_API_KEY, SERVICE_ACCOUNT_KEY) stay in server environment.
# ─────────────────────────────────────────────────────────────────────────────

import io
import re
import json
import logging
from datetime import datetime
from html import escape

from flask import Blueprint, request, jsonify, g, current_app
from firebase_admin import firestore

from . import db, drive_service
from .auth_guards import require_app_auth, rate_limit

# Reuse the tested Barefruit order helpers so the mobile order path shares the
# exact same catalog pricing, Drive upload, Firestore schema and admin email
# as the website order path.
from .barefruit import (
    ORDERS_COLLECTION,
    ADMIN_EMAIL as BAREFRUIT_ADMIN_EMAIL,
    _validate_and_price_items,
    _admin_order_email,
    _new_token,
    _send_email as _barefruit_send_email,
)

try:
    from brevo_python import (
        Configuration,
        ApiClient,
        TransactionalEmailsApi,
        SendSmtpEmail,
    )
    from brevo_python.rest import ApiException
except Exception:  # pragma: no cover
    Configuration = ApiClient = TransactionalEmailsApi = SendSmtpEmail = None
    ApiException = Exception

logger = logging.getLogger(__name__)

mobile_api = Blueprint("mobile_api", __name__, url_prefix="/api/mobile")

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG (senders/recipients are server-defined — the client cannot set them)
# ─────────────────────────────────────────────────────────────────────────────

import os

# Node/Express verification server that handles the emailed Verify/Reject links.
VERIFY_SERVER_BASE_URL = (
    os.getenv("VERIFY_SERVER_BASE_URL") or "https://verify.captain.hellotabeeb.pk"
).strip().rstrip("/")

LAB_SENDER = {"name": "HelloTabeeb Lab Services", "email": "support@hellotabeeb.com"}
LAB_ALERT_SENDER = {"name": "HelloTabeeb Alerts", "email": "support@hellotabeeb.com"}
LAB_SUPPORT_REPLY_TO = {"email": "support@hellotabeeb.com", "name": "HelloTabeeb Support"}
FREE_CONSULT_ALERT_EMAIL = "shahzad892@gmail.com"

DOCTOR_VERIFICATION_SENDER = {"name": "HelloTabeeb Verification", "email": "noreply@hellotabeeb.com"}
DOCTOR_ADMIN_EMAIL = "hellotabeeb@gmail.com"
DOCTOR_ADMIN_NAME = "HelloTabeeb"

MAX_PRESCRIPTION_BYTES = 10 * 1024 * 1024  # 10 MB safety cap
PRESCRIPTION_FOLDER = "lab test prescription from android app"

# Drive folders the app is allowed to upload profile/credential files into.
# The client may only target one of these known folders (no arbitrary folders).
ALLOWED_PROFILE_FOLDERS = {
    "patient profile images - hellotabeeb",
    "doctor profile images - hellotabeeb",
    "doctor credentials - hellotabeeb",
}

_ALLOWED_UPLOAD_MIMES = (
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ─────────────────────────────────────────────────────────────────────────────
# EMAIL / DRIVE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _brevo_client():
    api_key = os.getenv("BREVO_API_KEY")
    if not api_key or Configuration is None:
        logger.warning("Brevo unavailable (missing key or library) — email disabled.")
        return None
    cfg = Configuration()
    cfg.api_key["api-key"] = api_key
    return TransactionalEmailsApi(ApiClient(cfg))


def _send_email(sender, to, subject, html_content, reply_to=None):
    """Send one transactional email. Never raises (email is best-effort)."""
    api = _brevo_client()
    if api is None:
        logger.warning("Email NOT sent (no Brevo client): %s", subject)
        return False
    try:
        payload = SendSmtpEmail(
            to=to,
            sender=sender,
            subject=subject,
            html_content=html_content,
            reply_to=reply_to or {"email": sender["email"], "name": sender["name"]},
        )
        api.send_transac_email(payload)
        return True
    except ApiException as exc:  # pragma: no cover
        logger.error("Brevo API error sending '%s': %s", subject, exc)
    except Exception as exc:  # pragma: no cover
        logger.error("Unexpected error sending '%s': %s", subject, exc)
    return False


def _get_or_create_folder(folder_name):
    query = (
        f"name='{folder_name}' and "
        "mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    resp = drive_service.files().list(q=query, spaces="drive", fields="files(id)").execute()
    files = resp.get("files", [])
    if files:
        return files[0]["id"]
    folder = drive_service.files().create(
        body={"name": folder_name, "mimeType": "application/vnd.google-apps.folder"},
        fields="id",
    ).execute()
    return folder["id"]


def _upload_file_to_drive(file_storage, folder_name, base_name, max_bytes):
    """Upload a file to a dedicated Drive folder using the server service account.

    Keeps the existing "anyone with the link can read" behaviour so staff can
    open the file from the notification emails exactly as before.
    Returns the shareable webViewLink."""
    from googleapiclient.http import MediaIoBaseUpload
    from werkzeug.utils import secure_filename

    data = file_storage.read()
    if not data:
        raise ValueError("Empty file")
    if len(data) > max_bytes:
        raise ValueError("File is too large.")

    folder_id = _get_or_create_folder(folder_name)
    mime = file_storage.mimetype or "application/octet-stream"
    ext = (mime.split("/")[-1] or "bin").split(";")[0]
    safe_base = secure_filename(base_name or "upload") or "upload"
    fname = secure_filename(f"{safe_base}_{int(datetime.utcnow().timestamp())}.{ext}")

    media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime, resumable=False)
    created = drive_service.files().create(
        body={"name": fname, "parents": [folder_id]},
        media_body=media,
        fields="id, webViewLink",
    ).execute()

    file_id = created["id"]
    try:
        drive_service.permissions().create(
            fileId=file_id, body={"type": "anyone", "role": "reader"}
        ).execute()
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not set public permission on %s: %s", file_id, exc)

    return created.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view"


# ─────────────────────────────────────────────────────────────────────────────
# LAB EMAIL TEMPLATES  (ported verbatim from the old Flutter client so the
# emails look identical to what users received before)
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_rs(value):
    try:
        return f"Rs. {float(value):.0f}"
    except (TypeError, ValueError):
        return ""


def _lab_confirmation_html(name, test_names, test_fees, lab_name, discount_code,
                           has_consultation, chief_complaint):
    rows = []
    for i, tname in enumerate(test_names):
        fee = _fmt_rs(test_fees[i]) if i < len(test_fees) else ""
        rows.append(
            f"""
        <tr>
          <td style="padding: 10px; border-bottom: 1px solid #e2e8f0;">{escape(str(tname).strip())}</td>
          <td style="padding: 10px; text-align: right; border-bottom: 1px solid #e2e8f0;">{fee}</td>
        </tr>
      """
        )
    test_rows = "".join(rows)

    total = 0.0
    for f in test_fees:
        try:
            total += float(f)
        except (TypeError, ValueError):
            pass

    consultation_section = ""
    if has_consultation:
        symptom_html = (
            f'<p style="margin:8px 0 0; font-size:13px; color:#4a5568;"><strong>Your Symptoms:</strong> {escape(chief_complaint)}</p>'
            if chief_complaint else ""
        )
        consultation_section = f"""
        <div style="margin: 20px 0; background-color: #f0fff4; padding: 15px; border-radius: 6px; border-left: 4px solid #27ae60;">
          <p style="margin: 0; font-size: 15px; font-weight: bold; color: #27ae60;">FREE Doctor Consultation Included!</p>
          <p style="margin: 8px 0 0; font-size: 13px; color: #4a5568;">A doctor will review your test results and provide personalized advice — worth Rs. 1,500 — absolutely FREE with your booking.</p>
          {symptom_html}
        </div>
        """

    is_na = discount_code == "N/A"
    discount_section = "" if is_na else f"""
        <div style="margin: 20px 0; background-color: #fff8f8; padding: 15px; border-radius: 6px; border-left: 4px solid #ff3333; text-align: center;">
          <p style="margin: 0; font-size: 16px;">Your Discount Code</p>
          <p style="font-size: 24px; font-weight: bold; margin: 10px 0; color: #ff3333; letter-spacing: 2px;">{escape(discount_code)}</p>
        </div>
        """
    show_at_lab = "" if is_na else """
        <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee;">
          <p style="color: #666; font-size: 14px;">Show this mail at the Lab during your visit or home sampling to avail discount</p>
        </div>
        """

    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
      <div style="padding: 20px;">
        <h2 style="color: #333; font-size: 20px; margin-bottom: 20px; font-weight: normal;">Lab Test Booking Confirmation</h2>
        <p>Dear {escape(name)},</p>
        <p>Thank you for booking your lab test with HelloTabeeb. Your booking has been confirmed.</p>
        <div style="margin: 30px 0; background-color: #f8f9fa; padding: 15px; border-radius: 6px;">
          <h3 style="color: #333; font-size: 16px; margin-bottom: 15px;">Booking Details:</h3>
          <table style="width: 100%; border-collapse: collapse; background-color: #ffffff; border-radius: 4px;">
            <thead>
              <tr style="background-color: #edf2f7;">
                <th style="padding: 12px; text-align: left; border-bottom: 2px solid #e2e8f0;">Test</th>
                <th style="padding: 12px; text-align: right; border-bottom: 2px solid #e2e8f0;">Fee</th>
              </tr>
            </thead>
            <tbody>
              {test_rows}
              <tr style="background-color: #edf2f7; font-weight: bold;">
                <td style="padding: 12px;">Total</td>
                <td style="padding: 12px; text-align: right;">Rs. {total:.0f}</td>
              </tr>
            </tbody>
          </table>
        </div>
        {consultation_section}
        {discount_section}
        <p>Your lab test is booked with {escape(lab_name)}</p>
        <div style="margin: 30px 0;">
          <a href="#" style="display: inline-block; background-color: #2f3e4e; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; font-weight: bold;">Book Again</a>
        </div>
        <p>For support or to Book Home sampling, please call us at</p>
        <p style="font-size: 18px; font-weight: bold; margin: 15px 0;">0337 4373334</p>
        <p>Thank You!</p>
        {show_at_lab}
      </div>
    </body>
    </html>
    """


def _free_consult_alert_html(payload, discount_code):
    def row(label, value):
        return (
            f'<tr><td style="padding: 8px; border: 1px solid #e2e8f0;">{escape(label)}</td>'
            f'<td style="padding: 8px; border: 1px solid #e2e8f0;">{escape(str(value))}</td></tr>'
        )

    chief = payload.get("chiefComplaint") or ""
    symptom_text = chief if chief else "Not provided"
    home_sampling = "Yes" if payload.get("isHomeSampling") else "No"
    address = payload.get("fullAddress") or ""
    address_text = address if address else "Not provided"
    lat = payload.get("latitude")
    lng = payload.get("longitude")
    if lat is not None and lng is not None:
        try:
            location_text = f"{float(lat):.5f}, {float(lng):.5f}"
        except (TypeError, ValueError):
            location_text = "Not available"
    else:
        location_text = "Not available"

    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
      <h2 style="margin-bottom: 8px;">Free Consultation Request</h2>
      <p style="margin-top: 0;">A new free doctor consultation request was booked.</p>
      <table style="width: 100%; border-collapse: collapse;">
        {row('Name', payload.get('name', ''))}
        {row('Email', payload.get('email', ''))}
        {row('Phone', payload.get('phone', ''))}
        {row('Lab', payload.get('labName', ''))}
        {row('Tests', ', '.join(payload.get('testNames') or []))}
        {row('Total', 'Rs. ' + str(payload.get('totalFee', '')))}
        {row('Symptoms', symptom_text)}
        {row('Home Sampling', home_sampling)}
        {row('Address', address_text)}
        {row('Location', location_text)}
        {row('Discount Code', discount_code)}
      </table>
    </body>
    </html>
    """


# ─────────────────────────────────────────────────────────────────────────────
# DOCTOR VERIFICATION EMAIL TEMPLATE (ported from the old Flutter client)
# ─────────────────────────────────────────────────────────────────────────────

def _doctor_email_html(doc, verify_url, reject_url):
    def row(label, value):
        if value is None or value == "":
            return ""
        return f"""
        <tr>
          <td style="padding:10px 14px;font-weight:600;color:#4a5568;white-space:nowrap;border-bottom:1px solid #edf2f7;">{escape(str(label))}</td>
          <td style="padding:10px 14px;color:#1a202c;border-bottom:1px solid #edf2f7;">{escape(str(value))}</td>
        </tr>"""

    def link_row(label, url):
        if not url:
            return ""
        return f"""
        <tr>
          <td style="padding:10px 14px;font-weight:600;color:#4a5568;white-space:nowrap;border-bottom:1px solid #edf2f7;">{escape(str(label))}</td>
          <td style="padding:10px 14px;border-bottom:1px solid #edf2f7;">
            <a href="{escape(str(url))}" style="color:#2b6cb0;text-decoration:underline;">View File</a>
          </td>
        </tr>"""

    full_name = f"{doc.get('prefix') or ''} {doc.get('fullName') or ''}".strip()
    rows = "".join([
        row("Full Name", full_name),
        row("Email", doc.get("email")),
        row("PMDC Number", doc.get("pmdcNumber")),
        row("Specialization", doc.get("specialization")),
        row("Issuing Authority", doc.get("issuingAuthority")),
        row("Years of Experience", doc.get("yearsOfExperience")),
        row("Clinic / Hospital", doc.get("clinicName")),
        row("City", doc.get("city")),
        row("Address", doc.get("address")),
        row("Auth Provider", doc.get("authProvider") or "email"),
        link_row("Profile Photo", doc.get("profileImageUrl")),
        link_row("Credentials", doc.get("credentialsFileUrl") or doc.get("credentialsUrl")),
    ])

    return f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f7fafc;font-family:'Segoe UI',Roboto,Arial,sans-serif;">
  <div style="max-width:640px;margin:30px auto;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
    <div style="background:linear-gradient(135deg,#193F6C 0%,#2E7DD1 50%,#4782DE 100%);padding:32px 28px;text-align:center;">
      <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:700;letter-spacing:0.5px;">New Doctor Verification Request</h1>
      <p style="margin:8px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">A new doctor has registered on HelloTabeeb and is awaiting your review.</p>
    </div>
    <div style="padding:28px;">
      <h2 style="margin:0 0 16px;font-size:17px;color:#193F6C;font-weight:600;">Doctor Details</h2>
      <table style="width:100%;border-collapse:collapse;font-size:14px;line-height:1.6;">
        {rows}
      </table>
    </div>
    <div style="padding:0 28px 36px;text-align:center;">
      <p style="font-size:14px;color:#718096;margin-bottom:20px;">Please review the details above and take an action:</p>
      <a href="{escape(verify_url)}" style="display:inline-block;padding:14px 40px;background:linear-gradient(135deg,#27ae60,#2ecc71);color:#ffffff;font-size:15px;font-weight:700;text-decoration:none;border-radius:50px;margin:0 8px 12px;box-shadow:0 4px 14px rgba(39,174,96,0.35);">
        &#10004;&nbsp; Verify Doctor
      </a>
      <a href="{escape(reject_url)}" style="display:inline-block;padding:14px 40px;background:linear-gradient(135deg,#c0392b,#e74c3c);color:#ffffff;font-size:15px;font-weight:700;text-decoration:none;border-radius:50px;margin:0 8px 12px;box-shadow:0 4px 14px rgba(231,76,60,0.35);">
        &#10008;&nbsp; Reject Verification
      </a>
    </div>
    <div style="background:#f7fafc;padding:18px 28px;text-align:center;border-top:1px solid #edf2f7;">
      <p style="margin:0;font-size:12px;color:#a0aec0;">HelloTabeeb &mdash; Doctor Verification System</p>
    </div>
  </div>
</body>
</html>
"""


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@mobile_api.route("/health", methods=["GET"])
@require_app_auth
def mobile_health():
    return jsonify(success=True, uid=g.uid, appCheck=g.app_check_verified)


# ── Lab: prescription upload → Google Drive (server service account) ─────────
@mobile_api.route("/lab/prescription", methods=["POST"])
@require_app_auth
@rate_limit(max_calls=30, window_seconds=3600)
def lab_prescription_upload():
    file = request.files.get("file")
    if file is None or not file.filename:
        return jsonify(success=False, message="No file provided."), 400
    if not (file.mimetype or "").startswith(("image/", "application/pdf")) \
            and file.mimetype not in (
                "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ):
        return jsonify(success=False, message="Unsupported file type."), 400

    patient_name = (request.form.get("patientName") or "prescription").strip()
    try:
        url = _upload_file_to_drive(
            file, PRESCRIPTION_FOLDER, patient_name, MAX_PRESCRIPTION_BYTES
        )
    except ValueError as ve:
        return jsonify(success=False, message=str(ve)), 400
    except Exception as exc:
        logger.exception("Prescription upload failed for uid=%s: %s", g.uid, exc)
        return jsonify(success=False, message="Upload failed. Please try again."), 502

    logger.info("Prescription uploaded by uid=%s", g.uid)
    return jsonify(success=True, url=url)


# ── Profile / credentials upload → Google Drive (server service account) ─────
@mobile_api.route("/profile/upload", methods=["POST"])
@require_app_auth
@rate_limit(max_calls=30, window_seconds=3600)
def profile_upload():
    file = request.files.get("file")
    if file is None or not file.filename:
        return jsonify(success=False, message="No file provided."), 400

    folder = (request.form.get("folder") or "").strip()
    if folder not in ALLOWED_PROFILE_FOLDERS:
        return jsonify(success=False, message="Invalid upload target."), 400

    mimetype = file.mimetype or ""
    if not (mimetype.startswith("image/") or mimetype in _ALLOWED_UPLOAD_MIMES):
        return jsonify(success=False, message="Unsupported file type."), 400

    base_name = (request.form.get("fileName") or "upload").strip()
    try:
        url = _upload_file_to_drive(file, folder, base_name, MAX_PRESCRIPTION_BYTES)
    except ValueError as ve:
        return jsonify(success=False, message=str(ve)), 400
    except Exception as exc:
        logger.exception("Profile upload failed for uid=%s: %s", g.uid, exc)
        return jsonify(success=False, message="Upload failed. Please try again."), 502

    logger.info("Profile file uploaded by uid=%s to '%s'", g.uid, folder)
    return jsonify(success=True, url=url)


# ── Lab: booking confirmation email (customer) + optional internal alert ─────
@mobile_api.route("/lab/booking-confirmation", methods=["POST"])
@require_app_auth
@rate_limit(max_calls=40, window_seconds=3600)
def lab_booking_confirmation():
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    lab_name = (data.get("labName") or "").strip()
    discount_code = (data.get("discountCode") or "N/A").strip() or "N/A"
    test_names = data.get("testNames") or []
    test_fees = data.get("testFees") or []
    has_consultation = bool(data.get("has12PercentWithConsultation"))
    chief_complaint = (data.get("chiefComplaint") or "").strip()

    if not name or not _EMAIL_RE.match(email):
        return jsonify(success=False, message="Invalid booking payload."), 400
    if not isinstance(test_names, list) or not isinstance(test_fees, list):
        return jsonify(success=False, message="Invalid test data."), 400
    if len(test_names) > 100:
        return jsonify(success=False, message="Too many tests."), 400

    # 1) Customer confirmation (fixed sender + fixed template).
    html = _lab_confirmation_html(
        name, test_names, test_fees, lab_name, discount_code,
        has_consultation, chief_complaint,
    )
    _send_email(
        LAB_SENDER,
        [{"email": email, "name": name}],
        "Lab Test Booking Confirmation",
        html,
        reply_to=LAB_SUPPORT_REPLY_TO,
    )

    # 2) Internal free-consultation alert (only when applicable).
    if has_consultation:
        alert_html = _free_consult_alert_html(data, discount_code)
        _send_email(
            LAB_ALERT_SENDER,
            [{"email": FREE_CONSULT_ALERT_EMAIL, "name": "Shahzad"}],
            "Free Consultation Request",
            alert_html,
            reply_to=LAB_SUPPORT_REPLY_TO,
        )

    logger.info("Booking confirmation email queued by uid=%s", g.uid)
    return jsonify(success=True)


# ── Doctor: send verification request email to admin ─────────────────────────
@mobile_api.route("/doctor/verification-request", methods=["POST"])
@require_app_auth
@rate_limit(max_calls=10, window_seconds=3600)
def doctor_verification_request():
    # The caller can only trigger the email for THEIR OWN uid. The doctor
    # details + verification token are read from Firestore (authoritative),
    # never trusted from the client.
    uid = g.uid

    doc_data = None
    for collection in ("doctors", "newDoctorRegistration"):
        snap = db.collection(collection).document(uid).get()
        if snap.exists:
            doc_data = snap.to_dict()
            break

    if not doc_data:
        logger.warning("Doctor verification requested but no doc for uid=%s", uid)
        return jsonify(success=False, message="Doctor record not found."), 404

    token = doc_data.get("verificationToken")
    if not token:
        logger.warning("Doctor doc for uid=%s has no verificationToken", uid)
        return jsonify(success=False, message="Verification token missing."), 409

    from urllib.parse import urlencode
    verify_url = f"{VERIFY_SERVER_BASE_URL}/handleDoctorVerification?" + urlencode(
        {"uid": uid, "token": token, "action": "verify"}
    )
    reject_url = f"{VERIFY_SERVER_BASE_URL}/handleDoctorVerification?" + urlencode(
        {"uid": uid, "token": token, "action": "reject"}
    )

    doctor_name = doc_data.get("fullName") or "Unknown Doctor"
    html = _doctor_email_html(doc_data, verify_url, reject_url)
    _send_email(
        DOCTOR_VERIFICATION_SENDER,
        [{"email": DOCTOR_ADMIN_EMAIL, "name": DOCTOR_ADMIN_NAME}],
        f"New Doctor Verification Request — {doctor_name}",
        html,
        reply_to={"email": "noreply@hellotabeeb.com", "name": "HelloTabeeb"},
    )

    logger.info("Doctor verification email queued for uid=%s", uid)
    return jsonify(success=True)


# ── Barefruit: place order (upload screenshot + create order + email admin) ──
@mobile_api.route("/barefruit/place-order", methods=["POST"])
@require_app_auth
@rate_limit(max_calls=15, window_seconds=3600)
def barefruit_place_order():
    # Reuse the exact website order pipeline: prices are recomputed from the
    # server-side catalog, tokens are generated server-side, the screenshot is
    # uploaded with the server service account, and the admin email is sent.
    from .barefruit import _upload_screenshot_to_drive

    raw_items = request.form.get("items")
    try:
        parsed_items = json.loads(raw_items) if raw_items else None
    except (TypeError, ValueError):
        return jsonify(success=False, message="Invalid cart data."), 400

    try:
        items, subtotal, total_items = _validate_and_price_items(parsed_items)
    except ValueError as ve:
        return jsonify(success=False, message=str(ve)), 400

    customer = _validate_mobile_customer(request.form)
    if isinstance(customer, tuple):  # (error_message,)
        return jsonify(success=False, message=customer[0]), 400

    screenshot = request.files.get("screenshot")
    if screenshot is None or not screenshot.filename:
        return jsonify(success=False, message="Please attach your payment screenshot."), 400
    if not (screenshot.mimetype or "").startswith("image/"):
        return jsonify(success=False, message="Screenshot must be an image."), 400

    try:
        screenshot_url = _upload_screenshot_to_drive(screenshot, customer["name"] or "order")
    except ValueError as ve:
        return jsonify(success=False, message=str(ve)), 400
    except Exception as exc:
        logger.error("Mobile screenshot upload failed for uid=%s: %s", g.uid, exc)
        return jsonify(success=False, message="Could not upload the payment screenshot. Please try again."), 502

    order = {
        "status": "pending",
        "items": items,
        "subtotal": subtotal,
        "totalItems": total_items,
        "customerName": customer["name"],
        "customerEmail": customer["email"],
        "customerPhone": customer["phone"],
        "city": customer["city"],
        "latitude": customer["latitude"],
        "longitude": customer["longitude"],
        "orderNote": customer["note"],
        "paymentScreenshotUrl": screenshot_url,
        "adminToken": _new_token(),
        "shipToken": _new_token(),
        "reAcceptToken": _new_token(),
        "rejectionReason": None,
        "source": "mobile",
        "createdByUid": g.uid,
        "createdAt": firestore.SERVER_TIMESTAMP,
    }

    doc_ref = db.collection(ORDERS_COLLECTION).document()
    doc_ref.set(order)
    order_id = doc_ref.id

    _barefruit_send_email(
        [{"email": BAREFRUIT_ADMIN_EMAIL, "name": "HelloTabeeb"}],
        f"New Barefruit Order #{order_id} — PKR {subtotal}",
        _admin_order_email(order_id, order),
    )

    logger.info("Barefruit mobile order %s placed by uid=%s", order_id, g.uid)
    return jsonify(success=True, orderId=order_id)


def _validate_mobile_customer(form):
    """Lenient customer validation for the mobile app (the app already collects
    structured input). Returns a dict, or a 1-tuple with an error message."""
    name = (form.get("name") or "").strip()
    email = (form.get("email") or "").strip()
    phone = re.sub(r"\D", "", (form.get("phone") or "").strip())
    city = (form.get("city") or "").strip()
    note = (form.get("note") or "").strip()

    if not name or len(name) > 80:
        return ("Please enter a valid name.",)
    if not _EMAIL_RE.match(email):
        return ("Please enter a valid email address.",)
    if len(phone) < 7 or len(phone) > 15:
        return ("Please enter a valid phone number.",)
    if not city or len(city) > 60:
        return ("Please select your city.",)
    if len(note) > 1000:
        return ("Order note is too long (max 1000 chars).",)

    lat = form.get("latitude")
    lng = form.get("longitude")
    try:
        latitude = float(lat) if lat not in (None, "") else None
        longitude = float(lng) if lng not in (None, "") else None
    except (TypeError, ValueError):
        latitude = longitude = None

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "city": city,
        "note": note,
        "latitude": latitude,
        "longitude": longitude,
    }
