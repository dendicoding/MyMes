import os

# SQL Server connection settings
SQL_SERVER_HOST = 'DESKTOP-FVGN4I5'
SQL_SERVER_PORT = 1433
SQL_SERVER_DATABASE = 'MYMES'
SQL_SERVER_USERNAME = 'mymes'
SQL_SERVER_PASSWORD = 'mymes'

# Create a connection string
CONNECTION_STRING = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SQL_SERVER_HOST},{SQL_SERVER_PORT};DATABASE={SQL_SERVER_DATABASE};UID={SQL_SERVER_USERNAME};PWD={SQL_SERVER_PASSWORD}'

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or 'your_default_secret_key'

