from ComdirectConnection import Connection
import os
import configparser
from pathvalidate import sanitize_filename
import time
import datetime


dirname = os.path.dirname(__file__)

# If you want comfort, put your data into the settings.ini
# If you understandably don't want to leave all credentials in a clear textfile,
# just leave them out and you will be prompted for them.
if os.path.isfile(os.path.join(dirname, "settings.ini")):
    config = configparser.ConfigParser()
    config.read(os.path.join(dirname, "settings.ini"))
    if not config.has_option(None, "user"):
        user = input("Please enter your user number / Kundennummer")
    else:
        user = config['DEFAULT']['user']
    if not config.has_option(None, "pass"):
        pwd =input("Please enter your password")
    else:
        pwd = config['DEFAULT']['pass']
    if not config.has_option(None, "clientId"):
        clientId = input("Please enter your clientId for API access")
    else:
        clientId = config['DEFAULT']['clientId']
    if not config.has_option(None, "clientSecret"):
        clientSecret = input("Please enter your clientSecret for API access")
    else:
        clientSecret = config['DEFAULT']['clientSecret']
    if not config.has_option(None, "outputdir"):
        outputdir = input("Please enter the path to the folder you want reports to be downloaded to")
    else:
        outputdir = config['DEFAULT']['outputdir']

if os.path.isabs(outputdir):
    if not os.path.exists(outputdir):
        os.makedirs(outputdir)
else:
    if not os.path.exists(os.path.join(dirname, outputdir)):
        os.makedirs(os.path.join(dirname, outputdir))

conn = Connection(
    username = user,
    password = pwd,
    client_id = clientId,
    client_secret = clientSecret,
)
conn.login()



messagesMeta = conn.getMessagesList(0,1)
x = 0
overwrite = False # Only download new files
while x < messagesMeta["paging"]["matches"]:
    # Process batches of 100. Max batchsize is 1000 (API restriction)
    messagesMeta = conn.getMessagesList(x,100)
    x += 100
    for idx, messageMeta in enumerate(messagesMeta["values"]):
        filename = messageMeta["name"]
        if messageMeta["mimeType"] == "application/pdf":
            filename += ".pdf"
        elif messageMeta["mimeType"] == "text/html":
            filename += ".html"
        filepath = os.path.join(outputdir, sanitize_filename(filename))

        if not overwrite:
            if os.path.exists(filepath):
                continue
            
        print(idx, messageMeta["dateCreation"], messageMeta["name"], messageMeta["mimeType"])
        docContent = conn.downloadMessage(messageMeta)
        moddate = time.mktime(datetime.datetime.strptime(messageMeta["dateCreation"],"%Y-%m-%d").timetuple())
        with open(filepath, "wb") as f:
            f.write(docContent)
            os.utime(filepath, (moddate,moddate))
            #shutil.copyfileobj(docContent, f)