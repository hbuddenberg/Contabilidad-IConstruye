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

**src/models/registro.py**: Defines the Registro dataclass that represents invoice records with fields like:
- rut_proveedor, razon_social, folio, fecha_docto, area
- Processing states: estado_folio, estado_descarga, estado_url_archivo
- File paths and URLs

**src/services/**: Core business logic services
- **scraper.py**: Selenium-based web scraping for IConstruye platform authentication and navigation
- **reader.py**: Excel file processing and URL extraction
- **downloader.py**: PDF document downloading from extracted URLs
- **lectura.py**: Additional file reading utilities

**src/utils/**: Supporting utilities
- **grouping.py**: Groups records by area for email distribution
- **email_mapping.py**: Maps areas to email recipients and generates HTML content
- **email_sender.py**: Handles email sending via API

### Configuration

**config.yaml**: Central configuration file containing:
- Web scraping credentials and URLs
- ChromeDriver path and download directories
- Email configuration and templates
- File paths for data processing

### Data Flow

1. **Input**: Excel files with invoice records are read from configured directory
2. **Processing**: System logs into IConstruye platform, navigates to invoice pages
3. **Status Updates**: Each record is updated with found/not found status
4. **Download**: Excel files are downloaded and URLs extracted
5. **PDF Retrieval**: PDF documents are downloaded from extracted URLs
6. **Grouping**: Records are grouped by area for distribution
7. **Email Generation**: HTML emails are generated with invoice tables
8. **Delivery**: Emails with PDF attachments are sent to area recipients
9. **Archive**: Processed files are moved to date-stamped archive folders

### Dependencies

- **selenium**: Web browser automation for platform interaction
- **xlsx2csv**: Excel file processing
- **yaml**: Configuration file parsing
- **smtplib/email**: Email sending functionality
- Standard library modules for file operations and data handling

### Important Notes

- The system uses hardcoded Windows paths in config.yaml - these need to be updated for different environments
- ChromeDriver must be installed and configured in config.yaml
- Email credentials and platform credentials are stored in config.yaml
- The system processes files in batches and moves completed files to archive folders
- Error handling includes retry logic for web scraping operations
