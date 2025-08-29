
# Pixeldrainer

A tool that let you download and directively upload to pixeldrain without writing to disk.

## USAGE AND OPTIONS

### Execute from Source
To run Pixeldrainer directly from the source code, you need to have Python 3 and the required packages installed.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/liquidCS/Pixeldrainer.git
    cd Pixeldrainer
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements-runtime.txt
    ```

3.  **Run the script:**
    ```bash
    python main.py <source> [-n NAME] [-u USERNAME] [-k APIKEY] [--store-credential]
    ```
    -   `<source>` can be a URL (e.g., `http://example.com/file.zip`) or a local file path (e.g., `~/Downloads/my_local_file.txt`).

    **Example:**
    ```bash
    python main.py http://example.com/bigfile.iso -u your_username -k your_api_key --store-credential
    python main.py ~/Documents/report.pdf -n "Monthly Report" -u your_username -k your_api_key
    ```

### PyInstaller (Standalone Executable)
You can create a standalone executable using PyInstaller. This allows you to run Pixeldrainer without installing Python or its dependencies on the target machine.

1.  **Install build dependencies:**
    ```bash
    pip install -r requirements-build.txt
    ```

2.  **Build the executable:**
    ```bash
    pyinstaller --onefile main.py
    ```
    The executable will be found in the `dist/` directory.

3.  **Run the executable:**
    ```bash
    ./dist/main <source> [-n NAME] [-u USERNAME] [-k APIKEY] [--store-credential]
    ```
    (On Windows, it would be `dist\main.exe`)

### Arguments
```
usage: pixeldrainer [-h] [-n NAME] [-u USERNAME] [-k APIKEY] [--store-credential] source
```
```
positional arguments:
  source                The URL of the file to download from, or the path to a local file to upload.

options:
  -h, --help            show this help message and exit
  -n, --name NAME       The name for the file you want to store on Pixeldrain.
  -u, --username USERNAME
                        The username of the Pixeldrain account you want to upload to.
  -k, --apikey APIKEY   The API key of the Pixeldrain account you want to upload to.
  --store-credential    Store the username and API key in a .env file for future use. Previous stored keys will be overwritten.
```
