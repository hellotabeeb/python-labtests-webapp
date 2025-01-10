from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from .utils import send_email, move_code_to_availed
from flask import current_app
import logging
import firebase_admin
from firebase_admin import firestore
from . import db
from firebase_admin import credentials, storage
from werkzeug.utils import secure_filename
import dropbox
import os
import mimetypes
from googleapiclient.http import MediaFileUpload
from . import db, drive_service
from googleapiclient.http import MediaIoBaseUpload
from datetime import datetime
from brevo_python import Configuration, ApiClient, TransactionalEmailsApi, SendSmtpEmail
from brevo_python.rest import ApiException
from datetime import datetime
import json
from firebase_admin import firestore, credentials, initialize_app, get_app, _apps
from firebase_admin import firestore, credentials, initialize_app, _apps





main = Blueprint('main', __name__)

# Brevo Configuration
configuration = Configuration()
configuration.api_key['api-key'] = os.getenv('BREVO_API_KEY')
api_client = ApiClient(configuration)
api_instance = TransactionalEmailsApi(api_client)


# @main.route('/firebase-config')
# def firebase_config():
#     try:
#         with open('app/serviceAccountKey.json') as f:
#             config = json.load(f)
#         firebase_config = {
#             "apiKey": os.getenv('FIREBASE_API_KEY'),
#             "authDomain": os.getenv('FIREBASE_AUTH_DOMAIN'),
#             "projectId": config.get('project_id'),
#             "storageBucket": os.getenv('FIREBASE_STORAGE_BUCKET'),
#             "messagingSenderId": os.getenv('FIREBASE_MESSAGING_SENDER_ID'),
#             "appId": os.getenv('FIREBASE_APP_ID'),
#             "measurementId": os.getenv('FIREBASE_MEASUREMENT_ID')
#         }
#         return jsonify(firebase_config)
#     except Exception as e:
#         current_app.logger.error(f"Error fetching Firebase config: {e}")
#         return jsonify({"error": "Failed to fetch Firebase config"}), 500



# Initialize Firebase Admin SDK
if not _apps:
    service_account_info = json.loads(os.getenv('SERVICE_ACCOUNT_KEY'))
    cred = credentials.Certificate(service_account_info)
    initialize_app(cred)
db = firestore.client()

@main.route('/firebase-config')
def firebase_config():
    try:
        service_account_info = json.loads(os.getenv('SERVICE_ACCOUNT_KEY'))
        firebase_config = {
            "apiKey": os.getenv('FIREBASE_API_KEY'),
            "authDomain": os.getenv('FIREBASE_AUTH_DOMAIN'),
            "projectId": service_account_info.get('project_id'),
            "storageBucket": os.getenv('FIREBASE_STORAGE_BUCKET'),
            "messagingSenderId": os.getenv('FIREBASE_MESSAGING_SENDER_ID'),
            "appId": os.getenv('FIREBASE_APP_ID'),
            "measurementId": os.getenv('FIREBASE_MEASUREMENT_ID')
        }
        return jsonify(firebase_config)
    except Exception as e:
        current_app.logger.error(f"Error fetching Firebase config: {e}")
        return jsonify({"error": "Failed to fetch Firebase config"}), 500

@main.route('/labtests')
def index():
    return render_template('index.html')

@main.route('/appointment')
def appointment():
    return render_template('appointment.html')

@main.route('/appointment/doctor-listing/<category>')
def doctor_listing(category):
    return render_template('doctor-listing.html', category=category)

