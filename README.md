
# Pixeldrainer

A tool that let you download and directively upload to pixeldrain without writing to disk.

## USAGE AND OPTIONS
```
usage: pixeldrainer [-h] [-n NAME] [-u USERNAME] [-k APIKEY] [--store_credential] urls
```
```
positional arguments:
  urls                  The url of the file to download from.

options:
  -h, --help            show this help message and exit
  -n, --name NAME       The name for the file you want to store.
  -u, --username USERNAME
                        The username of the pixeldrain account you want to upload to.
  -k, --apikey APIKEY   The apikey of the pixeldrain account you want to upload to.
  --store_credential    Store the username and apikey for future use. Previous stored key will be rewrite
```
