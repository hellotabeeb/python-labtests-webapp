from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from .utils import send_email, move_code_to_availed
from flask import current_app as app
import logging

main = Blueprint('main', __name__)

@main.route('/')
def index():
    logger = logging.getLogger(__name__)
    logger.info("Index route accessed.")
    return render_template('index.html')

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
        
        # Logic for different labs
        if lab == 'chughtai-lab':
            # Existing Chughtai Lab logic
            code, tests_details = move_code_to_availed(name, phone, email, selected_tests)
            
            if not code:
                flash('Sorry, no booking codes are available at the moment. Please try again later.', 'error')
                logger.error("Failed to assign a booking code.")
                return redirect(url_for('main.index'))
            
            # Send confirmation email
            send_email(email, name, tests_details, code)
            
            flash('Booking successful! A confirmation email has been sent.', 'success')
            logger.info(f"Chughtai Lab booking successful for user {email} with code {code}.")
        
        elif lab == 'idc-islamabad':
            # New IDC Lab logic
            # Use 'IDC' as the default code for IDC lab
            code = 'IDC'
            
            # Fetch test details for selected IDC tests
            db = app.db
            tests_ref = db.collection('labs/IDC/tests')
            tests_details = []
            
            for test_id in selected_tests:
                test_doc = tests_ref.document(test_id).get()
                if test_doc.exists:
                    test_data = test_doc.to_dict()
                    tests_details.append({
                        'name': test_data.get('Name', 'N/A'),
                        'original_fee': f"Rs.{test_data.get('Fees', '0.00')}",
                        'discounted_fee': f"Rs.{float(test_data.get('Fees', '0.00')) * 0.9:.2f}"  # 10% discount
                    })
                    logger.info(f"Fetched IDC test: {test_data.get('Name', 'N/A')}")
                else:
                    logger.warning(f"IDC Test ID {test_id} not found.")
            
            # Send IDC specific email
            send_email(email, name, tests_details, code)
            
            flash('IDC Lab booking successful! A confirmation email has been sent.', 'success')
            logger.info(f"IDC Lab booking successful for user {email}.")
        
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
        # Get the lab parameter from the query string
        lab = request.args.get('lab', 'chughtai-lab')
        
        # Mapping lab selection to Firestore collection
        lab_collection_map = {
            'chughtai-lab': 'labs/chughtaiLab/tests',
            'idc-islamabad': 'labs/IDC/tests'
        }
        
        # Validate lab selection
        if lab not in lab_collection_map:
            logger.warning(f"Invalid lab selection: {lab}")
            return jsonify({"error": "Invalid lab selection"}), 400
        
        # Get Firestore instance
        db = app.db
        
        # Fetch tests from the specific lab's collection
        collection_path = lab_collection_map[lab]
        logger.info(f"Fetching tests from collection path: {collection_path}")
        tests_ref = db.collection(collection_path)
        tests = []
        for doc in tests_ref.stream():
            test = doc.to_dict()
            test['id'] = doc.id  # Include document ID
            tests.append(test)
            logger.info(f"Fetched test: {test}")
        
        logger.info(f"Fetched {len(tests)} tests successfully for lab: {lab}.")
        return jsonify(tests)
    except Exception as e:
        logger.error(f"Error fetching tests for lab {lab}: {e}")
        return jsonify({"error": "Failed to fetch tests."}), 500