@main.route('/book-appointment', methods=['POST'])
def book_appointment():
    try:
        data = request.form
        current_app.logger.info(f"Received form data: {data}")

        # Validate required fields
        required_fields = {
            'doctorName': 'Doctor Name',
            'doctorSpecialty': 'Doctor Specialty',
            'doctorEmail': 'Doctor Email',
            'patientName': 'Patient Name',
            'patientAge': 'Patient Age',
            'patientPhone': 'Patient Phone',
            'patientEmail': 'Patient Email',
            'appointmentDay': 'Appointment Day',
            'appointmentTime': 'Appointment Time'
        }

        # Check for missing required fields
        missing_fields = []
        for field, label in required_fields.items():
            if not data.get(field):
                missing_fields.append(label)
        
        if missing_fields:
            return jsonify({
                'success': False, 
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400

        # Extract form data
        doctor_name = data.get('doctorName')
        doctor_specialty = data.get('doctorSpecialty')
        doctor_email = data.get('doctorEmail')
        patient_name = data.get('patientName')
        patient_age = data.get('patientAge')
        patient_phone = data.get('patientPhone')
        patient_email = data.get('patientEmail')
        appointment_day = data.get('appointmentDay')
        appointment_time = data.get('appointmentTime')
        patient_remarks = data.get('patientRemarks', '')  # Optional field

        # Handle file attachment
        attachment = request.files.get('attachment')
        current_app.logger.info(f"Received booking request for {patient_name} with attachment: {attachment}")

        attachment_url = None
        if attachment:
            # Validate file type
            if attachment.mimetype not in ['image/jpeg', 'image/png', 'application/pdf']:
                current_app.logger.error("Invalid file type. Only JPG, PNG, and PDF are allowed.")
                return jsonify({
                    'success': False, 
                    'message': 'Invalid file type. Only JPG, PNG, and PDF are allowed.'
                }), 400

            # Validate file size (10MB limit)
            if attachment.content_length > 10 * 1024 * 1024:
                current_app.logger.error("File size exceeds 10MB limit.")
                return jsonify({
                    'success': False, 
                    'message': 'File size exceeds 10MB limit.'
                }), 400

            # Upload attachment to Google Drive
            file_name = secure_filename(f"{patient_name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{attachment.filename}")
            file_metadata = {
                'name': file_name, 
                'parents': ['1cv8hx__BI6ZAPd4H_tXqCecO6UZ8ivua']
            }
            media = MediaIoBaseUpload(
                attachment.stream, 
                mimetype=attachment.mimetype, 
                resumable=True
            )
            file = drive_service.files().create(
                body=file_metadata, 
                media_body=media, 
                fields='id,webViewLink'
            ).execute()
            
            # Make file accessible via link
            drive_service.permissions().create(
                fileId=file['id'], 
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()
            
            attachment_url = file.get('webViewLink')
            current_app.logger.info(f"File uploaded to Google Drive with URL: {attachment_url}")

        # Prepare admin email content
        admin_html_content = f"""
        <html>
            <body>
                <h2>New Appointment Booking</h2>
                <h3>Doctor Details</h3>
                <p><strong>Name:</strong> {doctor_name}</p>
                <p><strong>Specialty:</strong> {doctor_specialty}</p>
                <p><strong>Email:</strong> {doctor_email}</p>
                <h3>Patient Details</h3>
                <p><strong>Name:</strong> {patient_name}</p>
                <p><strong>Age:</strong> {patient_age}</p>
                <p><strong>Phone:</strong> {patient_phone}</p>
                <p><strong>Email:</strong> {patient_email}</p>
                <p><strong>Preferred Day:</strong> {appointment_day}</p>
                <p><strong>Preferred Time:</strong> {appointment_time}</p>
                <p><strong>Remarks:</strong> {patient_remarks}</p>
                {f'<p><strong>Attachment:</strong> <a href="{attachment_url}">View Attachment</a></p>' if attachment_url else ''}
            </body>
        </html>
        """

        # Send email to admin
        admin_email = "ahadnaseer47@gmail.com"
        admin_send_smtp_email = SendSmtpEmail(
            to=[{
                "email": admin_email,
                "name": "Admin"  # Added name field
            }],
            sender={
                "name": "HelloTabeeb",
                "email": "support@hellotabeeb.com"
            },
            subject="New Appointment Booking - HelloTabeeb",
            html_content=admin_html_content
        )
        current_app.logger.info(f"Sending admin email: {admin_send_smtp_email}")
        api_instance.send_transac_email(admin_send_smtp_email)

        # Prepare customer email content
        customer_html_content = f"""
        <html>
            <body>
                <h2>Appointment Booking Confirmation</h2>
                <p>Dear {patient_name},</p>
                <p>Thank you for booking an appointment with {doctor_name}. Your booking has been confirmed for {appointment_day} at {appointment_time}.</p>
                <p>You will be contacted soon on your provided number: {patient_phone}.</p>
                <h3>Appointment Details:</h3>
                <p><strong>Doctor:</strong> {doctor_name}</p>
                <p><strong>Specialty:</strong> {doctor_specialty}</p>
                <p><strong>Day:</strong> {appointment_day}</p>
                <p><strong>Time:</strong> {appointment_time}</p>
                <p>If you need to make any changes to your appointment, please contact us at support@hellotabeeb.com or +92 335 1626806</p>
                <p>Thank you for choosing HelloTabeeb!</p>
            </body>
        </html>
        """

        # Send email to customer
        customer_send_smtp_email = SendSmtpEmail(
            to=[{
                "email": patient_email,
                "name": patient_name  # Added name field
            }],
            sender={
                "name": "HelloTabeeb",
                "email": "support@hellotabeeb.com"
            },
            subject="Appointment Booking Confirmation - HelloTabeeb",
            html_content=customer_html_content
        )
        current_app.logger.info(f"Sending customer email: {customer_send_smtp_email}")
        api_instance.send_transac_email(customer_send_smtp_email)

        return jsonify({'success': True, 'message': 'Booking confirmed!'})

    except ApiException as e:
        current_app.logger.error(f"Brevo API Exception: {e}")
        return jsonify({
            'success': False, 
            'message': 'Email notification failed. Please contact support.'
        }), 500
    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return jsonify({
            'success': False, 
            'message': 'Booking failed. Please try again.'
        }), 500


@main.route('/submit-card-purchase', methods=['POST'])
def submit_card_purchase():
    try:
        # Get form data
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        age = request.form.get('age')
        message = request.form.get('message', '')
        payment_proof = request.files.get('payment-proof')
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

        # Validate required fields
        if not all([name, email, phone, age, payment_proof]):
            return jsonify({
                'success': False,
                'message': 'Please fill in all required fields'
            }), 400

        # Validate file size and type
        if payment_proof:
            # Check file size (10MB limit)
            payment_proof.seek(0, 2)  # Seek to end of file
            size = payment_proof.tell()
            payment_proof.seek(0)  # Reset file pointer
            
            if size > 10 * 1024 * 1024:
                return jsonify({
                    'success': False,
                    'message': 'Payment proof file size must be less than 10MB'
                }), 400

            # Check file type
            allowed_types = {'image/jpeg', 'image/png', 'image/jpg', 'application/pdf'}
            if payment_proof.content_type not in allowed_types:
                return jsonify({
                    'success': False,
                    'message': 'Please upload an image file (JPEG, PNG) or PDF'
                }), 400

        # Upload payment proof to Google Drive
        try:
            file_name = secure_filename(f"{name}_{timestamp}_{payment_proof.filename}")
            
            # Create 'card_purchases' folder if it doesn't exist
            folder_name = 'card_purchases'
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = drive_service.files().list(q=query, fields="files(id)").execute()
            folders = results.get('files', [])
            
            if not folders:
                folder_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
                folder_id = folder.get('id')
            else:
                folder_id = folders[0]['id']

            # Upload file
            file_metadata = {
                'name': file_name,
                'parents': [folder_id]
            }
            
            media = MediaIoBaseUpload(
                payment_proof,
                mimetype=payment_proof.content_type,
                resumable=True
            )
            
            file = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink'
            ).execute()

            # Make file publicly accessible
            drive_service.permissions().create(
                fileId=file['id'],
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()

            payment_proof_url = file.get('webViewLink', '')

        except Exception as upload_error:
            logging.error(f"Error uploading payment proof: {str(upload_error)}")
            return jsonify({
                'success': False,
                'message': 'Failed to upload payment proof. Please try again.'
            }), 500

        # Send email to admin
        try:
            sender = {"name": "HelloTabeeb", "email": "support@hellotabeeb.com"}
            admin_html_content = f"""
            <html>
                <body>
                    <h2>New Card Purchase</h2>
                    <h3>Customer Details</h3>
                    <p><strong>Name:</strong> {name}</p>
                    <p><strong>Email:</strong> {email}</p>
                    <p><strong>Phone Number:</strong> {phone}</p>
                    <p><strong>Age:</strong> {age}</p>
                    <p><strong>Message:</strong> {message}</p>
                    <p><strong>Payment Proof:</strong> <a href="{payment_proof_url}">View Payment Proof</a></p>
                    <p><strong>Purchase Timestamp:</strong> {timestamp}</p>
                </body>
            </html>
            """

            admin_email = SendSmtpEmail(
                to=[{"email": "shahzad892@gmail.com"}],
                sender=sender,
                subject="New Card Purchase - HelloTabeeb",
                html_content=admin_html_content
            )
            api_instance.send_transac_email(admin_email)
            logging.getLogger(__name__).info(f"Admin notification email sent for card purchase by {email}")

        except ApiException as e:
            logging.getLogger(__name__).error(f"Brevo API Exception when sending admin email: {e}")
        except Exception as e:
            logging.getLogger(__name__).error(f"Unexpected error when sending admin email: {e}")

        return jsonify({
            'success': True,
            'message': 'Purchase submitted successfully. You will be contacted soon on your provided number.',
            'redirect': '/card'
        })

    except Exception as e:
        logging.getLogger(__name__).error(f"Error saving card purchase: {str(e)}")
        return jsonify({
            'success': False, 
            'message': 'An unexpected error occurred. Please try again.'
        }), 500
    
    
@main.route('/validate-card', methods=['POST'])
def validate_card():
    try:
        phone = request.json.get('phone')
        if not phone:
            return jsonify({'valid': False, 'error': 'Phone number is required'}), 400
            
        db = firestore.client()
        
        # Query Firestore for the phone number
        docs = db.collection('cardPurchase').where('phone', '==', phone).limit(1).get()
        
        found = False
        for doc in docs:
            found = True
            data = doc.to_dict()
            return jsonify({
                'valid': True,
                'name': data.get('name'),
                'email': data.get('email'),
                'phone': phone,
                'age': data.get('age')  # Add age to response
            })
        
        if not found:
            return jsonify({'valid': False, 'message': 'No card found for this number'})
            
    except Exception as e:
        main.logger.error(f"Error validating card: {str(e)}")
        return jsonify({
            'valid': False, 
            'error': 'An error occurred while validating the card'
        }), 500

    


@main.route('/validation')
def validation():
    return render_template('validation.html')

@main.route('/card')
def card():
    return render_template('card.html')


# Initialize Dropbox client
DROPBOX_ACCESS_TOKEN = os.getenv('DROPBOX_ACCESS_TOKEN')
dropbox_client = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)

@main.route('/join')
def doctor_registration():
    return render_template('doctor_registration.html')


@main.route('/home-sampling', methods=['GET', 'POST'])
def home_sampling():
    if request.method == 'POST':
        try:
            data = request.form.to_dict()
            logger = logging.getLogger(__name__)
            logger.info(f"Received home sampling request data: {data}")

            # Handle file upload
            prescription = request.files['prescription']
            if prescription:
                # Check file size (max 10MB)
                if len(prescription.read()) > 10 * 1024 * 1024:
                    return jsonify({"success": False, "message": "File size exceeds 10MB limit."}), 400
                prescription.seek(0)  # Reset file pointer after reading size

                # Secure filename
                filename = secure_filename(prescription.filename)

                # Upload file to Google Drive
                mime_type, _ = mimetypes.guess_type(filename)
                media = MediaIoBaseUpload(prescription.stream, mimetype=mime_type)
                file_metadata = {'name': filename}
                file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()

                # Make the file publicly accessible
                drive_service.permissions().create(
                    fileId=file.get('id'),
                    body={'type': 'anyone', 'role': 'reader'}
                ).execute()

                # Add file URL to the data dictionary
                data['prescription_url'] = file.get('webViewLink')

            # Add timestamp to the data dictionary
            data['timestamp'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

            # Save data to Firestore
            doc_ref = db.collection('homeSampling').document(data['full-name'])
            doc_ref.set(data)

            # Send email to admin
            try:
                sender = {"name": "HelloTabeeb", "email": "support@hellotabeeb.com"}  # Replace with your sender email
                to = [{"email": "shahzad892@gmail.com"}]
                
                html_content = f"""
                <html>
                    <body>
                        <h2>New Home Sampling Request</h2>
                        <p><strong>Name:</strong> {data['full-name']}</p>
                        <p><strong>Phone Number:</strong> {data['phone-number']}</p>
                        <p><strong>Email:</strong> {data.get('email', 'N/A')}</p>
                        <p><strong>Address:</strong> {data['address']}</p>
                        <p><strong>City:</strong> {data['city']}</p>
                        <p><strong>Test Name:</strong> {data['test-name']}</p>
                        <p><strong>Preferred Date and Time:</strong> {data['date-time']}</p>
                        <p><strong>Mode of Payment:</strong> {data['payment-mode']}</p>
                        <p><strong>Additional Notes:</strong> {data.get('additional-notes', 'N/A')}</p>
                        <p><strong>Prescription URL:</strong> <a href="{data['prescription_url']}">View Prescription</a></p>
                        <p><strong>Timestamp:</strong> {data['timestamp']}</p>
                    </body>
                </html>
                """
                
                send_smtp_email = SendSmtpEmail(
                    to=to,
                    sender=sender,
                    subject="New Home Sampling Request",
                    html_content=html_content
                )
                
                api_instance.send_transac_email(send_smtp_email)
                logger.info(f"Email sent successfully to shahzad892@gmail.com.")
            except ApiException as e:
                logger.error(f"Brevo API Exception when sending email: {e}")
            except Exception as e:
                logger.error(f"Unexpected error when sending email: {e}")

            return jsonify({"success": True, "message": "Home sampling request submitted successfully."}), 200
        except Exception as e:
            logger.error(f"Error submitting home sampling request: {e}")
            return jsonify({"success": False, "message": "Failed to submit home sampling request."}), 500
    return render_template('home_sampling.html')




# routes.py
import mimetypes
from googleapiclient.http import MediaFileUpload

@main.route('/register-doctor', methods=['POST'])
def register_doctor():
    try:
        data = request.form.to_dict()
        logger = logging.getLogger(__name__)
        logger.info(f"Received doctor registration data: {data}")

        # Handle file uploads
        doctor_image = request.files['doctor-image']
        doctor_resume = request.files['doctor-resume']

        if doctor_image and doctor_resume:
            # File handling functions
            def create_folder(folder_name, parent_id=None):
                file_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                if parent_id:
                    file_metadata['parents'] = [parent_id]
                folder = drive_service.files().create(body=file_metadata, fields='id').execute()
                return folder.get('id')

            def upload_to_drive(file, filename, folder_id=None):
                mime_type, _ = mimetypes.guess_type(filename)
                media = MediaIoBaseUpload(file, mimetype=mime_type)
                file_metadata = {'name': filename}
                if folder_id:
                    file_metadata['parents'] = [folder_id]
                file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
                
                drive_service.permissions().create(
                    fileId=file.get('id'),
                    body={'type': 'anyone', 'role': 'reader'}
                ).execute()
                
                return file.get('webViewLink')

            # Helper functions for getting correct labels
            def get_license_label(country):
                labels = {
                    'afghanistan': 'Medical License Number',
        'albania': 'Medical License Registration',
        'algeria': 'Medical Registration Number',
        'andorra': 'Medical License Number',
        'angola': 'Medical License Registration',
        'antigua and barbuda': 'Medical License Number',
        'argentina': 'Matricula Nacional',
        'armenia': 'Medical Registration Number',
        'australia': 'Medical Registration Number',
        'austria': 'Medical Practitioner Registration Number',
        'azerbaijan': 'Medical License Number',
        'bahamas': 'Medical License Registration',
        'bahrain': 'Medical Registration Number',
        'bangladesh': 'BMDC Registration Number',
        'barbados': 'Medical License Number',
        'belarus': 'Medical Registration Number',
        'belgium': 'Medical Registration Number',
        'belize': 'Medical License Number',
        'benin': 'Medical License Registration',
        'bhutan': 'Medical License Number',
        'bolivia': 'Medical License Registration',
        'bosnia and herzegovina': 'Medical License Number',
        'botswana': 'Medical License Registration',
        'brazil': 'CRM Number',
        'brunei': 'Medical Registration Number',
        'bulgaria': 'Medical License Registration',
        'burkina faso': 'Medical License Number',
        'burundi': 'Medical License Registration',
        'cabo verde': 'Medical License Number',
        'cambodia': 'Medical License Number',
        'cameroon': 'Medical Registration Number',
        'canada': 'Medical License Number',
        'central african republic': 'Medical Registration Number',
        'chad': 'Medical License Registration',
        'chile': 'Medical License Number',
        'china': 'Medical Practitioner Registration Number',
        'colombia': 'Medical License Registration',
        'comoros': 'Medical License Number',
        'congo, democratic republic of the': 'Medical Registration Number',
        'congo, republic of the': 'Medical License Number',
        'costa rica': 'Medical License Registration',
        'croatia': 'Medical Registration Number',
        'cuba': 'Medical License Number',
        'cyprus': 'Medical Practitioner License',
        'czech republic': 'Medical License Number',
        'denmark': 'Medical License Registration',
        'djibouti': 'Medical Registration Number',
        'dominica': 'Medical License Number',
        'dominican republic': 'Medical License Registration',
        'ecuador': 'Medical License Number',
        'egypt': 'Medical Registration Number',
        'el salvador': 'Colegio Médico Registration Number',
        'equatorial guinea': 'Registro Médico Número',
        'eritrea': 'Medical License Number',
        'estonia': 'Medical Practitioner Registration Number',
        'eswatini': 'Medical Council Registration Number',
        'ethiopia': 'Ethiopian Medical Association License Number',
        'federated states of micronesia': 'FSM Medical Registration Number',
        'fiji': 'Medical Registration Number',
        'finland': 'Finnish Medical Association License Number',
        'france': 'Numéro d\'inscription au Conseil de l\'Ordre des Médecins',
        'gabon': 'Medical License Number',
        'gambia': 'Medical and Dental Registration Number',
        'gambia': 'Gambia Medical and Dental Registration Number',
        'georgia': 'Medical Registration Number',
        'germany': 'German Medical License Number',
        'ghana': 'Medical and Dental Council Registration Number',
        'greece': 'Greek Medical License Number',
        'grenada': 'Medical Registration Number',
        'guatemala': 'Colegio de Médicos Registration Number',
        'guinea': 'Medical Council License Number',
        'guinea-bissau': 'Medical License Number',
        'guyana': 'Medical Registration Number',
        'haiti': 'Haitian Medical Registration Number',
        'honduras': 'Colegio Médico Registration Number',
        'hungary': 'Hungarian Medical License Number',
        'iceland': 'Icelandic Medical Council Registration Number',
        'india': 'MCI Registration Number',
        'indonesia': 'Indonesian Medical License Number',
        'iran': 'Iranian Medical Council Registration Number',
        'iraq': 'Iraqi Medical License Number',
        'ireland': 'Irish Medical Council Registration Number',
        'israel': 'Israeli Medical License Number',
        'italy': 'Albo dei Medici Registration Number',
        'jamaica': 'Medical Council of Jamaica Registration Number',
        'japan': 'Japanese Medical License Number',
        'jordan': 'Jordan Medical Association Registration Number',
        'kazakhstan': 'Kazakh Medical License Number',
        'kenya': 'Kenya Medical Practitioners and Dentists Council Registration Number',
        'kiribati': 'Kiribati Medical Registration Number',
        'korea, north': 'North Korean Medical Registration Number',
        'korea, south': 'South Korean Medical License Number',
        'kosovo': 'Kosovo Medical License Number',
        'kuwait': 'Kuwait Medical License Number',
        'kyrgyzstan': 'Kyrgyz Medical License Number',
        'laos': 'Laos Medical License Number',
        'latvia': 'Latvian Medical Registration Number',
        'lebanon': 'Lebanese Medical Council Registration Number',
        'lesotho': 'Lesotho Medical Registration Number',
        'liberia': 'Liberian Medical License Number',
        'libya': 'Libyan Medical License Number',
        'liechtenstein': 'Liechtenstein Medical Registration Number',
        'lithuania': 'Lithuanian Medical License Number',
        'luxembourg': 'Luxembourg Medical License Number',
        'madagascar': 'Madagascar Medical Council Registration Number',
        'malawi': 'Malawi Medical Registration Number',
        'malaysia': 'Malaysian Medical Council Registration Number',
        'maldives': 'Maldives Medical License Number',
        'mali': 'Mali Medical License Number',
        'malta': 'Malta Medical Registration Number',
        'marshall islands': 'Marshall Islands Medical Registration Number',
        'mauritania': 'Mauritania Medical License Number',
        'mauritius': 'Mauritius Medical Council Registration Number',
        'mexico': 'Mexican Medical License Number',
        'moldova': 'Moldova Medical Registration Number',
        'monaco': 'Monaco Medical License Number',
        'mongolia': 'Mongolian Medical License Number',
        'montenegro': 'Montenegro Medical Registration Number',
        'morocco': 'Moroccan Medical License Number',
        'mozambique': 'Mozambique Medical License Number',
        'myanmar (formerly burma)': 'Myanmar Medical Registration Number',
        'namibia': 'Namibia Medical Registration Number',
        'nauru': 'Nauru Medical Registration Number',
        'nepal': 'Nepal Medical License Number',
        'netherlands': 'Dutch Medical Registration Number',
        'new zealand': 'New Zealand Medical Council Registration Number',
        'nicaragua': 'Nicaragua Medical Registration Number',
        'niger': 'Nigerian Medical Registration Number',
        'nigeria': 'Nigerian Medical License Number',
        'north macedonia': 'North Macedonian Medical License Number',
        'norway': 'Norwegian Medical License Number',
        'oman': 'Oman Medical Registration Number',
        'pakistan': 'PMDC Number',
        'palau': 'Palau Medical Registration Number',
        'panama': 'Panama Medical License Number',
        'papua new guinea': 'Papua New Guinea Medical Registration Number',
        'paraguay': 'Paraguay Medical License Number',
        'peru': 'Peru Medical License Number',
        'philippines': 'Philippine Medical License Number',
        'poland': 'Poland Medical License Number',
        'portugal': 'Portuguese Medical License Number',
        'qatar': 'Qatar Medical Registration Number',
        'romania': 'Romanian Medical License Number',
        'russia': 'Russian Medical License Number',
        'rwanda': 'Rwanda Medical License Number',
        'st kitts and nevis': 'St. Kitts and Nevis Medical Registration Number',
        'st lucia': 'Saint Lucia Medical License Number',
        'st vincent and the grenadines': 'St. Vincent and the Grenadines Medical License Number',
        'samoa': 'Samoa Medical License Number',
        'san marino': 'San Marino Medical Registration Number',
        'sao tome and principe': 'São Tomé and Príncipe Medical License Number',
        'saudi arabia': 'Saudi Medical Council Registration Number',
        'senegal': 'Senegal Medical License Number',
        'serbia': 'Serbia Medical License Number',
        'seychelles': 'Seychelles Medical Registration Number',
        'sierra leone': 'Sierra Leone Medical License Number',
        'singapore': 'Singapore Medical Registration Number',
        'slovakia': 'Slovak Medical License Number',
        'slovenia': 'Slovenian Medical Registration Number',
        'solomon islands': 'Medical License Number',
        'somalia': 'Medical License Number',
        'south africa': 'HPCSA Registration Number',
        'south sudan': 'Medical License Number',
        'spain': 'Medical Registration Number',
        'sri lanka': 'SLMC Registration Number',
        'sudan': 'Medical License Number',
        'suriname': 'Medical License Number',
        'sweden': 'Medical License Number',
        'switzerland': 'Swiss Medical License',
        'syria': 'Medical License Number',
        'taiwan': 'Taiwan Medical License',
        'tajikistan': 'Medical License Number',
        'tanzania': 'Medical Council of Tanzania Number',
        'thailand': 'Medical License Number',
        'timor-leste': 'Medical License Number',
        'togo': 'Medical License Number',
        'tonga': 'Medical License Number',
        'trinidad and tobago': 'Medical Registration Number',
        'tunisia': 'Medical License Number',
        'turkey': 'Turkish Medical License',
        'turkmenistan': 'Medical License Number',
        'tuvalu': 'Medical Registration Number',
        'uganda': 'UMDPC Registration Number',
        'ukraine': 'Medical Practitioner Registration Number',
        'united arab emirates': 'DHA/MOH License Number',
        'united kingdom': 'GMC Registration Number',
        'united states of america': 'State Medical License',
        'uruguay': 'Medical Practitioner License',
        'uzbekistan': 'Medical Registration Number',
        'vanuatu': 'Medical Council License',
        'vatican city': 'Holy See Medical Registration',
        'venezuela': 'Medical College Registration Number',
        'vietnam': 'Medical Practice Certificate Number',
        'yemen': 'Medical License Number',
        'zambia': 'HPCZ Registration Number',
        'zimbabwe': 'MDPCZ Registration Number'

                }
                return labels.get(country.lower(), 'Medical License')

            def get_id_label(country):
                labels = {
                    'afghanistan': 'Tazkira Number',
        'albania': 'National ID Number',
        'algeria': 'CIN (Carte d’Identité Nationale)',
        'andorra': 'National ID Number',
        'angola': 'Cartão de Cidadão',
        'antigua and barbuda': 'National Identification Number',
        'argentina': 'DNI (Documento Nacional de Identidad)',
        'armenia': 'Passport Number',
        'australia': 'Tax File Number',
        'austria': 'Social Security Number',
        'azerbaijan': 'Personal ID Number',
        'bahamas': 'National Insurance Number',
        'bahrain': 'National ID Number',
        'bangladesh': 'National ID Number',
        'barbados': 'National Registration Number',
        'belarus': 'Passport Number',
        'belgium': 'National Register Number',
        'belize': 'National ID Number',
        'benin': 'National ID Number',
        'bhutan': 'CID (Citizen Identification)',
        'bolivia': 'Carné de Identidad',
        'bosnia and herzegovina': 'JMBG (Unique Master Citizen Number)',
        'botswana': 'National ID Number',
        'brazil': 'CPF (Cadastro de Pessoas Físicas)',
        'brunei': 'National ID Number',
        'bulgaria': 'Personal Number',
        'burkina faso': 'National ID Number',
        'burundi': 'National ID Number',
        'cabo verde': 'Número de Identificação Pessoal',
        'cambodia': 'National ID Number',
        'cameroon': 'National ID Number',
        'canada': 'Social Insurance Number (SIN)',
        'central african republic': 'Carte Nationale d’Identité',
        'chad': 'National ID Number',
        'chile': 'RUT (Rol Único Tributario)',
        'china': 'Resident Identity Card Number',
        'colombia': 'Cédula de Ciudadanía',
        'comoros': 'National ID Number',
        'congo, democratic republic of the': 'National ID Number',
        'congo, republic of the': 'National ID Number',
        'costa rica': 'Cédula de Identidad',
        'croatia': 'OIB (Personal Identification Number)',
        'cuba': 'Carnet de Identidad',
        'cyprus': 'Civil Registry Number',
        'czech republic': 'Personal Identification Number',
        'denmark': 'CPR Number',
        'djibouti': 'National ID Number',
        'dominica': 'National ID Number',
        'dominican republic': 'Cédula de Identidad',
        'ecuador': 'Cédula de Identidad',
        'egypt': 'National ID Number',
        'el salvador': 'DUI (Documento Único de Identidad)',
        'equatorial guinea': 'Cédula de Identidad',
        'eritrea': 'National ID Number',
        'estonia': 'Personal Identification Code',
        'eswatini': 'National ID Number',
        'ethiopia': 'National ID Number',
        'federated states of micronesia': 'National ID Number',
        'fiji': 'National ID Number',
        'finland': 'Personal Identity Code',
        'france': 'Numéro d’Identité Nationale',
        'gabon': 'CNI (Carte Nationale d’Identité)',
        'gambia': 'National ID Number',
        'georgia': 'Personal ID Number',
        'germany': 'Personalausweis Nummer',
        'ghana': 'National ID Number',
        'greece': 'Social Security Number (AMKA)',
        'grenada': 'National ID Number',
        'guatemala': 'Cédula de Vecindad',
        'guinea': 'National ID Number',
        'guinea-bissau': 'NIN (National Identification Number)',
        'guyana': 'National ID Number',
        'haiti': 'National ID Number',
        'honduras': 'National ID Number',
        'hungary': 'Személyi Igazolvány (Personal ID)',
        'iceland': 'National ID Number',
        'india': 'Aadhaar Number',
        'indonesia': 'Nomor Induk Kependudukan (NIK)',
        'iran': 'National ID Number',
        'iraq': 'National ID Number',
        'ireland': 'Personal Public Service Number (PPSN)',
        'israel': 'Teudat Zehut Number',
        'italy': 'Codice Fiscale',
        'jamaica': 'National ID Number',
        'japan': 'My Number',
        'jordan': 'National ID Number',
        'kazakhstan': 'ID Number',
        'kenya': 'National ID Number',
        'kiribati': 'National ID Number',
        'korea, north': 'National ID Number',
        'korea, south': 'Resident Registration Number',
        'kosovo': 'Personal Identification Number',
        'kuwait': 'Civil ID Number',
        'kyrgyzstan': 'ID Number',
        'laos': 'National ID Number',
        'latvia': 'Personal ID Number',
        'lebanon': 'Personal ID Number',
        'lesotho': 'National ID Number',
        'liberia': 'National ID Number',
        'libya': 'National ID Number',
        'liechtenstein': 'Personal ID Number',
        'lithuania': 'Personal Identification Number',
        'luxembourg': 'National ID Number',
        'madagascar': 'National ID Number',
        'malawi': 'National ID Number',
        'malaysia': 'National ID Number',
        'maldives': 'National ID Number',
        'mali': 'National ID Number',
        'malta': 'National ID Number',
        'marshall islands': 'National ID Number',
        'mauritania': 'National ID Number',
        'mauritius': 'National ID Number',
        'mexico': 'CURP (Clave Única de Registro de Población)',
        'moldova': 'ID Number',
        'monaco': 'National ID Number',
        'mongolia': 'National ID Number',
        'pakistan': 'CNIC Number',
        'india': 'Aadhaar Number',
        'usa': 'Social Security Number',
        'montenegro': 'Personal ID Number',
        'morocco': 'CIN Number',
        'mozambique': 'Personal Identification Number',
        'myanmar (formerly burma)': 'National Registration Number',
        'namibia': 'National ID Number',
        'nauru': 'National ID Number',
        'nepal': 'Citizenship Number',
        'netherlands': 'BSN Number',
        'new zealand': 'IRD Number',
        'nicaragua': 'Nicaraguan ID Number',
        'niger': 'National ID Number',
        'nigeria': 'National Identification Number',
        'north macedonia': 'Personal ID Number',
        'norway': 'National ID Number',
        'oman': 'Civil ID Number',
        'palau': 'Palauan ID Number',
        'panama': 'Cedula Number',
        'papua new guinea': 'National ID Number',
        'paraguay': 'Cedula de Identidad',
        'peru': 'DNI (Documento Nacional de Identidad)',
        'philippines': 'Philippine National ID',
        'poland': 'PESEL Number',
        'portugal': 'Cartão de Cidadão Number',
        'qatar': 'Qatari ID Number',
        'romania': 'CNP (Personal Numeric Code)',
        'russia': 'SNILS Number',
        'rwanda': 'National ID Number',
        'st kitts and nevis': 'National ID Number',
        'st lucia': 'National ID Number',
        'st vincent and the grenadines': 'National ID Number',
        'samoa': 'Samoan ID Number',
        'san marino': 'San Marino ID Number',
        'sao tome and principe': 'National ID Number',
        'saudi arabia': 'National ID Number',
        'senegal': 'National ID Number',
        'serbia': 'JMBG (Unique Master Citizen Number)',
        'seychelles': 'National ID Number',
        'sierra leone': 'National ID Number',
        'singapore': 'NRIC Number',
        'slovakia': 'Rodné Číslo (Birth Number)',
        'slovenia': 'EMŠO Number',
        'solomon islands': 'National ID Number',
        'somalia': 'National ID Number',
        'south africa': 'ID Number',
        'south sudan': 'National ID Number',
        'spain': 'DNI (Documento Nacional de Identidad)',
        'sri lanka': 'NIC Number',
        'sudan': 'National ID Number',
        'suriname': 'National ID Number',
        'sweden': 'Personnummer (Personal Number)',
        'switzerland': 'AHV Number',
        'syria': 'National ID Number',
        'taiwan': 'National ID Number',
        'tajikistan': 'National ID Number',
        'tanzania': 'National ID Number',
        'thailand': 'ID Card Number',
        'timor-leste': 'ID Card Number',
        'togo': 'National ID Number',
        'tonga': 'National ID Number',
        'trinidad and tobago': 'National ID Number',
        'tunisia': 'National ID Number',
        'turkey': 'T.C. Kimlik No (Turkish ID Number)',
        'turkmenistan': 'National ID Number',
        'tuvalu': 'National ID Number',
        'uganda': 'National ID Number',
        'ukraine': 'Taxpayer Identification Number (TIN)',
        'united arab emirates': 'Emirates ID',
        'united kingdom': 'National Insurance Number',
        'united states of america': 'Social Security Number',
        'uruguay': 'Cédula de Identidad',
        'uzbekistan': 'Passport Number',
        'vanuatu': 'National ID Number',
        'vatican city': 'Personal ID Number',
        'venezuela': 'Cédula de Identidad',
        'vietnam': 'Citizen Identification Number',
        'yemen': 'National ID Number',
        'zambia': 'National Registration Card Number',
        'zimbabwe': 'National ID Number'
        

                }
                return labels.get(country.lower(), 'National ID')

            # Folder creation and file upload logic
            parent_folder_name = 'doctors'
            parent_folder_id = None

            query = f"name='{parent_folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            response = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            files = response.get('files', [])

            parent_folder_id = files[0]['id'] if files else create_folder(parent_folder_name)
            email_folder_id = create_folder(data['email'], parent_id=parent_folder_id)

            image_link = upload_to_drive(doctor_image.stream, secure_filename(doctor_image.filename), folder_id=email_folder_id)
            resume_link = upload_to_drive(doctor_resume.stream, secure_filename(doctor_resume.filename), folder_id=email_folder_id)

            data['profile_picture_url'] = image_link
            data['resume_url'] = resume_link
            data['timestamp'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

            # Save to Firestore
            doc_ref = db.collection('newDoctorRegistration').document(data['email'])
            doc_ref.set(data)

            sender = {"name": "HelloTabeeb", "email": "support@hellotabeeb.com"}

            # Send email to admin
            try:
                admin_html_content = f"""
                <html>
                    <body>
                        <h2>New Doctor Registration</h2>
                        <h3>Personal Information</h3>
                        <p><strong>Country:</strong> {data['country'].title()}</p>
                        <p><strong>Full Name:</strong> {data['full-name']}</p>
                        <p><strong>Email:</strong> {data['email']}</p>
                        <p><strong>Phone Number:</strong> {data['phone-number']}</p>
                        
                        <h3>Professional Details</h3>
                        <p><strong>{get_license_label(data['country'])}:</strong> {data['medical-license']}</p>
                        <p><strong>{get_id_label(data['country'])}:</strong> {data['national-id']}</p>
                        <p><strong>Specialty:</strong> {data.get('specialty', 'N/A')}</p>
                        <p><strong>Sub-specialty:</strong> {data.get('fcps-specialty') or data.get('allied-health-specialty', 'N/A')}</p>
                        <p><strong>Year of Graduation:</strong> {data.get('year-of-graduation', 'N/A')}</p>
                        
                        <h3>Practice Information</h3>
                        <p><strong>City:</strong> {data.get('city', 'N/A')}</p>
                        <p><strong>Consultation Fee:</strong> Rs. {data.get('fee', 'N/A')}</p>
                        
                        <h3>Uploaded Documents</h3>
                        <p><strong>Profile Picture:</strong> <a href="{data.get('profile_picture_url', '#')}">View Image</a></p>
                        <p><strong>Resume:</strong> <a href="{data.get('resume_url', '#')}">View Resume</a></p>
                        
                        <p><strong>Registration Timestamp:</strong> {data['timestamp']}</p>
                    </body>
                </html>
                """

                admin_email = SendSmtpEmail(
                    to=[{"email": "shahzad892@gmail.com"}],
                    sender=sender,
                    subject="New Doctor Registration",
                    html_content=admin_html_content
                )
                api_instance.send_transac_email(admin_email)

                # Send welcome email to doctor
                doctor_html_content = f"""
                <html>
                    <body>
                        <h2>Thank You for Joining HelloTabeeb!</h2>
                        
                        <p>Dear {data['full-name']},</p>
                        
                        <p>We are thrilled to welcome you to HelloTabeeb, Pakistan's leading healthcare platform connecting patients with trusted doctors like you. Thank you for signing up and becoming part of our mission to make quality healthcare accessible to everyone.</p>
                        
                        <p>At HelloTabeeb, we are committed to empowering healthcare professionals by:</p>
                        <ul>
                            <li>Offering a robust platform for patient referrals and consultations.</li>
                            <li>Enhancing your visibility through targeted marketing and promotions.</li>
                            <li>Helping you connect with patients in need of your expertise.</li>
                        </ul>
                        
                        <p>For more information about HelloTabeeb, visit our:</p>
                        <ul>
                            <li>Website: <a href="https://www.hellotabeeb.com">www.hellotabeeb.com</a></li>
                            <li>Facebook: <a href="https://www.facebook.com/hellotabeeb">www.facebook.com/hellotabeeb</a></li>
                            <li>YouTube: <a href="https://www.youtube.com/@hellotabeeb">www.youtube.com/@hellotabeeb</a></li>
                        </ul>
                        
                        <p>If you have any questions, feel free to reach out to our helpline at 0337-4373334.</p>
                        
                        <p>Additionally, we may invite you to record a short public service message video to educate the General Public about health topics in your area of expertise. This video will also help us promote your profile on HelloTabeeb, driving patient referrals for consultations.</p>
                        
                        <p>We're excited about the journey ahead and the positive impact we can create together in the healthcare landscape. Thank you for being a part of HelloTabeeb!</p>
                        
                        <p>Warm regards,<br>
                        Team HelloTabeeb<br>
                        <a href="https://www.hellotabeeb.com">www.hellotabeeb.com</a><br>
                        Helpline: 0337-4373334</p>
                    </body>
                </html>
                """

                doctor_email = SendSmtpEmail(
                    to=[{"email": data['email']}],
                    sender=sender,
                    subject="Thank You for Joining HelloTabeeb!",
                    html_content=doctor_html_content
                )
                api_instance.send_transac_email(doctor_email)
                
                logger.info(f"Emails sent successfully to admin and doctor {data['email']}")

            except ApiException as e:
                logger.error(f"Brevo API Exception when sending emails: {e}")
            except Exception as e:
                logger.error(f"Unexpected error when sending emails: {e}")

            return jsonify({"success": True, "message": "Doctor registered successfully."}), 200
        else:
            return jsonify({"success": False, "message": "File upload failed."}), 400
    except Exception as e:
        logger.error(f"Error registering doctor: {e}")
        return jsonify({"success": False, "message": "Failed to register doctor."}), 500



@main.route('/book', methods=['POST'])
def book():
    logger = logging.getLogger(__name__)
    try:
        name = request.form.get('patient-name', '').strip()
        phone = request.form.get('phone-number', '').strip()
        email = request.form.get('email', '').strip()
        selected_tests = request.form.getlist('selected-tests')
        lab = request.form.get('lab-select', '').strip()
        discount_type = request.form.get('discount-type', '').strip()  # Get the discount type
        
        # Input Validation
        if not name or not phone or not email:
            flash('All input fields are required.', 'error')
            logger.warning("Form submission with missing fields.")
            return redirect(url_for('main.index'))
        
        if not selected_tests:
            flash('Please select at least one test.', 'error')
            logger.warning("Form submission without selecting any tests.")
            return redirect(url_for('main.index'))
        
        db = firestore.client()
        
        # Check if user selected 12% discount
        is_twelve_percent = discount_type == '12'
        
        # Logic for different labs
        if lab == 'chughtai-lab':
            code, tests_details = move_code_to_availed(name, phone, email, selected_tests)
            if not code:
                flash('No available booking codes found.', 'error')
                return redirect(url_for('main.index'))
            
            # Pass the is_twelve_percent flag to send_email
            send_email(email, name, tests_details, code, "Chughtai Lab", is_twelve_percent=is_twelve_percent)
            
            # Store the discount type in availed codes collection
            current_month = datetime.utcnow().strftime('%m-%Y')
            availed_code_data = {
                'name': name,
                'phone': phone,
                'email': email,
                'lab': lab,
                'code': code,
                'tests': tests_details,
                'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                'discount_type': '12%' if is_twelve_percent else '20-30%'
            }
            db.collection('availedCodes').document(current_month).collection('details').document(code).set(availed_code_data)
            
            flash('Booking successful! A confirmation email has been sent.', 'success')
            logger.info(f"Chughtai Lab booking successful for user {email} with code {code} and discount type {discount_type}%")
        
        elif lab == 'idc-islamabad':
            code = 'IDC'
            tests_ref = db.collection('labs/IDC/tests')
            tests_details = []
            for test_id in selected_tests:
                test_doc = tests_ref.document(test_id).get()
                if test_doc.exists:
                    test_data = test_doc.to_dict()
                    tests_details.append({
                        'name': test_data.get('Name', 'N/A'),
                        'original_fee': f"Rs.{test_data.get('Fees', '0.00')}",
                        'discounted_fee': f"Rs.{test_data.get('Fees', '0.00')}"
                    })
            
            current_month = datetime.utcnow().strftime('%m-%Y')
            availed_code_data = {
                'name': name,
                'phone': phone,
                'email': email,
                'lab': lab,
                'code': code,
                'tests': tests_details,
                'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                'discount_type': '10%'
            }
            db.collection('availedCodes').document(current_month).collection('details').document(code).set(availed_code_data)
            send_email(email, name, tests_details, code, "IDC Islamabad", is_twelve_percent=False)  # IDC never gets 12% offer
            flash('IDC Lab booking successful! A confirmation email has been sent.', 'success')
            logger.info(f"IDC Lab booking successful for user {email}.")
        
        elif lab == 'dr-essa-lab':
            code = 'hellotabib'
            tests_ref = db.collection('labs/essa/tests')
            tests_details = []
            for test_id in selected_tests:
                test_doc = tests_ref.document(test_id).get()
                if test_doc.exists:
                    test_data = test_doc.to_dict()
                    tests_details.append({
                        'name': test_data.get('Name', 'N/A'),
                        'original_fee': f"Rs.{test_data.get('Fees', '0.00')}",
                        'discounted_fee': f"Rs.{test_data.get('Fees', '0.00')}"
                    })
            
            current_month = datetime.utcnow().strftime('%m-%Y')
            availed_code_data = {
                'name': name,
                'phone': phone,
                'email': email,
                'lab': lab,
                'code': code,
                'tests': tests_details,
                'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                'discount_type': '20%'
            }
            db.collection('availedCodes').document(current_month).collection('details').document(code).set(availed_code_data)
            send_email(email, name, tests_details, code, "Dr. Essa Lab", is_twelve_percent=False)  # Dr. Essa Lab never gets 12% offer
            flash('Essa Lab booking successful! A confirmation email has been sent.', 'success')
            logger.info(f"Essa Lab booking successful for user {email}.")
        
        elif lab == 'another-lab':
            code = 'HTB'
            tests_ref = db.collection('labs/excel/tests')
            tests_details = []
            for test_id in selected_tests:
                test_doc = tests_ref.document(test_id).get()
                if test_doc.exists:
                    test_data = test_doc.to_dict()
                    tests_details.append({
                        'name': test_data.get('Name', 'N/A'),
                        'original_fee': f"Rs.{test_data.get('Fees', '0.00')}",
                        'discounted_fee': f"Rs.{test_data.get('Fees', '0.00')}"
                    })
            
            current_month = datetime.utcnow().strftime('%m-%Y')
            availed_code_data = {
                'name': name,
                'phone': phone,
                'email': email,
                'lab': lab,
                'code': code,
                'tests': tests_details,
                'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                'discount_type': '15%'
            }
            db.collection('availedCodes').document(current_month).collection('details').document(code).set(availed_code_data)
            send_email(email, name, tests_details, code, "Excel Lab", is_twelve_percent=False)  # Excel Lab never gets 12% offer
            flash('Excel Lab booking successful! A confirmation email has been sent.', 'success')
            logger.info(f"Excel Lab booking successful for user {email}.")
        
        else:
            flash('Invalid lab selection.', 'error')
            logger.warning(f"Invalid lab selection: {lab}")
            return redirect(url_for('main.index'))
        
        return redirect(url_for('main.index'))
    
    except Exception as e:
        flash('An unexpected error occurred. Please try again later.', 'error')
        logger.error(f"Unexpected error during booking: {e}")
        return redirect(url_for('main.index'))

@main.route('/tests', methods=['GET'])
def get_tests():
    logger = logging.getLogger(__name__)
    try:
        # Attempt to get the Firestore client
        try:
            db = firestore.client()
        except Exception as init_error:
            logger.error(f"Error initializing Firestore: {init_error}")
            return jsonify([])

        # Map each lab to its Firestore subcollection path
        lab_collection_map = {
            'chughtai-lab': 'labs/chughtaiLab/tests',
            'idc-islamabad': 'labs/IDC/tests',
            'dr-essa-lab': 'labs/essa/tests',     # Added Dr. Essa Lab
            'another-lab': 'labs/excel/tests'     # Added Excel Lab
        }

        lab = request.args.get('lab', 'chughtai-lab')
        if lab not in lab_collection_map:
            logger.warning(f"Lab '{lab}' not recognized.")
            return jsonify([])

        collection_path = lab_collection_map[lab]
        logger.info(f"Fetching tests from collection path: {collection_path}")
        tests_ref = db.collection(collection_path)
        
        tests = []
        for doc in tests_ref.stream():
            data = doc.to_dict()
            data['id'] = doc.id
            tests.append(data)
        
        logger.info(f"Fetched {len(tests)} tests successfully for lab: {lab}.")
        return jsonify(tests)
    except Exception as e:
        logger.error(f"Error fetching tests: {e}")
        return jsonify([])
    
    

   