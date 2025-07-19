# Certificate Validator

A comprehensive certificate validation tool that can process single certificates or multiple certificates in batch mode.

## Features

### Single Certificate Processing
- Upload individual certificate images (JPG, PNG) or PDF files
- Automatic certificate detection using AI
- Information extraction from certificates
- QR code detection and validation
- URL-based validation (prints validation pages to PDF for better extraction)
- Real-time validation results

### Batch Processing
- Upload and process multiple certificates simultaneously
- Progress tracking with real-time status updates
- Comprehensive results summary with statistics
- Individual file processing results with detailed information
- Export options:
  - JSON format (complete results with extracted information)
  - CSV format (summary statistics)
- Processing options:
  - Skip validation for faster processing
  - Continue processing on errors
- File size information and validation

## Validation Methods

1. **QR Code Validation**: Compares certificate information with embedded QR code data
2. **URL Validation**: 
   - Extracts validation URLs from certificates
   - Prints validation pages to PDF for better text extraction
   - Compares certificate details with validation page content

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your Google API key in a `.env` file:
```
GOOGLE_API_KEY=your_google_api_key_here
```

3. Install Chrome WebDriver for URL validation

## Usage

1. Run the application:
```bash
streamlit run certificate_extractor.py
```

2. Choose processing mode:
   - **Single Certificate**: Process one certificate at a time
   - **Batch Processing**: Process multiple certificates simultaneously

3. Upload your certificate files

4. Configure processing options (for batch mode):
   - Skip validation for faster processing
   - Continue on errors to process all files

5. Click process and view results

## Output

### Single Certificate
- Certificate validity status
- Extracted information
- QR code data (if present)
- Validation results

### Batch Processing
- Summary statistics (total files, valid certificates, errors)
- Individual file results with detailed information
- Downloadable reports in JSON and CSV formats

## Supported File Types
- Images: JPG, JPEG, PNG
- Documents: PDF (first page is processed)

## Requirements
- Python 3.7+
- Google Generative AI API key
- Chrome browser (for URL validation)
