# barefruit.py
# ─────────────────────────────────────────────────────────────────────────────
# Barefruit Organics storefront + secure email-driven order workflow.
#
# Flow (all state lives in Firestore collection `barefruitOrders`):
#   place  -> status 'pending'  -> email admin (Accept / Reject buttons)
#   accept -> status 'accepted' -> email shipping manager (Order Shipped button)
#   reject -> status 'rejected' -> email customer (reason + support) AND
#                                   email admin a re-accept follow-up (workaround)
#   reaccept (support workaround) -> status 'accepted' -> email shipping manager
#   shipped -> status 'shipped' -> email customer
#
# Security model (mirrors the doctor-verification pattern):
#   * Every capability is a separate high-entropy, single-use token stored on
#     the order document (adminToken / shipToken / reAcceptToken).
#   * Each handler validates BOTH the order status AND a constant-time token
#     comparison before mutating state, then clears the consumed token.
#   * Status guards make every link idempotent and prevent out-of-order actions
#     (e.g. you cannot "ship" an order that was never "accepted").
# ─────────────────────────────────────────────────────────────────────────────

import os
import io
import json
import logging
import secrets
import re
from datetime import datetime
from html import escape

from flask import Blueprint, render_template, request, jsonify, current_app
from firebase_admin import firestore
from werkzeug.utils import secure_filename

from . import db, drive_service

try:
    from brevo_python import (
        Configuration,
        ApiClient,
        TransactionalEmailsApi,
        SendSmtpEmail,
    )
    from brevo_python.rest import ApiException
except Exception:  # pragma: no cover - keeps import safe in minimal envs
    Configuration = ApiClient = TransactionalEmailsApi = SendSmtpEmail = None
    ApiException = Exception

logger = logging.getLogger(__name__)

barefruit = Blueprint("barefruit", __name__)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

ORDERS_COLLECTION = "barefruitOrders"

ADMIN_EMAIL = "hellotabeeb@gmail.com"
SHIPPING_MANAGER_EMAIL = "hellotabeeb.dpt@gmail.com"
SUPPORT_EMAIL = "support@hellotabeeb.com"
SENDER = {"name": "Barefruit Organics", "email": "support@hellotabeeb.com"}

# Base URL the emailed action buttons point at. Override with PUBLIC_BASE_URL
# once the Flask app is deployed (e.g. https://hellotabeeb.pk).
# Trim whitespace/newlines (a stray line break in the env var would otherwise
# be baked into every emailed link and break Brevo's link tracking).
PUBLIC_BASE_URL = (os.getenv("PUBLIC_BASE_URL") or "https://hellotabeeb.pk").strip().rstrip("/")

MAX_SCREENSHOT_BYTES = 6 * 1024 * 1024  # 6 MB
MAX_QTY_PER_ITEM = 99
DRIVE_FOLDER_NAME = "barefruit payment screenshots"

# Random placeholder payment details — replace with the real ones later.
PAYMENT_DETAILS = {
    "bank_name": "Meezan Bank",
    "account_title": "Barefruit Organics",
    "account_number": "0123 4567 8901 234",
    "iban": "PK00 MEZN 0000 0123 4567 8901",
    "easypaisa_jazzcash": "0300 1234567",
}

# Brand palette (matches the Hello Tabeeb / Barefruit color scheme).
BRAND = {
    "navy": "#193F6C",
    "ocean": "#2E7DD1",
    "sky": "#4782DE",
    "green": "#2ECC71",
    "green_dark": "#27ae60",
    "red": "#E74C3C",
    "red_dark": "#c0392b",
}

