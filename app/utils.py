# utils.py
import os
import logging
from datetime import datetime
from brevo_python import Configuration, ApiClient, TransactionalEmailsApi, SendSmtpEmail
from brevo_python.rest import ApiException
from dotenv import load_dotenv
from datetime import datetime
from . import db  # Import db from __init__.py

# Load environment variables from .env file
load_dotenv()

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Brevo Configuration
configuration = Configuration()

configuration.api_key['api-key'] = os.getenv('BREVO_API_KEY')

# Replace line 19 with:

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

def move_code_to_availed(name, phone, email, selected_tests, discount_type=None):
    try:
        logger.info(f"Assigning booking code for user: {email} with discount type: {discount_type}")

        # Select the appropriate codes collection based on discount type
        if discount_type == '30':
            # Use codes11 collection for 30% discount
            codes_ref = db.collection('codes11')
            logger.info("Using codes11 collection for 30% discount")
        else:
            # Use default codes collection
            codes_ref = db.collection('codes')
            logger.info("Using default codes collection")

        code_docs = codes_ref.where('isUsed', '==', 'false').limit(1).get()

        if not code_docs:
            logger.warning(f"No available booking codes found in collection: {'codes11' if discount_type == '30' else 'codes'}")
            return None, []

        code_doc = code_docs[0]
        code_data = code_doc.to_dict()
        code = code_data.get('code')

        if not code:
            logger.error(f"Code field missing in document ID: {code_doc.id}")
            return None, []

        logger.info(f"Fetched code: {code}")

        # Delete the code document from the appropriate collection
        codes_ref.document(code_doc.id).delete()
        logger.info(f"Deleted code {code} from collection.")

        # Define discount percentage based on lab
        DISCOUNT_PERCENTAGE = 10  # Default discount
        if 'essaLab' in selected_tests:
            DISCOUNT_PERCENTAGE = 20
        elif 'excelLab' in selected_tests:
            DISCOUNT_PERCENTAGE = 15

        # Fetch selected test details
        tests_details = []
        tests_ref = db.collection('labs').document('chughtaiLab').collection('tests')
        for test_id in selected_tests:
            test_doc = tests_ref.document(test_id).get()
            if test_doc.exists:
                test_data = test_doc.to_dict()
                original_fee = float(test_data.get('Fees', '0.00'))
                discounted_fee = original_fee * (1 - DISCOUNT_PERCENTAGE / 100)
                tests_details.append({
                    'name': test_data.get('Name', 'N/A'),
                    'original_fee': f"Rs.{original_fee:.2f}",
                    'discounted_fee': f"Rs.{discounted_fee:.2f}"
                })
                logger.info(f"Fetched test: {test_data.get('Name', 'N/A')}")
            else:
                logger.warning(f"Test ID {test_id} not found.")

        # Get the current month and year
        current_month = datetime.utcnow().strftime('%m-%Y')

        # Add to 'availedCodes' collection under the current month
        availed_ref = db.collection('availedCodes').document(current_month).collection('details')
        availed_ref.document(code).set({
            'availableAt': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            'code': code,
            'testFee': ', '.join([test['original_fee'] for test in tests_details]),
            'discountedTestFee': ', '.join([test['discounted_fee'] for test in tests_details]),
            'testName': ', '.join([test['name'] for test in tests_details]),
            'userEmail': email,
            'userName': name,
            'userPhone': phone
        })
        logger.info(f"Moved code {code} to 'availedCodes/{current_month}/details' for user {email}.")

        return code, tests_details
    except Exception as e:
        logger.error(f"Error in move_code_to_availed: {e}")
        return None, []

