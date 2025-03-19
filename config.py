import os
from dotenv import load_dotenv

load_dotenv()

ACCOUNT_SID = os.getenv('ACCOUNT_SID')
AUTH_TOKEN = os.getenv('AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

MSSQL_DRIVER = os.getenv('MSSQL_DRIVER')
MSSQL_SERVER = os.getenv('MSSQL_SERVER')
MSSQL_DATABASE = os.getenv('MSSQL_DATABASE')
MSSQL_USER = os.getenv('MSSQL_USER')
MSSQL_PASSWORD = os.getenv('MSSQL_PASSWORD')

WHATSAPP_TOKEN = os.getenv('WSP_TOKEN')
WHATSAPP_PHONE_SID = os.getenv('WSP_PHONE_SID')
