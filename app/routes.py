from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from .utils import send_email, fetch_tests, move_code_to_availed
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
        
        # Input Validation
        if not name or not phone or not email:
            flash('All input fields are required.', 'error')
            logger.warning("Form submission with missing fields.")
            return redirect(url_for('main.index'))
        
        if not selected_tests:
            flash('Please select at least one test.', 'error')
            logger.warning("Form submission without selecting any tests.")
            return redirect(url_for('main.index'))
        
        # Move code to availedCodes and get test details
        code, tests_details = move_code_to_availed(name, phone, email, selected_tests)
        
        if not code:
            flash('Sorry, no booking codes are available at the moment. Please try again later.', 'error')
            logger.error("Failed to assign a booking code.")
            return redirect(url_for('main.index'))
        
        # Send confirmation email
        send_email(email, name, tests_details, code)
        
        flash('Booking successful! A confirmation email has been sent.', 'success')
        logger.info(f"Booking successful for user {email} with code {code}.")
        return redirect(url_for('main.index'))
    
    except Exception as e:
        flash('An unexpected error occurred. Please try again later.', 'error')
        logger.error(f"Unexpected error during booking: {e}")
        return redirect(url_for('main.index'))

@main.route('/tests', methods=['GET'])
def get_tests():
    logger = logging.getLogger(__name__)
    try:
        tests = fetch_tests()
        logger.info("Fetched tests successfully.")
        return jsonify(tests)
    except Exception as e:
        logger.error(f"Error fetching tests: {e}")
        return jsonify({"error": "Failed to fetch tests."}), 500