# Catalog — the single source of truth for prices (never trust the client).
BAREFRUIT_PRODUCTS = [
    {
        "id": "strawberry-jam", "name": "Strawberry Jam", "pack": "250 g", "price": 550,
        "image": "Strawberry jam.jpeg",
        "description": "Made with ripe natural strawberries for a bright, fruity spread. Its balanced sweetness makes breakfast and desserts feel freshly prepared.",
        "ingredients": "Natural Strawberry, Sugar, Lemon Juice, Pectin",
    },
    {
        "id": "orange-marmalade", "name": "Orange Marmalade", "pack": "250 g", "price": 600,
        "image": "orange marmalade.jpeg",
        "description": "Made with natural oranges for a fragrant citrus spread with a lively taste. Enjoy its sunny flavour on toast, pastries, and everyday snacks.",
        "ingredients": "Natural Orange, Sugar, Lemon Juice, Pectin",
    },
    {
        "id": "mango-jam", "name": "Mango Jam", "pack": "250 g", "price": 550,
        "image": "mango jam.jpeg",
        "description": "Made with natural mangoes for a rich tropical taste in every spoonful. It brings a smooth, cheerful fruit flavour to breakfast and baking.",
        "ingredients": "Natural Mango, Sugar, Lemon Juice, Pectin",
    },
    {
        "id": "peach-jam", "name": "Peach Jam", "pack": "250 g", "price": 550,
        "image": "peach jam.jpeg",
        "description": "Made with natural peaches for a soft, aromatic fruit spread. Its gentle sweetness is perfect for toast, yogurt, pastries, and desserts.",
        "ingredients": "Natural Peach, Sugar, Lemon Juice, Pectin",
    },
    {
        "id": "apple-jam", "name": "Apple Jam", "pack": "250 g", "price": 550,
        "image": "Apple Jam.jpeg",
        "description": "Made with natural apples for a comforting spread with a clean fruit taste. It is a delicious choice for toast, sandwiches, and home baking.",
        "ingredients": "Natural Apple, Sugar, Lemon Juice, Pectin",
    },
    {
        "id": "talbina-200g", "name": "Talbina", "pack": "200 g", "price": 900,
        "image": "talbina.jpeg",
        "description": "A wholesome Talbina blend made with barley and Ajwa dates for a nourishing bowl. Prepare it warm with milk or water for a satisfying daily meal.",
        "ingredients": "Milk, Barley Porridge, Raisins, Dates, Almonds, Walnuts",
    },
    {
        "id": "talbina-450g", "name": "Talbina", "pack": "450 g", "price": 1800,
        "image": "talbina.jpeg",
        "description": "A family size Talbina blend made with barley and Ajwa dates for a nourishing bowl. Prepare it warm with milk or water for a satisfying daily meal.",
        "ingredients": "Milk, Barley Porridge, Raisins, Dates, Almonds, Walnuts",
    },
]

PRODUCTS_BY_ID = {p["id"]: p for p in BAREFRUIT_PRODUCTS}

_PHONE_RE = re.compile(r"^03\d{9}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'-]{1,59}$")

# ─────────────────────────────────────────────────────────────────────────────
# BREVO
# ─────────────────────────────────────────────────────────────────────────────

def _brevo_api():
    """Build a Brevo transactional-email client, or None if unavailable."""
    api_key = os.getenv("BREVO_API_KEY")
    if not api_key or Configuration is None:
        logger.warning("Brevo API key/library missing — email disabled.")
        return None
    cfg = Configuration()
    cfg.api_key["api-key"] = api_key
    return TransactionalEmailsApi(ApiClient(cfg))


def _send_email(to, subject, html_content, reply_to=None):
    """Send one transactional email. `to` is a list of {'email','name'} dicts.

    Returns True on success. Never raises — email failure must not break the
    request flow (matches the app's fire-and-forget pattern)."""
    api = _brevo_api()
    if api is None:
        logger.warning("Email NOT sent (no Brevo client): %s -> %s", subject, to)
        return False
    try:
        payload = SendSmtpEmail(
            to=to,
            sender=SENDER,
            subject=subject,
            html_content=html_content,
            reply_to=reply_to or {"email": SENDER["email"], "name": SENDER["name"]},
        )
        api.send_transac_email(payload)
        return True
    except ApiException as exc:  # pragma: no cover
        logger.error("Brevo API error sending '%s': %s", subject, exc)
    except Exception as exc:  # pragma: no cover
        logger.error("Unexpected error sending '%s': %s", subject, exc)
    return False


# ─────────────────────────────────────────────────────────────────────────────
# TOKENS & URLS
# ─────────────────────────────────────────────────────────────────────────────

def _new_token():
    """48-char URL-safe cryptographically-secure single-use token."""
    return secrets.token_urlsafe(36)[:48]


def _action_url(order_id, token, action):
    from urllib.parse import urlencode
    q = urlencode({"orderId": order_id, "token": token, "action": action})
    url = f"{PUBLIC_BASE_URL}/barefruit/action?{q}"
    # Defensive: strip any control characters (newlines/tabs) that would break
    # URL parsing / email link tracking.
    return "".join(ch for ch in url if ch >= " ")


