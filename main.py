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
def download_to_ram(url: str) -> tuple:
    """
    Downloads a file from a given URL directly into RAM using BytesIO.

    Args:
        url (str): The URL of the file to download.

    Returns:
        tuple: (default_file_name, file_in_ram)
    """
    logger.info('Starting file download to RAM.')
    
    # Initial HEAD request to get file metadata
    response = requests.head(url)
    logger.debug(f'Response headers: {response.headers}')

    total_size = int(response.headers.get('content-length', 0))
    content_disposition = response.headers.get('Content-Disposition', None)
    
    # Determine filename from Content-Disposition header or default to 'Unnamed'
    if content_disposition:
        default_file_name = content_disposition.split('filename=')[1].strip('"')
    else:
        default_file_name = 'Unnamed'

    file_in_ram = BytesIO()
    downloaded_size = 0

    # Download the file in chunks with a progress bar
    while downloaded_size < total_size:
        try:
            headers = {'Range': f'bytes={downloaded_size}-{total_size}'}
            response = requests.get(url, headers=headers, stream=True, timeout=60)
            response.raise_for_status()  # Raise an exception for HTTP errors

            if response.status_code == 206:  # Partial Content
                with tqdm(total=total_size, initial=downloaded_size, unit='iB', unit_scale=True, unit_divisor=1024, desc=f"Downloading {default_file_name}") as bar:
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
                with tqdm(total=total_size, unit='iB', unit_scale=True, unit_divisor=1024, desc=f"Downloading {default_file_name}") as bar:
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
    return default_file_name, file_in_ram


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


def upload_local_file(file_path: str, file_name: str, username: str, apikey: str) -> dict:
    """
    Uploads a local file to Pixeldrain.

    Args:
        file_path (str): The file path to the file to upload. 
        file_name (str): The name of the file to upload.
        username (str): Pixeldrain username.
        apikey (str): Pixeldrain API key.

    Returns:
        dict: The JSON response from the Pixeldrain API.
    """
    logger.info(f'Starting upload of local file: {file_path}')

    try:
        with open(file_path, 'rb') as local_file_obj:
            
            response = requests.post(
                'https://pixeldrain.com/api/file',
                auth=HTTPBasicAuth(username, apikey),
                headers={'name': file_name},
                files={'file': (file_name, local_file_obj)},
            )
            response.raise_for_status()  # Raise an exception for HTTP errors
            logger.debug(response.text)

    except FileNotFoundError:
        logger.error(f"Error: Local file not found at '{file_path}'")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error processing local file '{file_path}': {e}")
        sys.exit(1)

    logger.info('Local file upload complete.')
    return response.json()


# --- Credential Management ---
def get_upload_properties(args: argparse.Namespace, default_file_name: str) -> tuple:
    """
    Retrieves username, API key, and filename for upload.
    Prioritizes command-line arguments, then environment variables.

    Args:
        args (argparse.Namespace): Command-line arguments.
        default_file_name (str): The default file name of the file (Name the URL or name of the local file in disk). 

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
    filename = args.name if args.name else default_file_name 
    
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
        logger.info(
f"""
+ ---------------------- Upload Successful --------------------- +
| Share and preview:                                             |
|    https://pixeldrain.com/u/{file_id}                           |
| Direct download:                                               |
|    https://pixeldrain.com/api/file/{file_id}?download           |
| Unlimited download:                                            |
|    https://pd.cybar.xyz/{file_id}                               |
+ -------------------------------------------------------------- +
""")

    else:
        logger.error(f"Upload failed: {result.get('message', 'Unknown error')}")
        sys.exit(1)


def main():
    """
    Main function to parse arguments, download, upload, and handle credentials.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='A tool to upload files to Pixeldrain from a URL or local disk.'
    )
    parser.add_argument('source', type=str,
                        help='The URL of the file to download from, or the path to a local file to upload.')
    parser.add_argument('-n', '--name', type=str, help='The name for the file you want to store on Pixeldrain.')
    parser.add_argument('-u', '--username', type=str, help='The username of the Pixeldrain account.')
    parser.add_argument('-k', '--apikey', type=str, help='The API key of the Pixeldrain account.')
    parser.add_argument('-s', '--store-credential', action='store_true',
                        help='Store the username and API key in a .env file for future use. '
                             'Previous stored keys will be overwritten.')
    args = parser.parse_args()

    upload_result = None
    filename = None
    
    # Check if the source is a URL
    # Todo: Check whether a account is valid before upload 
    # Todo: Check whether there is enough RAM before downloading
    if args.source.startswith(('http://', 'https://')):
        # Download file to RAM
        default_file_name, file_in_ram = download_to_ram(args.source)

        # Get upload properties (filename, username, apikey)
        filename, username, apikey = get_upload_properties(args, default_file_name)

        # Upload file from RAM
        upload_result = upload_from_ram(file_in_ram, filename, username, apikey)
    else:
        # Assume it's a local file path
 
        # Get upload properties (filename, username, apikey)
        filename, username, apikey = get_upload_properties(args, os.path.basename(args.source)) 

        # Upload local file
        upload_result = upload_local_file(args.source, filename, username, apikey)

    if upload_result:
        # Display upload result
        display_upload_result(upload_result)
 
        # Store credentials if requested and upload was successful
        if args.store_credential and upload_result.get('success'):
            store_credentials(username, apikey)


if __name__ == "__main__":
    main()
