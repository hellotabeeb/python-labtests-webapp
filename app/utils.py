# utils.py
import os
import logging
from datetime import datetime
from brevo_python import Configuration, ApiClient, TransactionalEmailsApi, SendSmtpEmail
from brevo_python.rest import ApiException
from dotenv import load_dotenv
from . import db  # Import db from __init__.py

# Load environment variables from .env file
load_dotenv()

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Brevo Configuration
configuration = Configuration()

configuration.api_key['api-key'] = os.getenv('BREVO_API_KEY')

if not configuration.api_key['api-key']:
    logger.error("Brevo API key not found in environment variables.")
    raise ValueError("Brevo API key is missing.")



api_client = ApiClient(configuration)
api_instance = TransactionalEmailsApi(api_client)

def fetch_tests():
    """
    Fetches all tests from the 'labs/chughtaiLab/tests' subcollection in Firestore.
    """
    try:
        logger.info("Fetching tests from Firestore.")
        tests_ref = db.collection('labs').document('chughtaiLab').collection('tests')
        tests = []
        for doc in tests_ref.stream():
            test = doc.to_dict()
            test['id'] = doc.id  # Include document ID
            tests.append(test)
        logger.info(f"Fetched {len(tests)} tests successfully.")
        return tests
    except Exception as e:
        logger.error(f"Error fetching tests: {e}")
        return []

def move_code_to_availed(name, phone, email, selected_tests):
    """
    Assigns an available booking code to the user, deletes it from 'codes',
    and moves details to 'availedCodes'.
    """
    try:
        logger.info(f"Assigning booking code for user: {email}")

        # Access the top-level 'codes' collection
        codes_ref = db.collection('codes')
        code_docs = codes_ref.where('isUsed', '==', 'false').limit(1).get()

        if not code_docs:
            logger.warning("No available booking codes found.")
            return None, []

        code_doc = code_docs[0]
        code_data = code_doc.to_dict()
        code = code_data.get('code')

        if not code:
            logger.error(f"Code field missing in document ID: {code_doc.id}")
            return None, []

        logger.info(f"Fetched code: {code}")

        # Delete the code document from 'codes'
        codes_ref.document(code_doc.id).delete()
        logger.info(f"Deleted code {code} from 'codes' collection.")

        # Fetch selected test details
        tests_details = []
        tests_ref = db.collection('labs').document('chughtaiLab').collection('tests')
        for test_id in selected_tests:
            test_doc = tests_ref.document(test_id).get()
            if test_doc.exists:
                test_data = test_doc.to_dict()
                tests_details.append({
                    'name': test_data.get('Name', 'N/A'),
                    'fee': f"Rs.{test_data.get('Fees', '0.00')}"
                })
                logger.info(f"Fetched test: {test_data.get('Name', 'N/A')}")
            else:
                logger.warning(f"Test ID {test_id} not found.")

        # Add to top-level 'availedCodes' collection
        availed_ref = db.collection('availedCodes')
        availed_ref.add({
            'availableAt': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            'code': code,
            'testFee': ', '.join([test['fee'] for test in tests_details]),
            'testName': ', '.join([test['name'] for test in tests_details]),
            'userEmail': email,
            'userName': name,
            'userPhone': phone
        })
        logger.info(f"Moved code {code} to 'availedCodes' for user {email}.")

        return code, tests_details
    except Exception as e:
        logger.error(f"Error in move_code_to_availed: {e}")
        return None, []

def generate_email_template(name, tests_details, discount_code):
    """
    Generates the HTML email content using the provided template.
    """
    tests_html = ''.join([
        f"<li><strong>Test:</strong> {test['name']}</li>"
        f"<li><strong>Fee:</strong> {test['fee']}</li>"
        for test in tests_details
    ])

    return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">Lab Test Booking Confirmation</h2>
                <p>Dear {name},</p>
                <p>Thank you for booking your lab test with HelloTabeeb. Your booking has been confirmed.</p>
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0;">Booking Details:</h3>
                    <ul style="list-style-type: none; padding-left: 0;">
                        {tests_html}
                        <li style="margin-top: 10px;"><strong>Your Discount Code:</strong> 
                            <span style="background-color: #e9ecef; padding: 5px 10px; border-radius: 3px;">
                                {discount_code}
                            </span>
                        </li>
                    </ul>
                </div>
                <p><strong>Important:</strong> Please keep this code safe as it can only be used once.</p>
                <p>Please show this email at the lab during your visit.</p>
                <hr style="border-top: 1px solid #eee; margin: 20px 0;">
                <p style="color: #666; font-size: 14px;">
                    Best regards,<br>
                    HelloTabeeb Lab Services Team
                </p>
            </div>
        </body>
        </html>
    """

def send_email(email, name, tests_details, code):
    """
    Sends an email with the booking code and test details to the user using Brevo's transactional email API.
    """
    try:
        logger.info(f"Preparing to send email to {email} with code {code}.")

        sender = {"name": "HelloTabeeb", "email": "support@hellotabeeb.com"}  # Replace with your sender email
        to = [{"email": email}]
        
        html_content = generate_email_template(name, tests_details, code)
        
        send_smtp_email = SendSmtpEmail(
            to=to,
            sender=sender,
            subject="Your Lab Test Booking Confirmation",
            html_content=html_content
        )
        
        api_instance.send_transac_email(send_smtp_email)
        logger.info(f"Email sent successfully to {email} with code {code}.")
    except ApiException as e:
        logger.error(f"Brevo API Exception when sending email to {email}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error when sending email to {email}: {e}")