def _tokens_match(stored, provided):
    if not stored or not provided:
        return False
    return secrets.compare_digest(str(stored), str(provided))


# ─────────────────────────────────────────────────────────────────────────────
# GOOGLE DRIVE UPLOAD (payment screenshot)
# ─────────────────────────────────────────────────────────────────────────────

def _get_or_create_drive_folder():
    query = (
        f"name='{DRIVE_FOLDER_NAME}' and "
        "mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    resp = drive_service.files().list(q=query, spaces="drive", fields="files(id)").execute()
    files = resp.get("files", [])
    if files:
        return files[0]["id"]
    folder = drive_service.files().create(
        body={"name": DRIVE_FOLDER_NAME, "mimeType": "application/vnd.google-apps.folder"},
        fields="id",
    ).execute()
    return folder["id"]


def _upload_screenshot_to_drive(file_storage, order_ref_name):
    """Upload the payment screenshot to Drive and return a shareable link."""
    from googleapiclient.http import MediaIoBaseUpload

    data = file_storage.read()
    if not data:
        raise ValueError("Empty file")
    if len(data) > MAX_SCREENSHOT_BYTES:
        raise ValueError("File exceeds 6MB limit")

    folder_id = _get_or_create_drive_folder()
    mime = file_storage.mimetype or "image/jpeg"
    ext = (mime.split("/")[-1] or "jpg").split(";")[0]
    fname = secure_filename(f"{order_ref_name}_{int(datetime.utcnow().timestamp())}.{ext}")

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
        logger.warning("Could not set public permission on screenshot: %s", exc)

    return created.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view"


# ─────────────────────────────────────────────────────────────────────────────
# VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def _validate_and_price_items(raw_items):
    """Validate a client cart against the catalog and re-price server-side.

    `raw_items` is a list of {'id', 'quantity'}. Returns (items, subtotal, total_items)
    or raises ValueError."""
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("Your cart is empty.")

    items = []
    subtotal = 0
    total_items = 0
    seen = set()
    for entry in raw_items:
        if not isinstance(entry, dict):
            raise ValueError("Invalid cart item.")
        pid = str(entry.get("id", "")).strip()
        product = PRODUCTS_BY_ID.get(pid)
        if product is None:
            raise ValueError("One of the selected products is no longer available.")
        if pid in seen:
            raise ValueError("Duplicate product in cart.")
        seen.add(pid)
        try:
            qty = int(entry.get("quantity", 0))
        except (TypeError, ValueError):
            raise ValueError("Invalid quantity.")
        if qty < 1 or qty > MAX_QTY_PER_ITEM:
            raise ValueError(f"Quantity must be between 1 and {MAX_QTY_PER_ITEM}.")
        line_total = product["price"] * qty
        subtotal += line_total
        total_items += qty
        items.append({
            "id": product["id"],
            "name": product["name"],
            "pack": product["pack"],
            "price": product["price"],
            "quantity": qty,
        })
    return items, subtotal, total_items


def _validate_customer(form):
    name = (form.get("name") or "").strip()
    email = (form.get("email") or "").strip()
    phone = re.sub(r"\D", "", (form.get("phone") or "").strip())
    city = (form.get("city") or "").strip()
    note = (form.get("note") or "").strip()

    if not _NAME_RE.match(name):
        raise ValueError("Please enter a valid name (letters only, 2–60 chars).")
    if not _EMAIL_RE.match(email):
        raise ValueError("Please enter a valid email address.")
    if not _PHONE_RE.match(phone):
        raise ValueError("Please enter a valid phone number (03XXXXXXXXX).")
    if not city or len(city) > 60:
        raise ValueError("Please select your city.")
    if len(note) > 1000:
        raise ValueError("Order note is too long (max 1000 chars).")

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


# ─────────────────────────────────────────────────────────────────────────────
# EMAIL TEMPLATES
# ─────────────────────────────────────────────────────────────────────────────

def _items_table_html(items):
    rows = []
    for it in items:
        rows.append(
            f"""<tr>
              <td style="padding:10px 14px;border-bottom:1px solid #edf2f7;color:#1a202c;">{escape(it['name'])}
                <span style="color:#718096;font-size:12px;">({escape(it['pack'])})</span></td>
              <td style="padding:10px 14px;border-bottom:1px solid #edf2f7;text-align:center;color:#4a5568;">{it['quantity']}</td>
              <td style="padding:10px 14px;border-bottom:1px solid #edf2f7;text-align:right;color:#1a202c;">PKR {it['price'] * it['quantity']}</td>
            </tr>"""
        )
    return "".join(rows)


def _detail_row(label, value):
    if value in (None, ""):
        return ""
    return (
        f"""<tr>
          <td style="padding:8px 14px;font-weight:600;color:#4a5568;white-space:nowrap;border-bottom:1px solid #edf2f7;">{escape(str(label))}</td>
          <td style="padding:8px 14px;color:#1a202c;border-bottom:1px solid #edf2f7;">{escape(str(value))}</td>
        </tr>"""
    )


def _shell(title, subtitle, body_html):
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f7fafc;font-family:'Segoe UI',Roboto,Arial,sans-serif;">
  <div style="max-width:640px;margin:30px auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
    <div style="background:linear-gradient(135deg,{BRAND['navy']} 0%,{BRAND['ocean']} 50%,{BRAND['sky']} 100%);padding:30px 28px;text-align:center;">
      <h1 style="margin:0;color:#fff;font-size:22px;font-weight:700;">{escape(title)}</h1>
      <p style="margin:8px 0 0;color:rgba(255,255,255,0.9);font-size:14px;">{escape(subtitle)}</p>
    </div>
    <div style="padding:28px;">{body_html}</div>
    <div style="background:#f7fafc;padding:16px 28px;text-align:center;border-top:1px solid #edf2f7;">
      <p style="margin:0;font-size:12px;color:#a0aec0;">Barefruit Organics &times; HelloTabeeb &mdash; Order Management</p>
    </div>
  </div>
</body></html>"""


def _customer_block(order):
    loc = ""
    if order.get("latitude") is not None and order.get("longitude") is not None:
        maps = f"https://www.google.com/maps/search/?api=1&query={order['latitude']},{order['longitude']}"
        loc = (
            f"""<tr><td style="padding:8px 14px;font-weight:600;color:#4a5568;border-bottom:1px solid #edf2f7;">Location</td>
            <td style="padding:8px 14px;border-bottom:1px solid #edf2f7;">
            <a href="{escape(maps)}" style="color:#2b6cb0;">{order['latitude']:.5f}, {order['longitude']:.5f}</a></td></tr>"""
        )
    return (
        _detail_row("Name", order.get("customerName"))
        + _detail_row("Email", order.get("customerEmail"))
        + _detail_row("Phone", order.get("customerPhone"))
        + _detail_row("City", order.get("city"))
        + loc
        + _detail_row("Order Note", order.get("orderNote"))
        + _detail_row("Source", order.get("source"))
    )


def _admin_order_email(order_id, order):
    accept_url = _action_url(order_id, order["adminToken"], "accept")
    reject_url = _action_url(order_id, order["adminToken"], "reject")
    screenshot = order.get("paymentScreenshotUrl")
    screenshot_html = (
        f"""<p style="margin:18px 0 0;"><a href="{escape(screenshot)}" style="color:{BRAND['ocean']};font-weight:600;">&#128247; View Payment Screenshot</a></p>"""
        if screenshot else
        """<p style="margin:18px 0 0;color:#e53e3e;">No payment screenshot attached.</p>"""
    )
    body = f"""
      <h2 style="margin:0 0 12px;font-size:17px;color:{BRAND['navy']};">Order #{escape(order_id)}</h2>
      <table style="width:100%;border-collapse:collapse;font-size:14px;">{_items_table_html(order['items'])}
        <tr><td style="padding:12px 14px;font-weight:700;">Total</td><td></td>
        <td style="padding:12px 14px;text-align:right;font-weight:700;color:{BRAND['navy']};">PKR {order['subtotal']}</td></tr>
      </table>
      <h3 style="margin:22px 0 8px;font-size:15px;color:{BRAND['navy']};">Customer Details</h3>
      <table style="width:100%;border-collapse:collapse;font-size:14px;">{_customer_block(order)}</table>
      {screenshot_html}
      <div style="text-align:center;margin-top:28px;">
        <p style="font-size:14px;color:#718096;margin-bottom:16px;">Verify the payment, then choose an action:</p>
        <a href="{escape(accept_url)}" style="display:inline-block;padding:14px 38px;background:linear-gradient(135deg,{BRAND['green_dark']},{BRAND['green']});color:#fff;font-weight:700;text-decoration:none;border-radius:50px;margin:0 6px 12px;">&#10004; Place Order</a>
        <a href="{escape(reject_url)}" style="display:inline-block;padding:14px 38px;background:linear-gradient(135deg,{BRAND['red_dark']},{BRAND['red']});color:#fff;font-weight:700;text-decoration:none;border-radius:50px;margin:0 6px 12px;">&#10008; Reject Order</a>
      </div>"""
    return _shell("New Barefruit Order", "A customer has placed an order and paid.", body)


