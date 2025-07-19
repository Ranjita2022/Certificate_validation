from dotenv import load_dotenv
import streamlit as st
import os
from PIL import Image
import google.generativeai as genai
import fitz  # PyMuPDF
import io
import cv2
import numpy as np
from pyzbar.pyzbar import decode
import requests
from bs4 import BeautifulSoup
import re
from rapidfuzz import fuzz
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import tempfile
import time
from PIL import Image as PILImage
import io
import base64

load_dotenv() #load environment variables from .env
genai.configure(api_key = os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def pdf_page_to_image(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc.load_page(0)  # first page
    pix = page.get_pixmap()
    img_data = pix.tobytes("png")
    image = Image.open(io.BytesIO(img_data))
    return image

def is_certificate(image):
    prompt = "Is this a certificate? Answer yes or no."
    response = model.generate_content([prompt, image])
    parts = response.candidates[0].content.parts
    text = ' '.join(part.text for part in parts).strip().lower()
    if "yes" in text:
        return True
    else:
        return False

def extract_certificate_info(image):
    prompt = "Extract all relevant information from this certificate."
    response = model.generate_content([prompt, image])
    parts = response.candidates[0].content.parts
    text = ' '.join(part.text for part in parts)
    return text

def print_url_to_pdf(url):
    options = Options()
    options.headless = True
    options.add_argument("--window-size=1920,1080")  # Larger viewport for better rendering
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--page-load-strategy=normal")  # Wait for complete page load
    driver = webdriver.Chrome(options=options)
    
    # Set page load timeout
    driver.set_page_load_timeout(60)  # 60 seconds timeout for page load
    try:
        driver.get(url)
        
        # Wait for initial page load
        time.sleep(5)
        
        # Wait for document ready state
        timeout = 30  # Maximum wait time
        start_time = time.time()
        while driver.execute_script("return document.readyState") != "complete":
            if time.time() - start_time > timeout:
                st.warning("Page load timeout - proceeding with current state")
                break
            time.sleep(0.5)
        
        # Wait for any JavaScript/AJAX to complete
        time.sleep(2)
        
        # Check for jQuery completion if available
        try:
            jquery_active = driver.execute_script("return typeof jQuery !== 'undefined' && jQuery.active === 0")
            if not jquery_active:
                # Wait for jQuery to complete
                start_time = time.time()
                while time.time() - start_time < 10:  # Max 10 seconds for AJAX
                    try:
                        if driver.execute_script("return typeof jQuery !== 'undefined' && jQuery.active === 0"):
                            break
                    except:
                        break
                    time.sleep(0.5)
        except:
            pass  # jQuery not available
          # Wait for any lazy-loaded images or content
        time.sleep(3)
        
        # Check for network idle (no active network requests)
        try:
            # Wait for network to be idle
            start_time = time.time()
            while time.time() - start_time < 10:  # Max 10 seconds
                # Check if there are any active network requests
                active_requests = driver.execute_script("""
                    return window.performance.getEntriesByType('navigation')[0].loadEventEnd > 0 &&
                           document.readyState === 'complete';
                """)
                if active_requests:
                    break
                time.sleep(0.5)
        except:
            pass
        
        # Scroll to ensure all content is loaded
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
          # Final wait to ensure everything is rendered
        time.sleep(2)
        
        # Additional checks for common loading indicators
        try:
            # Wait for any loading spinners to disappear
            loading_indicators = ['loading', 'spinner', 'loader', 'progress']
            for indicator in loading_indicators:
                elements = driver.find_elements(By.CLASS_NAME, indicator)
                if elements:
                    start_time = time.time()
                    while elements and time.time() - start_time < 15:
                        try:
                            # Check if loading elements are still visible
                            visible_loaders = [el for el in elements if el.is_displayed()]
                            if not visible_loaders:
                                break
                        except:
                            break
                        time.sleep(0.5)
                        elements = driver.find_elements(By.CLASS_NAME, indicator)
        except:
            pass
        
        # Wait for images to load
        try:
            driver.execute_script("""
                return new Promise((resolve) => {
                    const images = document.querySelectorAll('img');
                    let loadedImages = 0;
                    const totalImages = images.length;
                    
                    if (totalImages === 0) {
                        resolve();
                        return;
                    }
                    
                    images.forEach((img) => {
                        if (img.complete) {
                            loadedImages++;
                        } else {
                            img.onload = img.onerror = () => {
                                loadedImages++;
                                if (loadedImages === totalImages) {
                                    resolve();
                                }
                            };
                        }
                    });
                    
                    if (loadedImages === totalImages) {
                        resolve();
                    }
                });
            """)
        except:
            pass
        
        # Final pause to ensure rendering is complete
        time.sleep(1)
        
        # Print page to PDF
        pdf_data = driver.execute_cdp_cmd("Page.printToPDF", {
            "landscape": False,
            "displayHeaderFooter": False,
            "printBackground": True,
            "preferCSSPageSize": True,
            "paperWidth": 8.27,  # A4 width in inches
            "paperHeight": 11.69,  # A4 height in inches
            "marginTop": 0.4,
            "marginBottom": 0.4,
            "marginLeft": 0.4,
            "marginRight": 0.4
        })
        
        # Return PDF bytes
        return base64.b64decode(pdf_data['data'])
    finally:
        driver.quit()

def validate_certificate_url(url, extracted_info):
    try:
        # Log the validation URL for debugging purposes
        st.info(f"🔄 Validating certificate with URL: {url}")
        st.info("⏳ Loading validation page completely - this may take a moment...")
        
        # Print the validation page to PDF
        pdf_bytes = print_url_to_pdf(url)
        # Convert PDF to image using existing function
        image = pdf_page_to_image(pdf_bytes)
        # Extract info from PDF image using existing extract_certificate_info function
        extracted_text_from_pdf = extract_certificate_info(image)
        
        st.success("✅ Validation page loaded and converted to PDF successfully")
        
        # Use Gemini to compare certificate info with PDF data
        return validate_certificate_with_screenshot(extracted_info, extracted_text_from_pdf)
    except Exception as e:
        st.warning(f"Could not validate certificate URL {url}: {e}")
        return False

def decode_qr_code(image):
    # Convert PIL image to OpenCV format
    cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    # Resize image to 2x for better small QR code detection
    scale_factor = 2
    height, width = cv_image.shape[:2]
    resized_image = cv2.resize(cv_image, (width * scale_factor, height * scale_factor), interpolation=cv2.INTER_LINEAR)

    qr_data_set = set()

    # Define tile size and overlap
    tile_size = 300
    overlap = 50

    # Slide over the image in tiles with overlap
    for y in range(0, resized_image.shape[0], tile_size - overlap):
        for x in range(0, resized_image.shape[1], tile_size - overlap):
            tile = resized_image[y:y+tile_size, x:x+tile_size]
            decoded_objects = decode(tile)
            for obj in decoded_objects:
                qr_data_set.add(obj.data.decode('utf-8'))

    # Fallback: try decoding the whole resized image as well
    decoded_objects_full = decode(resized_image)
    for obj in decoded_objects_full:
        qr_data_set.add(obj.data.decode('utf-8'))

    return list(qr_data_set)

def validate_certificate_info_with_qr_code(certificate_info, qr_data):
    try:
        # Create a prompt for Gemini to check if certificate info matches QR data
        # Specifically instructing to ignore issuance dates and issuer organization
        prompt = f"""
        Compare these two texts:
        
        CERTIFICATE INFORMATION:
        {certificate_info}
        
        QR CODE DATA:
        {qr_data}
        
        IMPORTANT: Ignore differences in issuance dates, issue dates, and issuing organization/authority names.
        Focus on matching the certificate holder's name, certificate title/name, certificate ID/number, 
        and the general purpose or subject of certification.
        
        Does the QR code data match or validate the certificate information with these considerations?
        Answer only 'yes' or 'no' followed by a brief explanation of what matched and what didn't.
        """
        
        # Make API call to Gemini
        response = model.generate_content(prompt)
        response_text = ' '.join(part.text for part in response.candidates[0].content.parts).lower()
        
        # Log the comparison result
        st.write("QR Code validation result: " + response_text)
        
        # Check if response indicates a match
        if "yes" in response_text[:5]:  # check first few characters for yes
            return True
        else:
            return False
    except Exception as e:
        st.warning(f"Error comparing certificate with QR code data: {e}")
        return False

def validate_certificate_with_screenshot(certificate_info, pdf_text):
    try:
        # Create a prompt for Gemini to check if certificate info matches PDF data
        prompt = f"""
        Compare these two texts:
        
        CERTIFICATE INFORMATION:
        {certificate_info}
        
        VALIDATION PAGE PDF INFORMATION:
        {pdf_text}
        
        IMPORTANT: Ignore differences in formatting, layout, certificate ID/number and minor text variations.
        Focus on matching the key certificate details such as certificate holder's name, 
        certificate title/name, and course title/name.
        
        Does the validation page information confirm the authenticity of the certificate information?
        Answer only 'yes' or 'no' followed by a brief explanation of what matched and what didn't.
        """
        
        # Make API call to Gemini
        response = model.generate_content(prompt)
        response_text = ' '.join(part.text for part in response.candidates[0].content.parts).lower()
        
        # Log the comparison result
        st.write("URL validation result: " + response_text)
        
        # Check if response indicates a match
        if "yes" in response_text[:5]:  # check first few characters for yes
            return True
        else:
            return False
    except Exception as e:
        st.warning(f"Error comparing certificate with validation page: {e}")
        return False

def process_single_certificate(image, filename="Certificate"):
    """Process a single certificate and return results"""
    results = {
        'filename': filename,
        'is_certificate': False,
        'extracted_info': None,
        'qr_data': [],
        'validation_result': False,
        'validation_method': None,
        'error': None
    }
    
    try:
        # Check if it's a certificate
        if not is_certificate(image):
            results['error'] = "The file is not a certificate."
            return results
        
        results['is_certificate'] = True
        
        # Extract certificate information
        extracted_info = extract_certificate_info(image)
        results['extracted_info'] = extracted_info
        
        # Decode QR codes
        qr_data = decode_qr_code(image)
        results['qr_data'] = qr_data
        
        # Validation process (always performed)
        valid = False
        if qr_data:
            # Validate with QR code data
            combined_qr_data = "\n".join(qr_data)
            valid = validate_certificate_info_with_qr_code(extracted_info, combined_qr_data)
            results['validation_method'] = "QR Code"
        else:
            # Validate with URL
            url_pattern = r'((?:https?://)?(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:/[^\s]*)?)'
            urls = re.findall(url_pattern, extracted_info)
            
            for url in urls:
                if not url.startswith('http://') and not url.startswith('https://'):
                    url = 'http://' + url
                try:
                    from urllib.parse import urlparse
                    result = urlparse(url)
                    if all([result.scheme, result.netloc]):
                        if validate_certificate_url(url, extracted_info):
                            valid = True
                            results['validation_method'] = f"URL: {url}"
                            break
                except Exception:
                    continue
        
        results['validation_result'] = valid
        return results
        
    except Exception as e:
        results['error'] = str(e)
        return results

##Initialise streamlit app
st.set_page_config(page_title = "Certificate Extractor")
st.header("Certificate Extractor")

# Processing mode selector
processing_mode = st.radio(
    "Choose processing mode:",
    ["Single Certificate", "Batch Processing"],
    horizontal=True
)

if processing_mode == "Single Certificate":
    # Single certificate processing (existing functionality)
    uploaded_file = st.file_uploader("Choose a certificate image or PDF...", type=["jpg", "jpeg", "png", "pdf"])

    image = None
    if uploaded_file is not None:
        if uploaded_file.type == "application/pdf":
            pdf_bytes = uploaded_file.read()
            try:
                image = pdf_page_to_image(pdf_bytes)
                st.image(image, caption="Certificate Image (from PDF).")
            except Exception as e:
                st.error(f"Could not convert PDF to image: {e}")
        elif uploaded_file.type in ["image/jpeg", "image/png", "image/jpg"]:
            image = Image.open(uploaded_file)
            st.image(image, caption="Certificate Image.")
        else:
            st.error("Unsupported file type. Please upload an image or PDF.")

    submit = st.button("Extract Certificate Info")

    #If extract button is clicked
    if submit:
        if image is not None:
            with st.spinner("Processing certificate..."):
                results = process_single_certificate(image, uploaded_file.name if uploaded_file else "Certificate")
                
                if results['error']:
                    st.error(results['error'])
                else:
                    if results['qr_data']:
                        st.subheader("Decoded QR Code Data")
                        for idx, data in enumerate(results['qr_data']):
                            st.write(f"QR Code {idx+1}: {data}")
                    
                    st.subheader("Extracted Information")
                    st.write(results['extracted_info'])
                    
                    if results['validation_result']:
                        st.success(f"✅ Valid Certificate (Validated via: {results['validation_method']})")
                    else:
                        st.warning("⚠️ Certificate validation failed or no matching info found on validation site.")
        else:
            st.error("Please upload a valid certificate image or PDF file.")

else:
    # Batch processing mode
    st.subheader("Batch Certificate Processing")
    
    uploaded_files = st.file_uploader(
        "Choose multiple certificate images or PDFs...", 
        type=["jpg", "jpeg", "png", "pdf"],        accept_multiple_files=True
    )
    
    if uploaded_files:
        st.info(f"Selected {len(uploaded_files)} file(s) for processing")
        process_batch = st.button("🚀 Process All Certificates", type="primary")
        
        if process_batch:
            # Initialize progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Results storage
            all_results = []
            
            # Process each file
            for idx, uploaded_file in enumerate(uploaded_files):
                status_text.text(f"Processing {uploaded_file.name}...")
                progress_bar.progress((idx) / len(uploaded_files))
                
                try:
                    # Convert file to image
                    image = None
                    if uploaded_file.type == "application/pdf":
                        pdf_bytes = uploaded_file.read()
                        image = pdf_page_to_image(pdf_bytes)
                    elif uploaded_file.type in ["image/jpeg", "image/png", "image/jpg"]:
                        image = Image.open(uploaded_file)
                    
                    if image:
                        results = process_single_certificate(image, uploaded_file.name)
                        all_results.append(results)
                    else:
                        all_results.append({
                            'filename': uploaded_file.name,
                            'error': "Unsupported file type"
                        })
                        
                except Exception as e:
                    error_result = {
                        'filename': uploaded_file.name,
                        'error': str(e)
                    }
                    all_results.append(error_result)
              # Complete progress
            progress_bar.progress(1.0)
            status_text.text("Processing completed!")
            
            # Display results
            st.subheader("Batch Processing Results")
            
            # Summary statistics
            valid_count = sum(1 for r in all_results if r.get('validation_result') is True)
            invalid_count = sum(1 for r in all_results if r.get('validation_result') is False)
            certificate_count = sum(1 for r in all_results if r.get('is_certificate', False))
            error_count = sum(1 for r in all_results if r.get('error'))
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Files", len(all_results))
            col2.metric("Certificates", certificate_count)
            col3.metric("✅ Valid", valid_count)
            col4.metric("❌ Errors", error_count)
            
            # Detailed results
            for idx, result in enumerate(all_results):
                with st.expander(f"📄 {result['filename']}", expanded=False):
                    if result.get('error'):
                        st.error(f"❌ Error: {result['error']}")
                    elif not result.get('is_certificate'):
                        st.warning("⚠️ Not identified as a certificate")
                    else:
                        # QR Code data
                        if result.get('qr_data'):
                            st.write("**QR Code Data:**")
                            for qr_idx, data in enumerate(result['qr_data']):
                                st.write(f"QR Code {qr_idx+1}: {data}")
                          # Extracted information
                        st.write("**Extracted Information:**")
                        st.write(result['extracted_info'])
                        
                        # Validation result
                        if result['validation_result']:
                            st.success(f"✅ Valid Certificate (Validated via: {result['validation_method']})")
                        else:
                            st.warning("⚠️ Validation failed or no validation source found")
