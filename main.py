import os
from dotenv import load_dotenv
import requests
import argparse
from io import BytesIO
from tqdm import tqdm
from requests.auth import HTTPBasicAuth
import logging 


BLOCK_SIZE = 1024

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def download_to_ram(url):
    logger.info('Start Downloading File')
    response = requests.head(url)
    logger.debug(f'Response headers: {response.headers}')

    total_size = int(response.headers.get('content-length', 0)) # Get size of the file
    content_disposition = response.headers.get('Content-Disposition', None) # Get filename from server 
    if content_disposition != None: 
        filename = content_disposition.split('filename=')[1].strip('"')
    else:
        filename = 'Unnamed'

    file_in_ram = BytesIO() # Create a BytesIO object to hold the file in memory
    downloaded_size = 0

    # Download
    while downloaded_size < total_size:
        try: 
            headers = {'Range': f'bytes={downloaded_size}-{total_size}'} # Range to downlaod
            response = requests.get(url, headers=headers, stream=True, timeout=60)
            
            if response.status_code == 206:
                with tqdm(total=total_size, initial=downloaded_size, unit='iB', unit_scale=True, unit_divisor=1024) as bar:
                    for data in response.iter_content(BLOCK_SIZE):
                        file_in_ram.write(data)
                        downloaded_size += len(data)
                        bar.update(len(data))
            else:
                logger.error('Server did not support range requests.')

        except requests.exceptions.RequestException as e:
            logger.error(f'Error occurred: {e}. Retrying...')
            continue

    # Move the cursor to the beginning of the BytesIO object
    file_in_ram.seek(0)
    logger.info("Done Downloading File")
    return [filename, file_in_ram]


def upload_from_ram(file_in_ram, file_name, username, apikey):
    logger.info('Start uploading file')
    # Get the total size of the data
    total_size = file_in_ram.getbuffer().nbytes

    # Upload the file in chunks
    response = requests.post(
        'https://pixeldrain.com/api/file',
        auth=HTTPBasicAuth(username, apikey),
        headers={'name': file_name},
        files={'file': (file_name, file_in_ram)},
    )
    return response




if __name__ == "__main__":

    # Read arguments form command line
    parser = argparse.ArgumentParser(description='A tool to let you download and directively upload to pixeldrain without writing to disk.')
    parser.add_argument('urls', type=str, help='The url of the file to download from.')
    parser.add_argument('-n', '--name', type=str, help='The name for the file you want to store.')
    parser.add_argument('-u', '--username', type=str, help='The username of the pixeldrain account you want to upload to.')
    parser.add_argument('-k', '--apikey', type=str, help='The apikey of the pixeldrain account you want to upload to.')
    parser.add_argument('--store_credential', action='store_true', help='Store the username and apikey for future use.\nPrevious stored key will be rewrite')
    args = parser.parse_args()
    
    # Load .env files
    load_dotenv()

    # Downlaoding files
    file_data = download_to_ram(args.urls)

    # Uploading files
    if(args.username == None and args.apikey == None):
        if os.getenv('username') != None and os.getenv('apikey') != None:
            if args.name != None:
                response = upload_from_ram(file_data[1], args.name, os.getenv('username'), os.getenv('apikey')) 
            else:
                response = upload_from_ram(file_data[1], file_data[0], os.getenv('username'), os.getenv('apikey'))
            logger.debug(response.text)
        else:
            logger.error("Can't get username or apikey from previous credential.")
            exit()

    elif(args.username == None or args.apikey == None):
        logger.error('You need to provide both username and apikey')
        exit()

    
    if args.store_credential:
        with open('.env', 'w') as file:
            file.write(f'username={args.username}\n')
            file.write(f'apikey={args.apikey}\n')






    