def _shipping_email(order_id, order):
    ship_url = _action_url(order_id, order["shipToken"], "shipped")
    body = f"""
      <h2 style="margin:0 0 12px;font-size:17px;color:{BRAND['navy']};">Order #{escape(order_id)} — approved & ready to pack</h2>
      <table style="width:100%;border-collapse:collapse;font-size:14px;">{_items_table_html(order['items'])}
        <tr><td style="padding:12px 14px;font-weight:700;">Total</td><td></td>
        <td style="padding:12px 14px;text-align:right;font-weight:700;color:{BRAND['navy']};">PKR {order['subtotal']}</td></tr>
      </table>
      <h3 style="margin:22px 0 8px;font-size:15px;color:{BRAND['navy']};">Ship To</h3>
      <table style="width:100%;border-collapse:collapse;font-size:14px;">{_customer_block(order)}</table>
      <div style="text-align:center;margin-top:28px;">
        <p style="font-size:14px;color:#718096;margin-bottom:16px;">Once packed and handed to the courier, mark it shipped:</p>
        <a href="{escape(ship_url)}" style="display:inline-block;padding:14px 40px;background:linear-gradient(135deg,{BRAND['navy']},{BRAND['ocean']});color:#fff;font-weight:700;text-decoration:none;border-radius:50px;">&#128230; Order is Shipped</a>
      </div>"""
    return _shell("Order Approved — Ship It", "Payment verified by admin.", body)


