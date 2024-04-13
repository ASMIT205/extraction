from flask import Flask, request, jsonify
from PIL import Image
import pytesseract
import json
import os
import re
import PyPDF2
from datetime import datetime
from google.cloud import storage

app = Flask(__name__)

# Configure Tesseract executable path (update it according to your installation)
pytesseract.pytesseract.tesseract_cmd = '/home/gkumar/.local/bin/tesseract'
                                        #'myproject\.venv\Scripts\pytesseract.exe'
                                       # myproject\.venv\Lib\site-packages\pytesseract

# Define keyword lists for different categories
blood_report_keywords = ['KFT', 'ESR','ANGIOTENSIN CONVERTING ENZYME']
radiology_keywords = ['Echocardiography','CMR','Cardian MRI','PET','HRCT Chest','CMR', 'PET-CT Review',
                      'PET-CT Review Continued','USG ( ultrasound  ) Abdomen ( in case kidney written so abdomen )',
                      'USG - Abdomen & Pelvis','PSMA PET Scan','CEMRI Pelvis for Prostate', 'PSMA PET-CT',
                      'Bone Scan','MRI, Whole Spine','PET-CT','MRI Whole Spine','Right Mammogram', 
                      'MRI Lumbar Spine','CE-MRI Upper Abdomen','DOTANOC PET CT','CT Abdomen',
                      'CECT ( Contrast Enhanced  CT ) Abdomen continued','CE MRI - SELLA',
                      'Multiphase CT Abdomen','Ultrasound Abdomen','CECT WHOLE ABDOMEN']
pathology_keywords = ['Histopathology Report','FlowCytometry & Bone Marrow Aspiration ( BMA )']
previous_treatment_keywords = []





storage_client = storage.Client.from_service_account_json('project1-419908-856d7a3f35c7.json')

my_bucket = storage_client.get_bucket('extraction_medi')

def upload_to_bucket(blob_name,file_path,bucket_name):
    try:
        bucket = storage_client.get_bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(file_path)
        return True
    except Exception as e:
        print(e)
        return False


def generate_unique_filename(filename):
    # Split the filename and extension
    name, extension = os.path.splitext(filename)
    
    current_time = datetime.now()
    timestamp = current_time.strftime("%Y%m%d_%H%M%S")
    unique_filename = f"{name}_{timestamp}{extension}"
    return unique_filename


@app.route('/extract', methods=['POST'])
def extract_text_and_date():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    user_name = request.form.get('user_name')

    if not user_name:
        return jsonify({'error': 'Please provide your name'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    file_path = f'uploads/{user_name}_{file.filename}'
    file.save(file_path)
    unique_file_name = generate_unique_filename(file_path)

    #file_path =r'C:\Users\ASMIT\Desktop\Fundabox\extraction\extraction\aman_test_2.jpeg'
    upload_to_bucket(unique_file_name,file_path,'extraction_medi')

    extracted_text=''

    if file_path.lower().endswith('.pdf'):
        extracted_text=extract_text_from_pdf(file_path)
    else:
        extracted_text = extract_text_from_image(file_path)
    extracted_date = extract_date_from_text(extracted_text)
    test_name = create_test_name(extracted_text)
    write_to_master_json(user_name, extracted_text, extracted_date, test_name)
    return jsonify({'user_name': user_name, 'extracted_text': extracted_text, 'extracted_date': extracted_date, 'test_name': test_name})
def extract_text_from_pdf(pdf_path):
    try:
        print("PDF")
        text = ""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            num_pages = len(reader.pages)
            for page_num in range(num_pages):
                page = reader.pages[page_num]
                text += page.extract_text()
        return text
    except Exception as e:
        print("An error occurred during text extraction:", e)
        return None

def extract_text_from_image(image_path):
    # Use Tesseract OCR to extract text from the image
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img)
    return text

def extract_date_from_text(text):
    # Define a list of date patterns to look for in the text
    date_patterns = [
    r'\b(\d{1,2}/\d{1,2}/\d{4})\b',        # DD/MM/YYYY
    r'\b(\d{1,2}-[a-zA-Z]{3}-\d{4})\b',    # DD-MMM-YYYY
    r'\b(\d{1,2}/\d{1,2}/\d{2})\b',        # DD/MM/YY
    r'\b(\d{1,2} [a-zA-Z]+ \d{4})\b',      # DD Month YYYY
    r'\b(\d{1,2}-[a-zA-Z]{3}-\d{2})\b',    # DD-MMM-YY
    r'\b(\d{1,2} [a-zA-Z]+ \d{4})\b',      # DD Month YYYY
    r'\b(\d{1,2}-\d{2}-\d{4})\b',          # DD-MM-YYYY
    r'\b(\d{1,2}\.\d{2}\.\d{2})\b',        # DD.MM.YY
    r'\b(\d{1,2}/[a-zA-Z]+/\d{4})\b',      # DD/Month/YYYY
    r'\b(\d{2}/[a-zA-Z]+/\d{4})\b',        # MM/Month/YYYY
    r'\b(\d{1,2}/\d{1,2}/\d{2})\b',        # DD/MM/YY
    r'\b(\d{1,2}-[a-zA-Z]+-\d{2})\b',      # DD-Month-YY
    r'\b(\d{1,2} [a-zA-Z]+ \d{2})\b'       # DD Month YY
    ]

    # Try to match each pattern in the text
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            # If a match is found, return the matched date
            return match.group(1)

    # If no match is found, return a placeholder value
    return "Date not found"

def create_test_name(text):
    # Check for keywords in the extracted text and create test_name accordingly
    for keyword in blood_report_keywords:
        if keyword.lower() in text.lower():
            return f'B_{keyword}'

    for keyword in radiology_keywords:
        if keyword.lower() in text.lower():
            return f'R_{keyword}'

    for keyword in pathology_keywords:
        if keyword.lower() in text.lower():
            return f'P_{keyword}'

    for keyword in previous_treatment_keywords:
        if keyword.lower() in text.lower():
            return f'D_{keyword}'

    # If no keyword is found, return a default value
    return "Test_name_not_found"

def write_to_master_json(user_name, extracted_text, extracted_date, test_name):
    master_json_file_path = 'master_data_ocr.json'

    # Check if the master JSON file exists
    is_file_exist = os.path.isfile(master_json_file_path)

    # Read existing data from the file or initialize an empty list
    data_list = []
    if is_file_exist and os.path.getsize(master_json_file_path) > 0:
        with open(master_json_file_path, 'r') as jsonfile:
            try:
                data_list = json.load(jsonfile)
            except json.decoder.JSONDecodeError:
                # Handle the case where the file is not valid JSON
                pass

    # Append the new data to the list
    new_data = {'user_name': user_name, 'extracted_text': extracted_text, 'extracted_date': extracted_date,
                'test_name': test_name}
    data_list.append(new_data)

    # Write the updated list to the master JSON file
    with open(master_json_file_path, 'w') as jsonfile:
        json.dump(data_list, jsonfile, indent=2)

@app.route('/reports/<string:user_name>', methods=['GET'])
def get_user_reports(user_name):
    # Load data from the master data JSON file
    with open('master_data_ocr.json', 'r') as jsonfile:
        data = json.load(jsonfile)

    # Filter reports for the specified user
    user_reports = [report for report in data if report['user_name'] == user_name]
    extracted_data = [{'test_name': report['test_name'], 'extracted_date': report['extracted_date']} for report in user_reports]

    # Return the filtered reports as JSON response
    return jsonify(extracted_data)

if __name__ == '__main__':
    app.run(port=5000, debug=True)

