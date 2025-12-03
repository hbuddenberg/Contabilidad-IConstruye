# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based automated accounting system called "Contabilidad IConstruye" that processes invoices from the IConstruye platform. The system performs web scraping, downloads documents, processes Excel files, and sends automated email notifications with PDF attachments for approval.

## Key Commands

### Running the Application
```bash
cd "Contabilidad/Contabilidad IConstruye"
python main.py
```

### Installing Dependencies
```bash
cd "Contabilidad/Contabilidad IConstruye"
pip install -r requirements.txt
```

### Virtual Environment
The project includes a Python virtual environment at `.venv/`. To activate:
```bash
cd "Contabilidad/Contabilidad IConstruye"
source .venv/bin/activate  # On macOS/Linux
```

### Development/Testing
- No specific test framework is configured
- Manual testing is done by running the main script
- Check the output logs for process status

## Architecture

### Core Components

**main.py**: Entry point that orchestrates the entire workflow:
- Loads configuration from config.yaml
- Reads Excel records for processing
- Manages web authentication and navigation
- Coordinates document downloading and email sending
- Handles Google Drive uploads and file archiving

**src/models/registro.py**: Defines the Registro dataclass that represents invoice records with fields like:
- rut_proveedor, razon_social, folio, fecha_docto, area
- Processing states: estado_folio, estado_descarga, estado_url_archivo
- File paths and URLs
- Google Drive integration fields

**src/services/**: Core business logic services
- **scraper.py**: Selenium-based web scraping for IConstruye platform authentication and navigation
- **reader.py**: Excel file processing and URL extraction
- **downloader.py**: PDF document downloading from extracted URLs
- **lectura.py**: Additional file reading utilities

**src/utils/**: Supporting utilities
- **grouping.py**: Groups records by area for email distribution
- **email_mapping.py**: Maps areas to email recipients and generates HTML content
- **email_sender.py**: Handles email sending via API

**src/google_drive/**: Google Drive integration
- **drive_oauth.py**: OAuth2 authentication and credential management
- **drive_upload.py**: File upload operations with folder structure organization
- **main.py**: Drive service interface and folder creation utilities

### Configuration

**config.yaml**: Central configuration file containing:
- Web scraping credentials and URLs for IConstruye platform
- ChromeDriver path and download directories
- Email configuration and templates
- Google Drive destination settings
- File paths for data processing

### Data Flow

1. **Input**: Excel files with invoice records are read from configured directory
2. **Authentication**: System logs into IConstruye platform using Selenium
3. **Navigation**: Automated navigation to invoice pages and document extraction
4. **Status Updates**: Each record is updated with found/not found status
5. **Download**: Excel files are downloaded and URLs extracted
6. **PDF Retrieval**: PDF documents are downloaded from extracted URLs
7. **Google Drive Upload**: Files are organized by date and company in Drive
8. **Grouping**: Records are grouped by area for email distribution
9. **Email Generation**: HTML emails are generated with invoice tables
10. **Delivery**: Emails with PDF attachments are sent to area recipients
11. **Archive**: Processed files are moved to date-stamped archive folders

### Dependencies

Core dependencies from pyproject.toml:
- **pyyaml**: Configuration file parsing
- **rich**: Terminal formatting and progress display
- **selenium**: Web browser automation for platform interaction
- **xlsx2csv**: Excel file processing
- **requests**: HTTP client for API calls
- **pandas**: Data manipulation and analysis
- **openpyxl**: Excel file handling
- **pydrive2**: Google Drive integration
- **pydantic**: Data validation and settings management
- **playwright**: Browser automation (alternative to Selenium)
- **google-auth\***: Google API authentication suite
- **google-api-python-client**: Google API client library

### Environment Setup

The project uses absolute paths in config.yaml that need to be adapted:
- ChromeDriver path for Selenium operations
- Download directories for file storage
- Email templates and configuration files
- Google Drive folder structure

### Important Notes

- ChromeDriver must be installed and configured in config.yaml
- Email credentials and platform credentials are stored in config.yaml
- The system processes files in batches and moves completed files to archive folders
- Google Drive integration creates folder structure: `SantaElena/IConstruye/Facturas/YYYY-MM-DD/[Empresa]/`
- Error handling includes retry logic for web scraping operations
- OAuth2 credentials for Google Drive are cached locally for subsequent runs