def _admin_reaccept_email(order_id, order):
    reaccept_url = _action_url(order_id, order["reAcceptToken"], "reaccept")
    body = f"""
      <h2 style="margin:0 0 12px;font-size:17px;color:{BRAND['navy']};">Order #{escape(order_id)} was rejected</h2>
      <p style="font-size:14px;color:#4a5568;">Rejection reason: <strong>{escape(order.get('rejectionReason') or 'N/A')}</strong></p>
      <p style="font-size:14px;color:#4a5568;">If the customer has since contacted support (<a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a>) and the issue is resolved, you can still approve this order using the button below. This link is a safety workaround and works only for this rejected order.</p>
      <table style="width:100%;border-collapse:collapse;font-size:14px;margin-top:12px;">{_customer_block(order)}</table>
      <div style="text-align:center;margin-top:26px;">
        <a href="{escape(reaccept_url)}" style="display:inline-block;padding:14px 40px;background:linear-gradient(135deg,{BRAND['green_dark']},{BRAND['green']});color:#fff;font-weight:700;text-decoration:none;border-radius:50px;">&#10004; Approve Order Anyway</a>
      </div>"""
    return _shell("Rejected Order — Re-Approval Option", "Support workaround for a rejected order.", body)


def _customer_rejected_email(order_id, order):
    reason = order.get("rejectionReason") or "the payment could not be verified"
    body = f"""
      <p style="font-size:15px;color:#1a202c;">Dear {escape(order.get('customerName') or 'Customer')},</p>
      <p style="font-size:14px;color:#4a5568;line-height:1.7;">Unfortunately your Barefruit order <strong>#{escape(order_id)}</strong> could not be approved for the following reason:</p>
      <div style="background:#fff5f5;border-left:4px solid {BRAND['red']};padding:14px 16px;border-radius:8px;margin:12px 0;color:#742a2a;">{escape(reason)}</div>
      <p style="font-size:14px;color:#4a5568;line-height:1.7;">You can simply place the order again using the same payment screenshot — just mention in the <strong>order note</strong> that this issue has been resolved, so our team can approve it quickly.</p>
      <p style="font-size:14px;color:#4a5568;line-height:1.7;">If you believe this is a mistake or you have already paid correctly, please contact our support team and share your claim so we make sure your order reaches you safely:</p>
      <p style="text-align:center;margin:18px 0;"><a href="mailto:{SUPPORT_EMAIL}" style="display:inline-block;padding:12px 30px;background:{BRAND['navy']};color:#fff;text-decoration:none;border-radius:50px;font-weight:600;">Contact Support</a></p>
      <p style="font-size:13px;color:#718096;text-align:center;">{SUPPORT_EMAIL}</p>"""
    return _shell("About Your Barefruit Order", "Order update", body)


