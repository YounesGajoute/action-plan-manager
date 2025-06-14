#!/usr/bin/env python3
# ===================================================================
# scripts/import_excel.py - Excel Import Script
# ===================================================================

import sys
import os
import logging
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app import create_app, db
from app.models import User, SyncStatus
from app.services.excel_service import ExcelService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('import.log')
    ]
)
logger = logging.getLogger(__name__)

def create_system_user():
    """Create system user for import operations"""
    try:
        system_user = User.query.filter_by(email='system@techmac.ma').first()
        if not system_user:
            system_user = User(
                email='system@techmac.ma',
                name='System Import',
                roles=['admin'],
                department='IT',
                position='System'
            )
            db.session.add(system_user)
            db.session.commit()
            logger.info("System user created")
        return system_user
    except Exception as e:
        logger.error(f"Error creating system user: {str(e)}")
        return None

def validate_file_path(file_path):
    """Validate the provided file path"""
    if not file_path:
        logger.error("No file path provided")
        return False
    
    if not os.path.exists(file_path):
        logger.error(f"File does not exist: {file_path}")
        return False
    
    if not file_path.lower().endswith(('.xlsx', '.xls')):
        logger.error(f"Invalid file format. Expected .xlsx or .xls, got: {file_path}")
        return False
    
    return True

def print_usage():
    """Print usage instructions"""
    print("""
Usage: python scripts/import_excel.py <path_to_excel_file>

Examples:
    python scripts/import_excel.py data/Plan_daction.xlsx
    python scripts/import_excel.py /path/to/your/excel/file.xlsx

Options:
    --validate-only    Only validate the file without importing
    --dry-run         Show what would be imported without actually importing
    --help           Show this help message

The Excel file should have the following structure:
- Date: Task creation date (DD/MM/YYYY format)
- PO: Purchase Order number (optional)
- Catégorie: Task category (optional)
- Action: Task description (required)
- Colonne1: Additional information (optional)
- Customer: Customer name (required)
- Requester: Person who requested the task (required)
- Techmac Resp: Responsible person (required)
- Dead line: Task deadline (DD/MM/YYYY format, optional)
- Status: Task status (optional)
- Note: Additional notes (optional)
- Installation/F: Installation flag (optional)
- Réparation: Repair flag (optional)
- Développement: Development flag (optional)
- Livraison: Delivery flag (optional)
    """)

def validate_excel_structure(file_path):
    """Validate Excel file structure and show preview"""
    try:
        logger.info(f"Validating Excel file: {file_path}")
        
        # Validate file
        is_valid, message = ExcelService.validate_excel_file(file_path)
        
        if not is_valid:
            logger.error(f"File validation failed: {message}")
            return False
        
        logger.info("✓ File validation passed")
        
        # Show file preview
        from openpyxl import load_workbook
        workbook = load_workbook(file_path, read_only=True)
        sheet = workbook.active
        
        # Get headers
        headers = [cell.value for cell in sheet[1] if cell.value]
        logger.info(f"Headers found: {headers}")
        
        # Count rows
        row_count = sheet.max_row - 1  # Exclude header
        logger.info(f"Data rows: {row_count}")
        
        # Show sample data
        logger.info("Sample data (first 3 rows):")
        for row_num, row in enumerate(sheet.iter_rows(min_row=2, max_row=4, values_only=True), start=2):
            if any(row):
                row_data = dict(zip(headers, row))
                logger.info(f"Row {row_num}: {row_data}")
        
        workbook.close()
        return True
        
    except Exception as e:
        logger.error(f"Error validating Excel structure: {str(e)}")
        return False

def import_excel_file(file_path, dry_run=False):
    """Import Excel file into the database"""
    try:
        logger.info(f"Starting Excel import: {file_path}")
        logger.info(f"Dry run mode: {dry_run}")
        
        # Create system user
        system_user = create_system_user()
        if not system_user:
            logger.error("Failed to create system user")
            return False
        
        if dry_run:
            logger.info("DRY RUN MODE - No data will be imported")
            # Just validate and show what would be imported
            return validate_excel_structure(file_path)
        
        # Import the file
        start_time = datetime.now()
        result = ExcelService.import_from_excel(file_path, system_user.id)
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds()
        
        if result['success']:
            logger.info("✓ Import completed successfully!")
            logger.info(f"  Duration: {duration:.2f} seconds")
            logger.info(f"  Imported: {result['imported']} tasks")
            logger.info(f"  Updated: {result['updated']} tasks")
            logger.info(f"  Processed: {result.get('processed', 0)} rows")
            
            if result.get('errors'):
                logger.warning(f"  Errors: {len(result['errors'])}")
                for error in result['errors'][:5]:  # Show first 5 errors
                    logger.warning(f"    - {error}")
                if len(result['errors']) > 5:
                    logger.warning(f"    ... and {len(result['errors']) - 5} more errors")
            
            return True
        else:
            logger.error(f"✗ Import failed: {result.get('error', 'Unknown error')}")
            if result.get('errors'):
                for error in result['errors']:
                    logger.error(f"  - {error}")
            return False
            
    except Exception as e:
        logger.error(f"Error importing Excel file: {str(e)}")
        return False

def main():
    """Main function"""
    try:
        # Parse command line arguments
        if len(sys.argv) < 2 or '--help' in sys.argv:
            print_usage()
            return 0
        
        file_path = sys.argv[1]
        validate_only = '--validate-only' in sys.argv
        dry_run = '--dry-run' in sys.argv
        
        # Validate file path
        if not validate_file_path(file_path):
            return 1
        
        # Create Flask app context
        app = create_app()
        
        with app.app_context():
            logger.info("Starting Excel import script")
            logger.info(f"File: {file_path}")
            logger.info(f"Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
            
            # Ensure database tables exist
            try:
                db.create_all()
                logger.info("Database tables verified")
            except Exception as e:
                logger.error(f"Database error: {str(e)}")
                return 1
            
            if validate_only:
                logger.info("Validation only mode")
                if validate_excel_structure(file_path):
                    logger.info("✓ File validation completed successfully")
                    return 0
                else:
                    logger.error("✗ File validation failed")
                    return 1
            
            # Import the file
            if import_excel_file(file_path, dry_run):
                logger.info("✓ Script completed successfully")
                return 0
            else:
                logger.error("✗ Script failed")
                return 1
                
    except KeyboardInterrupt:
        logger.info("Import interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)