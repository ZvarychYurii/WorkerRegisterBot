import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import json

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    logging.warning("gspread not available - Google Sheets integration disabled")

logger = logging.getLogger(__name__)

class GoogleSheetsManager:
    def __init__(self):
        self.gc = None
        self.sheet = None
        self.worksheet = None
        self.initialized = False
        self._init_task = None
        
        if GSPREAD_AVAILABLE:
            # Don't create task in __init__, wait for async context
            pass
    
    async def _initialize(self):
        """Initialize Google Sheets connection"""
        try:
            # Get credentials from environment variable
            creds_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS')
            if not creds_json:
                logger.warning("Google Sheets credentials not found in environment")
                return
            
            # Parse credentials
            try:
                creds_dict = json.loads(creds_json)
            except json.JSONDecodeError:
                logger.error("Invalid JSON in GOOGLE_SHEETS_CREDENTIALS")
                return
            
            # Set up credentials
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
            self.gc = gspread.authorize(credentials)
            
            # Get or create spreadsheet
            sheet_name = os.getenv('GOOGLE_SHEET_NAME', 'Worker Registrations')
            try:
                self.sheet = self.gc.open(sheet_name)
            except gspread.SpreadsheetNotFound:
                logger.info(f"Creating new spreadsheet: {sheet_name}")
                self.sheet = self.gc.create(sheet_name)
                # Share with admin email if provided
                admin_email = os.getenv('ADMIN_EMAIL')
                if admin_email:
                    self.sheet.share(admin_email, perm_type='user', role='writer')
            
            # Get or create worksheet
            try:
                self.worksheet = self.sheet.worksheet('Registrations')
            except gspread.WorksheetNotFound:
                logger.info("Creating new worksheet: Registrations")
                self.worksheet = self.sheet.add_worksheet(title='Registrations', rows=1000, cols=10)
                # Add headers
                headers = [
                    'Дата регистрации', 'Имя', 'Возраст', 'Телефон',
                    'Telegram Username', 'Telegram ID', 'Статус', 'Комментарии'
                ]
                self.worksheet.append_row(headers)
            
            self.initialized = True
            logger.info("Google Sheets integration initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets: {e}")
            self.initialized = False
    
    async def add_registration(self, data: Dict) -> bool:
        """Add new registration to the sheet"""
        # Ensure initialization
        if not self.initialized and GSPREAD_AVAILABLE:
            await self._initialize()
            
        if not self.initialized or not self.worksheet:
            logger.warning("Google Sheets not initialized, saving to local file instead")
            return await self._save_to_local_file(data)
        
        try:
            # Prepare row data
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            row = [
                timestamp,
                data['name'],
                data['age'],
                data['phone'],
                data['telegram_username'],
                data['telegram_id'],
                'Новый',  # Status
                ''  # Comments
            ]
            
            # Add to sheet
            self.worksheet.append_row(row)
            logger.info(f"Added registration for {data['name']} to Google Sheets")
            
            # Update data with timestamp for admin notification
            data['registration_date'] = timestamp
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add registration to Google Sheets: {e}")
            # Fallback to local file
            return await self._save_to_local_file(data)
    
    async def _save_to_local_file(self, data: Dict) -> bool:
        """Fallback method to save to local CSV file"""
        try:
            import csv
            from pathlib import Path
            
            file_path = Path('registrations.csv')
            file_exists = file_path.exists()
            
            with open(file_path, 'a', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'registration_date', 'name', 'age', 'phone',
                    'telegram_username', 'telegram_id', 'status', 'comments'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # Write header if file is new
                if not file_exists:
                    writer.writeheader()
                
                # Write data
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                row_data = {
                    'registration_date': timestamp,
                    'name': data['name'],
                    'age': data['age'],
                    'phone': data['phone'],
                    'telegram_username': data['telegram_username'],
                    'telegram_id': data['telegram_id'],
                    'status': 'Новый',
                    'comments': ''
                }
                writer.writerow(row_data)
            
            logger.info(f"Saved registration for {data['name']} to local CSV file")
            data['registration_date'] = timestamp
            return True
            
        except Exception as e:
            logger.error(f"Failed to save to local file: {e}")
            return False
    
    async def get_registration_stats(self) -> Dict:
        """Get registration statistics"""
        # Ensure initialization
        if not self.initialized and GSPREAD_AVAILABLE:
            await self._initialize()
            
        if not self.initialized or not self.worksheet:
            return await self._get_local_stats()
        
        try:
            # Get all records
            records = self.worksheet.get_all_records()
            
            now = datetime.now()
            today = now.date()
            week_start = today - timedelta(days=today.weekday())
            month_start = today.replace(day=1)
            
            stats = {
                'total': len(records),
                'today': 0,
                'this_week': 0,
                'this_month': 0
            }
            
            for record in records:
                try:
                    reg_date = datetime.strptime(record['Дата регистрации'], '%Y-%m-%d %H:%M:%S').date()
                    
                    if reg_date == today:
                        stats['today'] += 1
                    if reg_date >= week_start:
                        stats['this_week'] += 1
                    if reg_date >= month_start:
                        stats['this_month'] += 1
                        
                except (ValueError, KeyError):
                    continue
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get stats from Google Sheets: {e}")
            return await self._get_local_stats()
    
    async def _get_local_stats(self) -> Dict:
        """Get statistics from local CSV file"""
        try:
            import csv
            from pathlib import Path
            
            file_path = Path('registrations.csv')
            if not file_path.exists():
                return {'total': 0, 'today': 0, 'this_week': 0, 'this_month': 0}
            
            now = datetime.now()
            today = now.date()
            week_start = today - timedelta(days=today.weekday())
            month_start = today.replace(day=1)
            
            stats = {
                'total': 0,
                'today': 0,
                'this_week': 0,
                'this_month': 0
            }
            
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    stats['total'] += 1
                    
                    try:
                        reg_date = datetime.strptime(row['registration_date'], '%Y-%m-%d %H:%M:%S').date()
                        
                        if reg_date == today:
                            stats['today'] += 1
                        if reg_date >= week_start:
                            stats['this_week'] += 1
                        if reg_date >= month_start:
                            stats['this_month'] += 1
                            
                    except (ValueError, KeyError):
                        continue
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get local stats: {e}")
            return {'total': 0, 'today': 0, 'this_week': 0, 'this_month': 0}