def _customer_shipped_email(order_id, order):
    body = f"""
      <p style="font-size:15px;color:#1a202c;">Dear {escape(order.get('customerName') or 'Customer')},</p>
      <p style="font-size:14px;color:#4a5568;line-height:1.7;">Great news! Your Barefruit order <strong>#{escape(order_id)}</strong> has been packed and <strong>shipped</strong>. It is now on its way to you.</p>
      <table style="width:100%;border-collapse:collapse;font-size:14px;margin-top:12px;">{_items_table_html(order['items'])}
        <tr><td style="padding:12px 14px;font-weight:700;">Total</td><td></td>
        <td style="padding:12px 14px;text-align:right;font-weight:700;color:{BRAND['navy']};">PKR {order['subtotal']}</td></tr>
      </table>
      <p style="font-size:14px;color:#4a5568;line-height:1.7;margin-top:16px;">Thank you for shopping with Barefruit Organics — pure, wild and uncompromised. For any query, reach us at <a href="mailto:{SUPPORT_EMAIL}">{SUPPORT_EMAIL}</a>.</p>"""
    return _shell("Your Order Has Shipped", "Barefruit Organics", body)


# ─────────────────────────────────────────────────────────────────────────────
# RESULT PAGE (shown to whoever clicks an email button)
# ─────────────────────────────────────────────────────────────────────────────

def _result_page(title, message, success=True, status_code=200):
    accent = BRAND["green"] if success else BRAND["red"]
    badge_bg = "#d4edda" if success else "#f8d7da"
    icon = "&#9989;" if success else "&#10060;"
    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0"><title>{escape(title)} – Barefruit</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',sans-serif;background:#f0f4f8;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:24px}}
