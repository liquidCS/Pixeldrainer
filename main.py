import os
import sys
import json
import argparse
import logging
from io import BytesIO

import requests
from dotenv import load_dotenv
from tqdm import tqdm
from requests.auth import HTTPBasicAuth


# --- Constants ---
BLOCK_SIZE = 4096  # Chunk size for downloading files

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# --- File Operations ---
def download_to_ram(url: str) -> list:
    """
    Downloads a file from a given URL directly into RAM using BytesIO.

    Args:
        url (str): The URL of the file to download.

    Returns:
        list: A list containing the filename and the BytesIO object with the file content.
    """
    logger.info('Starting file download to RAM.')
    
    # Initial HEAD request to get file metadata
    response = requests.head(url)
    logger.debug(f'Response headers: {response.headers}')

    total_size = int(response.headers.get('content-length', 0))
    content_disposition = response.headers.get('Content-Disposition', None)
    
    # Determine filename from Content-Disposition header or default to 'Unnamed'
    if content_disposition:
        filename = content_disposition.split('filename=')[1].strip('"')
    else:
        filename = 'Unnamed'

    file_in_ram = BytesIO()
    downloaded_size = 0

    # Download the file in chunks with a progress bar
    while downloaded_size < total_size:
        try:
            headers = {'Range': f'bytes={downloaded_size}-{total_size}'}
            response = requests.get(url, headers=headers, stream=True, timeout=60)
            response.raise_for_status()  # Raise an exception for HTTP errors

            if response.status_code == 206:  # Partial Content
                with tqdm(total=total_size, initial=downloaded_size, unit='iB', unit_scale=True, unit_divisor=1024, desc=f"Downloading {filename}") as bar:
                    for data in response.iter_content(BLOCK_SIZE):
                        file_in_ram.write(data)
                        downloaded_size += len(data)
                        bar.update(len(data))
            else:
                logger.error(f'Server did not support range requests. Status code: {response.status_code}')
                # Fallback for servers not supporting range requests: download entire file
                file_in_ram.seek(0) # Reset BytesIO if partial download occurred
                file_in_ram.truncate(0)
                response = requests.get(url, stream=True, timeout=60)
                response.raise_for_status()
                with tqdm(total=total_size, unit='iB', unit_scale=True, unit_divisor=1024, desc=f"Downloading {filename}") as bar:
                    for data in response.iter_content(BLOCK_SIZE):
                        file_in_ram.write(data)
                        downloaded_size += len(data)
                        bar.update(len(data))
                break # Exit loop after full download

        except requests.exceptions.RequestException as e:
            logger.error(f'Error occurred during download: {e}. Retrying...')
            continue
        except Exception as e:
            logger.error(f'An unexpected error occurred: {e}')
            sys.exit(1)

    file_in_ram.seek(0)  # Move cursor to the beginning for subsequent reads
    logger.info("File download complete.")
    return [filename, file_in_ram]


def upload_from_ram(file_in_ram: BytesIO, file_name: str, username: str, apikey: str) -> dict:
    """
    Uploads a file from RAM to Pixeldrain.

    Args:
        file_in_ram (BytesIO): The BytesIO object containing the file content.
        file_name (str): The name of the file to upload.
        username (str): Pixeldrain username.
        apikey (str): Pixeldrain API key.

    Returns:
        dict: The JSON response from the Pixeldrain API.
    """
    logger.info(f'Starting upload of file: {file_name}')
    
    response = requests.post(
        'https://pixeldrain.com/api/file',
        auth=HTTPBasicAuth(username, apikey),
        headers={'name': file_name},
        files={'file': (file_name, file_in_ram)},
    )
    response.raise_for_status()  # Raise an exception for HTTP errors
    logger.debug(response.text)
    logger.info('File upload complete.')
    return response.json()


# --- Credential Management ---
def get_upload_properties(args: argparse.Namespace, file_data: list) -> tuple:
    """
    Retrieves username, API key, and filename for upload.
    Prioritizes command-line arguments, then environment variables.

    Args:
        args (argparse.Namespace): Command-line arguments.
        file_data (list): List containing original filename and BytesIO object.

    Returns:
        tuple: (filename, username, apikey)
    """
    load_dotenv()  # Load environment variables from .env file

    username = args.username
    apikey = args.apikey

    # Check for credentials from .env if not provided via command line
    if not username and not apikey:
        username = os.getenv('username')
        apikey = os.getenv('apikey')
        if not username or not apikey:
            logger.error("Error: Pixeldrain username and API key not found. Please provide them via command-line arguments or in a .env file.")
            sys.exit(1)
    elif not username or not apikey:
        logger.error('Error: Both username and apikey must be provided if using command-line arguments.')
        sys.exit(1)
    
    # Determine the filename for upload
    filename = args.name if args.name else file_data[0]
    
    return filename, username, apikey


def store_credentials(username: str, apikey: str):
    """
    Stores username and API key in a .env file.

    Args:
        username (str): Pixeldrain username.
        apikey (str): Pixeldrain API key.
    """
    try:
        with open('.env', 'w') as file:
            file.write(f'username={username}\n')
            file.write(f'apikey={apikey}\n')
        logger.info('Credentials successfully stored in .env file.')
    except IOError as e:
        logger.error(f'Error storing credentials to .env file: {e}')


# --- Output and Main Execution ---
def display_upload_result(result: dict):
    """
    Displays the upload result links or an error message.

    Args:
        result (dict): The JSON response from the Pixeldrain API.
    """
    if result.get('success'):
        file_id = result['id']
        logger.info(f"\n--- Upload Successful ---"
                    f"\nDirect download link:\n\thttps://pixeldrain.com/api/file/{file_id}?download"
                    f"\nUnlimited download using:\n\thttps://pd.cybar.xyz/{file_id}"
                    f"\nShare or preview using:\n\thttps://pixeldrain.com/u/{file_id}\n")
    else:
        logger.error(f"Upload failed: {result.get('message', 'Unknown error')}")
        sys.exit(1)


def main():
    """
    Main function to parse arguments, download, upload, and handle credentials.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='A tool to download files and directly upload them to Pixeldrain without writing to disk.'
    )
    parser.add_argument('urls', type=str, help='The URL of the file to download from.')
    parser.add_argument('-n', '--name', type=str, help='The name for the file you want to store on Pixeldrain.')
    parser.add_argument('-u', '--username', type=str, help='The username of the Pixeldrain account.')
    parser.add_argument('-k', '--apikey', type=str, help='The API key of the Pixeldrain account.')
    parser.add_argument('--store-credential', action='store_true',
                        help='Store the username and API key in a .env file for future use. '
                             'Previous stored keys will be overwritten.')
    args = parser.parse_args()

    # Download file to RAM
    file_data = download_to_ram(args.urls)
    file_in_ram = file_data[1]

    # Get upload properties (filename, username, apikey)
    filename, username, apikey = get_upload_properties(args, file_data)

    # Upload file from RAM
    upload_result = upload_from_ram(file_in_ram, filename, username, apikey)

    # Display upload result
    display_upload_result(upload_result)
    
    # Store credentials if requested and upload was successful
    if args.store_credential and upload_result.get('success'):
        store_credentials(username, apikey)


if __name__ == "__main__":
    main()
