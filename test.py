from flask import Flask, request, jsonify
from flask_cors import CORS  # Import the CORS library
from PIL import Image
import pytesseract
import json
import os
import re
import PyPDF2

app = Flask(__name__)
CORS(app)  # Enable CORS on the Flask app

# Define keyword lists for different categories
blood_report_keywords = ['KFT', 'ESR', 'ANGIOTENSIN CONVERTING ENZYME']
radiology_keywords = [
    'Echocardiography', 'CMR', 'Cardian MRI', 'PET', 'HRCT Chest', 'CMR', 'PET-CT Review',
    'PET-CT Review Continued', 'USG (ultrasound) Abdomen (in case kidney written so abdomen)',
    'USG - Abdomen & Pelvis', 'PSMA PET Scan', 'CEMRI Pelvis for Prostate', 'PSMA PET-CT',
    'Bone Scan', 'MRI, Whole Spine', 'PET-CT', 'MRI Whole Spine', 'Right Mammogram',
    'MRI Lumbar Spine', 'CE-MRI Upper Abdomen', 'DOTANOC PET CT', 'CT Abdomen',
    'CECT (Contrast Enhanced CT) Abdomen continued', 'CE MRI - SELLA',
    'Multiphase CT Abdomen', 'Ultrasound Abdomen', 'CECT WHOLE ABDOMEN'
]
pathology_keywords = ['Histopathology Report', 'FlowCytometry & Bone Marrow Aspiration (BMA)']
previous_treatment_keywords = []  # Populate this list as needed

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
    #checking file format
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
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img)
    return text

def extract_date_from_text(text):
    date_patterns = [
        # Add your date patterns here
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return "Date not found"

def create_test_name(text):
    for keyword in blood_report_keywords:
        if keyword.lower() in text.lower():
            return f'B_{keyword}'
    for keyword in radiology_keywords:
        if keyword.lower() in text.lower():
            return f'R_{keyword}'
    for keyword in pathology_keywords:
        if keyword.lower() in text.lower():
            return f'P_{keyword}'
    return "Test_name_not_found"

def write_to_master_json(user_name, extracted_text, extracted_date, test_name):
    master_json_file_path = 'master_data_ocr.json'
    data_list = []
    if os.path.isfile(master_json_file_path):
        with open(master_json_file_path, 'r') as jsonfile:
            data_list = json.load(jsonfile)
    new_data = {
        'user_name': user_name, 'extracted_text': extracted_text,
        'extracted_date': extracted_date, 'test_name': test_name
    }
    data_list.append(new_data)
    with open(master_json_file_path, 'w') as jsonfile:
        json.dump(data_list, jsonfile, indent=2)

@app.route('/reports/<string:user_name>', methods=['GET'])
def get_user_reports(user_name):
    with open('master_data_ocr.json', 'r') as jsonfile:
        data = json.load(jsonfile)
    user_reports = [report for report in data if report['user_name'] == user_name]
    extracted_data = [{'test_name': report['test_name'], 'extracted_date': report['extracted_date']} for report in user_reports]
    return jsonify(extracted_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    # extract_text_and_date()