.card{{background:#fff;border-radius:20px;padding:48px 40px;max-width:480px;width:100%;text-align:center;box-shadow:0 10px 40px rgba(0,0,0,.1)}}
.icon{{width:80px;height:80px;border-radius:50%;background:{badge_bg};display:flex;align-items:center;justify-content:center;margin:0 auto 24px;font-size:40px}}
h1{{color:{BRAND['navy']};font-size:22px;font-weight:700;margin-bottom:12px}}
p{{color:#555;font-size:15px;line-height:1.7}}
.badge{{display:inline-block;margin-top:24px;padding:6px 20px;border-radius:50px;background:{badge_bg};color:{accent};font-size:13px;font-weight:600}}</style></head>
<body><div class="card"><div class="icon">{icon}</div><h1>{escape(title)}</h1><p>{message}</p>
<span class="badge">Barefruit Organics Admin</span></div></body></html>"""
    return html, status_code


def _reject_reason_form(order_id, token):
    action_post = f"{PUBLIC_BASE_URL}/barefruit/reject"
    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Reject Order – Barefruit</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',sans-serif;background:#f0f4f8;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:24px}}
.card{{background:#fff;border-radius:20px;padding:40px;max-width:520px;width:100%;box-shadow:0 10px 40px rgba(0,0,0,.1)}}
h1{{color:{BRAND['navy']};font-size:20px;margin-bottom:8px}}
p{{color:#666;font-size:14px;margin-bottom:18px;line-height:1.6}}
textarea{{width:100%;min-height:120px;border:1px solid #d0d7de;border-radius:12px;padding:14px;font-size:14px;font-family:inherit;resize:vertical}}
button{{margin-top:18px;width:100%;padding:14px;border:none;border-radius:50px;background:linear-gradient(135deg,{BRAND['red_dark']},{BRAND['red']});color:#fff;font-size:15px;font-weight:700;cursor:pointer}}</style></head>
<body><div class="card"><h1>Reject Order #{escape(order_id)}</h1>
<p>Please provide a reason for rejecting this order (most often a payment-screenshot issue). The customer will receive this reason by email.</p>
<form method="get" action="{escape(action_post)}">
<input type="hidden" name="orderId" value="{escape(order_id)}">
<input type="hidden" name="token" value="{escape(token)}">
<textarea name="reason" required maxlength="1000" placeholder="e.g. The payment screenshot is unclear / amount does not match / transaction not found."></textarea>
<button type="submit">Confirm Rejection</button>
</form></div></body></html>"""
    return html


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@barefruit.route("/barefruit")
def storefront():
    return render_template(
        "barefruit.html",
        products=BAREFRUIT_PRODUCTS,
        payment=PAYMENT_DETAILS,
        cities=[
            "Lahore", "Karachi", "Islamabad", "Rawalpindi", "Faisalabad",
            "Gujranwala", "Multan", "Peshawar", "Quetta", "Sialkot",
        ],
    )


@barefruit.route("/barefruit/place-order", methods=["POST"])
def place_order():
    try:
        raw_items = request.form.get("items")
        try:
            parsed_items = json.loads(raw_items) if raw_items else None
        except (TypeError, ValueError):
            return jsonify(success=False, message="Invalid cart data."), 400

        items, subtotal, total_items = _validate_and_price_items(parsed_items)
        customer = _validate_customer(request.form)

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
            logger.error("Screenshot upload failed: %s", exc)
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
            "source": "web",
            "createdAt": firestore.SERVER_TIMESTAMP,
        }

        doc_ref = db.collection(ORDERS_COLLECTION).document()
        doc_ref.set(order)
        order_id = doc_ref.id

        _send_email(
            [{"email": ADMIN_EMAIL, "name": "HelloTabeeb"}],
            f"New Barefruit Order #{order_id} — PKR {subtotal}",
            _admin_order_email(order_id, order),
        )

        return jsonify(success=True, orderId=order_id,
                       message="Your order has been placed! You'll be notified once it is confirmed.")
    except ValueError as ve:
        return jsonify(success=False, message=str(ve)), 400
    except Exception as exc:  # pragma: no cover
        logger.exception("place_order failed: %s", exc)
        return jsonify(success=False, message="Something went wrong. Please try again."), 500


@barefruit.route("/barefruit/action")
def order_action():
    order_id = request.args.get("orderId", "")
    token = request.args.get("token", "")
    action = request.args.get("action", "")

    if not order_id or not token or action not in {"accept", "reject", "reaccept", "shipped"}:
        return _result_page("Invalid Request",
                            "This link is missing required information.", False, 400)

    doc_ref = db.collection(ORDERS_COLLECTION).document(order_id)
    snap = doc_ref.get()
    if not snap.exists:
        return _result_page("Order Not Found",
                            "No order was found for this link.", False, 404)
    order = snap.to_dict()
    status = order.get("status")

    # ── REJECT (step 1): show reason form, no state change yet ──────────────
    if action == "reject":
        if status != "pending":
            return _result_page("Already Processed",
                                f"This order is already <strong>{escape(status)}</strong>.", False)
        if not _tokens_match(order.get("adminToken"), token):
            return _result_page("Invalid or Expired Link",
                                "This link is invalid or has already been used.", False, 403)
        return _reject_reason_form(order_id, token)

    # ── ACCEPT ──────────────────────────────────────────────────────────────
    if action == "accept":
        if status == "accepted":
            return _result_page("Already Approved", "This order was already approved.", True)
        if status != "pending":
            return _result_page("Cannot Approve",
                                f"This order is <strong>{escape(status)}</strong> and can no longer be approved here.", False)
        if not _tokens_match(order.get("adminToken"), token):
            return _result_page("Invalid or Expired Link",
                                "This link is invalid or has already been used.", False, 403)
        doc_ref.update({
            "status": "accepted",
            "adminToken": firestore.DELETE_FIELD,
            "acceptedAt": firestore.SERVER_TIMESTAMP,
        })
        order["status"] = "accepted"
        _send_email(
            [{"email": SHIPPING_MANAGER_EMAIL, "name": "Shipping Manager"}],
            f"Barefruit Order #{order_id} — Approved, please ship",
            _shipping_email(order_id, order),
        )
        return _result_page("Order Approved",
                            "The order was approved and the shipping manager has been notified.", True)

    # ── RE-ACCEPT (support workaround for a rejected order) ──────────────────
    if action == "reaccept":
        if status == "accepted":
            return _result_page("Already Approved", "This order was already approved.", True)
        if status != "rejected":
            return _result_page("Cannot Re-Approve",
                                f"This order is <strong>{escape(status)}</strong>.", False)
        if not _tokens_match(order.get("reAcceptToken"), token):
            return _result_page("Invalid or Expired Link",
                                "This re-approval link is invalid or has already been used.", False, 403)
        doc_ref.update({
            "status": "accepted",
            "reAcceptToken": firestore.DELETE_FIELD,
            "acceptedAt": firestore.SERVER_TIMESTAMP,
            "reApproved": True,
        })
        order["status"] = "accepted"
        _send_email(
            [{"email": SHIPPING_MANAGER_EMAIL, "name": "Shipping Manager"}],
            f"Barefruit Order #{order_id} — Approved (re-approved), please ship",
            _shipping_email(order_id, order),
        )
        return _result_page("Order Re-Approved",
                            "The order was approved and the shipping manager has been notified.", True)

    # ── SHIPPED ──────────────────────────────────────────────────────────────
    if action == "shipped":
        if status == "shipped":
            return _result_page("Already Shipped", "This order was already marked as shipped.", True)
        if status != "accepted":
            return _result_page("Cannot Mark Shipped",
                                f"This order is <strong>{escape(status)}</strong>. Only approved orders can be shipped.", False)
        if not _tokens_match(order.get("shipToken"), token):
            return _result_page("Invalid or Expired Link",
                                "This link is invalid or has already been used.", False, 403)
        doc_ref.update({
            "status": "shipped",
            "shipToken": firestore.DELETE_FIELD,
            "shippedAt": firestore.SERVER_TIMESTAMP,
        })
        order["status"] = "shipped"
        _send_email(
            [{"email": order.get("customerEmail"), "name": order.get("customerName") or "Customer"}],
            f"Your Barefruit Order #{order_id} has shipped",
            _customer_shipped_email(order_id, order),
        )
        return _result_page("Marked as Shipped",
                            "The customer has been notified that their order is on the way.", True)

    return _result_page("Invalid Action", "Unknown action.", False, 400)


@barefruit.route("/barefruit/reject", methods=["GET", "POST"])
def reject_order():
    # Read from request.values so it works whether the reason form is submitted
    # as GET (fields in the query string, survives email/proxy redirects) or POST.
    order_id = request.values.get("orderId", "")
    token = request.values.get("token", "")
    reason = (request.values.get("reason") or "").strip()

    if not order_id or not token:
        return _result_page("Invalid Request", "Missing required information.", False, 400)
    if not reason:
        return _result_page("Reason Required", "Please provide a rejection reason.", False, 400)
    if len(reason) > 1000:
        reason = reason[:1000]

    doc_ref = db.collection(ORDERS_COLLECTION).document(order_id)
    snap = doc_ref.get()
    if not snap.exists:
        return _result_page("Order Not Found", "No order was found for this link.", False, 404)
    order = snap.to_dict()
    status = order.get("status")

    if status != "pending":
        return _result_page("Already Processed",
                            f"This order is already <strong>{escape(status)}</strong>.", False)
    if not _tokens_match(order.get("adminToken"), token):
        return _result_page("Invalid or Expired Link",
                            "This link is invalid or has already been used.", False, 403)

    doc_ref.update({
        "status": "rejected",
        "rejectionReason": reason,
        "adminToken": firestore.DELETE_FIELD,
        "rejectedAt": firestore.SERVER_TIMESTAMP,
    })
    order["status"] = "rejected"
    order["rejectionReason"] = reason

    # Notify the customer with the reason + support guidance.
    if order.get("customerEmail"):
        _send_email(
            [{"email": order["customerEmail"], "name": order.get("customerName") or "Customer"}],
            f"Update on your Barefruit Order #{order_id}",
            _customer_rejected_email(order_id, order),
        )

    # Send the admin a re-accept follow-up (support workaround).
    _send_email(
        [{"email": ADMIN_EMAIL, "name": "HelloTabeeb"}],
        f"Barefruit Order #{order_id} rejected — re-approval available",
        _admin_reaccept_email(order_id, order),
    )

    return _result_page("Order Rejected",
                        "The customer has been notified with your reason, and a re-approval option was sent to admin.", True)
