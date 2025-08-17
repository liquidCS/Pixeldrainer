import os
from dotenv import load_dotenv
import requests
import argparse
from io import BytesIO
from tqdm import tqdm
from requests.auth import HTTPBasicAuth
import logging 
import json


BLOCK_SIZE = 4096 

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
    logger.debug(response.text)

    return response.json()

def get_upload_properties(args):

    load_dotenv() # Read .env file

    if(args.username == None and args.apikey == None):
        if os.getenv('username') != None and os.getenv('apikey') != None:
            username = os.getenv('username')
            apikey = os.getenv('apikey')
        else:
            logger.error("Can't get username or apikey from previous credential.")
            exit()
    
    elif(args.username != None and args.apikey != None):
        username = args.username
        apikey = args.apikey

    elif(args.username == None or args.apikey == None):
        logger.error('You need to provide both username and apikey')
        exit()

    else:
        logger.error('Credential Error.')
        exit()
    
    filename = args.name if args.name else file_data[0]
    
    return filename, username, apikey 


def end_message(result):
    if result['success']:
        id = result['id']
        logger.info(f"\n\nDirect download link:\n\thttps://pixeldrain.com/api/file/{id}?download\nUnlimited download using:\n\thttps://pd.cybar.xyz/{id}\nShare or preview using:\n\thttps://pixeldrain.com/u/{id}\n")
    else:
        logger.error('Upload error')
        exit()




if __name__ == "__main__":

    # Read arguments form command line
    parser = argparse.ArgumentParser(description='A tool to let you download and directively upload to pixeldrain without writing to disk.')
    parser.add_argument('urls', type=str, help='The url of the file to download from.')
    parser.add_argument('-n', '--name', type=str, help='The name for the file you want to store.')
    parser.add_argument('-u', '--username', type=str, help='The username of the pixeldrain account you want to upload to.')
    parser.add_argument('-k', '--apikey', type=str, help='The apikey of the pixeldrain account you want to upload to.')
    parser.add_argument('--store_credential', action='store_true', help='Store the username and apikey for future use.\nPrevious stored key will be rewrite')
    args = parser.parse_args()
    
    # Downlaoding files
    file_data = download_to_ram(args.urls)
    file = file_data[1]

    # Prepare upload properties 
    filename, username, apikey = get_upload_properties(args)

    # Start uploading
    result = upload_from_ram(file, filename, username, apikey)

    end_message(result)
    
    # Store credential if success
    if args.store_credential:
        with open('.env', 'w') as file:
            file.write(f'username={args.username}\n')
            file.write(f'apikey={args.apikey}\n')






    