def generate_email_template(name, tests_details, discount_code, lab_name, is_twelve_percent=False, specific_code=None):
    """
    Generates the HTML email content using the provided template.
    Includes special 12% discount offer messaging when applicable.
    """
    tests_html = ''.join([
        f"""
        <li>
            <strong>Test:</strong> {test['name']}<br>
            <strong>Fee:</strong> <span style="text-decoration: line-through; color: #a0a0a0;">{test['original_fee']}</span>
            <span style="color: #e74c3c; font-weight: bold;"> {test['discounted_fee']}</span>
        </li>
        """
        for test in tests_details
    ])

    # Add specific handling for IDC code
    if discount_code == 'IDC':
        code_section = "<p><strong>Your lab test code: IDC</strong></p>"
    else:
        code_section = f"<p><strong>Your code: {discount_code}</strong></p>"
    
    # Enhanced special offer section for 12% discount customers
    special_offer_section = ""
    if is_twelve_percent:
        special_offer_section = f"""
        <div style="background: linear-gradient(135deg, #f6d365 0%, #fda085 100%); 
                    padding: 25px; 
                    border-radius: 15px; 
                    margin: 30px 0; 
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
            <div style="background: rgba(255,255,255,0.95);
                        padding: 20px;
                        border-radius: 10px;
                        border: 2px dashed #ff6b6b;">
                
                <div style="text-align: center; margin-bottom: 20px;">
                    <h3 style="color: #ff6b6b; 
                               font-size: 24px; 
                               margin: 0;
                               text-transform: uppercase;
                               letter-spacing: 1px;">
                        🎉 Exclusive VIP Offer 🎉
                    </h3>
                </div>

                <div style="color: #2d3436; line-height: 1.6;">
                    <p style="font-size: 16px; margin: 10px 0;">
                        Congratulations! As our valued 12% discount customer, you've unlocked these premium benefits:
                    </p>
                    
                    <ul style="list-style: none; 
                               padding: 0; 
                               margin: 20px 0;">
                        <li style="margin: 12px 0;
                                   padding: 10px 15px;
                                   background: #fff;
                                   border-radius: 8px;
                                   border-left: 4px solid #ff6b6b;
                                   box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                            ✨ <strong>Additional Lab Test Discounts</strong>
                        </li>
                        <li style="margin: 12px 0;
                                   padding: 10px 15px;
                                   background: #fff;
                                   border-radius: 8px;
                                   border-left: 4px solid #ff6b6b;
                                   box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                            🎯 <strong>1 FREE Medical Consultation</strong> (Worth Rs. 1000)
                        </li>
                    </ul>

                    <div style="background: #2d3436;
                               color: white;
                               padding: 15px;
                               border-radius: 8px;
                               text-align: center;
                               margin: 25px 0 15px 0;">
                        <p style="font-weight: bold; 
                                  font-size: 18px; 
                                  margin: 0 0 10px 0;">
                            To Claim Your VIP Benefits:
                        </p>
                        <p style="font-size: 20px; 
                                  margin: 0;
                                  color: #ffd32a;">
                            Call or WhatsApp: <strong>+92 335 1626806</strong>
                        </p>
                        <p style="font-size: 14px;
                                  color: #dfe6e9;
                                  margin: 10px 0 0 0;">
                            Use code: "<strong>{specific_code}</strong>" when contacting us
                        </p>
                    </div>
                    
                    <p style="text-align: center;
                              font-size: 14px;
                              color: #636e72;
                              margin: 15px 0 0 0;">
                        * Offer valid for limited time only. Terms and conditions apply.
                    </p>
                </div>
            </div>
        </div>
        """

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
                        </ul>
                    </div>
                    {code_section}
                    <p>Your lab test is booked with {lab_name}</p>
                    
                    {special_offer_section}
                    
                    <!-- Book Again Button -->
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="https://hellotabeeb.pk" 
                           style="background-color: #2c3e50; 
                                  color: white; 
                                  padding: 12px 30px; 
                                  text-decoration: none; 
                                  border-radius: 5px; 
                                  font-weight: bold;
                                  display: inline-block;
                                  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                                  transition: background-color 0.3s ease;">
                            Book Again
                        </a>
                    </div>
    
                    <!-- Support Information -->
                    <div style="text-align: center; margin-top: 30px; padding: 20px; border-top: 1px solid #eee;">
                        <p style="margin: 0;">For support or to Book Home sampling, please call us at</p>
                        <p style="font-size: 18px; font-weight: bold; color: #2c3e50; margin: 10px 0;">0337 4373334</p>
                        <p style="margin: 0;">ThankYou!</p>
                    </div>
    
                    <!-- Show this mail at the Lab -->
                    <div style="text-align: center; margin-top: 30px; padding: 20px; border-top: 1px solid #eee;">
                        <p style="font-size: 20px; font-weight: bold; color: #2c3e50; margin: 10px 0;">
                            Show this mail at the Lab during your visit or home sampling to avail discount
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """

def calculate_discounted_fee(test):
    special_tests = ["Lipid Profile", "Serum 25-OH Vitamin D", "Glycosylated Hemoglobin (HbA1c)"]
    discount_rate = 0.3 if test['name'] in special_tests else 0.2
    original_fee = float(test['original_fee'].replace('Rs.', ''))
    discounted_fee = original_fee * (1 - discount_rate)
    return f"Rs.{discounted_fee:.2f}"


def send_email(email, name, tests_details, code, lab_name, is_twelve_percent=False):
    """
    Sends an email with the booking code and test details to the user using Brevo's transactional email API.
    Now includes support for 12% discount special offers.
    """
    try:
        logger.info(f"Preparing to send email to {email} with code {code}.")

        sender = {"name": "HelloTabeeb", "email": "support@hellotabeeb.com"}
        to = [{"email": email}]
        
        # Fetch a specific code from "cashback discount codes" collection
        specific_code = None
        if is_twelve_percent:
            cashback_ref = db.collection('cashback discount codes')
            cashback_docs = cashback_ref.limit(1).get()
            if cashback_docs:
                cashback_doc = cashback_docs[0]
                specific_code = cashback_doc.to_dict().get('code')
                cashback_ref.document(cashback_doc.id).delete()
                # Save to "used12%" collection
                used12_ref = db.collection('used12%')
                used12_ref.add({
                    'code': specific_code,
                    'userEmail': email,
                    'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                })
        
        html_content = generate_email_template(name, tests_details, code, lab_name, is_twelve_percent, specific_code)
        
        send_smtp_email = SendSmtpEmail(
            to=to,
            sender=sender,
            subject="Your Lab Test Booking Confirmation",
            html_content=html_content
        )
        
        api_instance.send_transac_email(send_smtp_email)
        logger.info(f"Email sent successfully to {email} with code {code}.")

        # Send email to admin
        admin_email = "bookings@hellotabeeb.com"
        admin_html_content = f"""
        <html>
            <body>
                <h2>New Lab Test Booking</h2>
                <h3>User Details</h3>
                <p><strong>Name:</strong> {name}</p>
                <p><strong>Email:</strong> {email}</p>
                <p><strong>Lab:</strong> {lab_name}</p>
                <p><strong>Code:</strong> {code}</p>
                <p><strong>Tests:</strong></p>
                <ul>
                    {''.join([f"<li>{test['name']} - Original Fee: {test['original_fee']}, Discounted Fee: {test['discounted_fee']}</li>" for test in tests_details])}
                </ul>
                <p><strong>Timestamp:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Specific Code:</strong> {specific_code}</p>
            </body>
        </html>
        """

        admin_send_smtp_email = SendSmtpEmail(
            to=[{"email": admin_email}],
            sender=sender,
            subject="New Lab Test Booking - HelloTabeeb",
            html_content=admin_html_content
        )
        
        api_instance.send_transac_email(admin_send_smtp_email)
        logger.info(f"Admin notification email sent for booking by {email}")

    except ApiException as e:
        logger.error(f"Brevo API Exception when sending email to {email}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error when sending email to {email}: {e}")
