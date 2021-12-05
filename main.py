import configparser
import csv
import logging
import os.path
from datetime import datetime

import mysql.connector
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from mysql.connector import Error

config = configparser.RawConfigParser()
config.read('database.properties')

# Mute (unwanted) Google API logs
logging.getLogger("googleapiclient.discovery").setLevel(logging.ERROR)

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive']

BACKUP_FOLDER_PATH = 'backups/'

LOGS_FOLDER_PATH = 'logs/'

CONFIG = {
    'database': config.get('Database', 'database.dbname'),
    'host': config.get('Database', 'database.host'),
    'user': config.get('Database', 'database.user'),
    'password': config.get('Database', 'database.password'),
    'raise_on_warnings': True
}


if not os.path.exists(BACKUP_FOLDER_PATH):
    os.makedirs(BACKUP_FOLDER_PATH)

if not os.path.exists(LOGS_FOLDER_PATH):
    os.makedirs(LOGS_FOLDER_PATH)


logging.basicConfig(
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler("logs/script.log"),
        logging.StreamHandler()
    ],
    level=logging.DEBUG
)


def backup_database():
    try:
        connection = mysql.connector.connect(**CONFIG)
        recently_backed_files = []

        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute('SHOW TABLES')

            tables = cursor.fetchall()

            # Table names
            tables = list(map(lambda entry: entry[0], tables))

            for table_name in tables:
                cursor.execute('SELECT * FROM ' + table_name)
                rows = cursor.fetchall()

                headers = list(map(lambda entry: entry[0], cursor.description))
                file = dump_to_csv(table_name, headers, rows)
                recently_backed_files.append(file)

            logging.info('All tables backed up successfully!')

            cursor.close()

        connection.close()

        return recently_backed_files

    except Error as e:
        logging.error('Error while trying to retrieve data from db')
        print(e)


def dump_to_csv(table_name, headers, rows):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_name = f'{table_name}-{timestamp}.csv'

    with open(f'{BACKUP_FOLDER_PATH}{file_name}', 'w', encoding='utf-8') as csv_file:
        output = csv.writer(csv_file)
        output.writerow(headers)
        output.writerows(rows)

        logging.debug(f'Table: {file_name} backed up successfully')

        return file_name


def upload_to_drive(recently_backed_files):
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    for file_name in recently_backed_files:
        file_path = f'{BACKUP_FOLDER_PATH}{file_name}'

        file_metadata = {'name': file_name,
                         'parents': ['1op1jEXiXWExXQFiquOZxIZLPW0tjBKr8']
                         }

        service = build(
            'drive',
            'v3',
            credentials=creds,
            cache_discovery=False
        )

        # Call the Drive v3 API
        media = MediaFileUpload(
            file_path,
            mimetype='text/csv'
        )

        file_id = service.files().create(body=file_metadata,
                                         media_body=media,
                                         fields='id'
                                         ).execute()

        file_id = file_id.get('id')

        logging.debug(
            f'File: {file_name} ({file_id}) uploaded to Google drive'
        )

    logging.info('All data successfully uploaded to Google drive!')


if __name__ == '__main__':
    recently_backed_files = backup_database()

    upload_to_drive(recently_backed_files)

    logging.info('Script finished successfully')

    input("Press enter to exit ;)")
