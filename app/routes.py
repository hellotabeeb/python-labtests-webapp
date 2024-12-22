from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from .utils import send_email, move_code_to_availed
from flask import current_app
import logging
import firebase_admin
from firebase_admin import firestore
from . import db
from firebase_admin import storage
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




main = Blueprint('main', __name__)

# Brevo Configuration
configuration = Configuration()
configuration.api_key['api-key'] = os.getenv('BREVO_API_KEY')
api_client = ApiClient(configuration)
api_instance = TransactionalEmailsApi(api_client)

@main.route('/')
def index():
    logger = logging.getLogger(__name__)
    logger.info("Index route accessed.")
    return render_template('index.html')


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
                to=[{"email": "ahadnaseer47@gmail.com"}],
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
                to = [{"email": "ahadnaseer47@gmail.com"}]
                
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
            # File handling functions remain the same
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
                        <p><strong>Full Name:</strong> {data['full-name']}</p>
                        <p><strong>Email:</strong> {data['email']}</p>
                        <p><strong>Phone Number:</strong> {data['phone-number']}</p>
                        
                        <h3>Professional Details</h3>
                        <p><strong>PMDC Number:</strong> {data.get('pmdc-number', 'N/A')}</p>
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
                    to=[{"email": "ahadnaseer47@gmail.com"}],
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
        
        # Logic for different labs
        if lab == 'chughtai-lab':
            code, tests_details = move_code_to_availed(name, phone, email, selected_tests)
            if not code:
                flash('No available booking codes found.', 'error')
                return redirect(url_for('main.index'))
            send_email(email, name, tests_details, code, "Chughtai Lab")
            flash('Booking successful! A confirmation email has been sent.', 'success')
            logger.info(f"Chughtai Lab booking successful for user {email} with code {code}.")
        
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
                        'discounted_fee': f"Rs.{float(test_data.get('Fees', '0.00')) * 0.9:.2f}"
                    })
            current_month = datetime.utcnow().strftime('%m-%Y')
            availed_code_data = {
                'name': name,
                'phone': phone,
                'email': email,
                'lab': lab,
                'code': code,
                'tests': tests_details,
                'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            }
            db.collection('availedCodes').document(current_month).collection('details').add(availed_code_data)
            logger.info(f"IDC booking data saved in availed codes collection for user {email}.")
            send_email(email, name, tests_details, code, "IDC Islamabad")
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
                        'discounted_fee': f"Rs.{float(test_data.get('Fees', '0.00')) * 0.8:.2f}"
                    })
            current_month = datetime.utcnow().strftime('%m-%Y')
            availed_code_data = {
                'name': name,
                'phone': phone,
                'email': email,
                'lab': lab,
                'code': code,
                'tests': tests_details,
                'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            }
            db.collection('availedCodes').document(current_month).collection('details').add(availed_code_data)
            logger.info(f"Essa Lab booking data saved in availed codes collection for user {email}.")
            send_email(email, name, tests_details, code, "Dr. Essa Lab")
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
                        'discounted_fee': f"Rs.{float(test_data.get('Fees', '0.00')) * 0.85:.2f}"
                    })
            current_month = datetime.utcnow().strftime('%m-%Y')
            availed_code_data = {
                'name': name,
                'phone': phone,
                'email': email,
                'lab': lab,
                'code': code,
                'tests': tests_details,
                'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            }
            db.collection('availedCodes').document(current_month).collection('details').add(availed_code_data)
            logger.info(f"Excel Lab booking data saved in availed codes collection for user {email}.")
            send_email(email, name, tests_details, code, "Excel Lab")
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