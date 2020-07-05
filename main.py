from ComdirectConnection import Connection
from settings import Settings
from pathvalidate import sanitize_filename
import os
import time
import datetime

class Main:

    def __init__(self, dirname):
        self.dirname = dirname
        self.settings = Settings(dirname)
        self.conn = False
        self.showMenu()


    def showMenu(self):

        menuWidth = 74
        
        def __print_menu():
            __printFullWidth("--")
            __printFullWidth(" Comdirect Documents Downloader ")
            __printFullWidth(" by WGPSenshi & retiredHero ")
            __printFullWidth("--")
            onlineStatus = " online "
            if not self.conn:
                onlineStatus = " not online "
            __printFullWidth("Current Status: " + onlineStatus, "left")    
            __printFullWidth("--")
            print("1. Show Current Settings ")
            print("2. Reload Settings From File settings.ini ")
            print("3. Show Status Local Files (WIP) ")
            print("4. Show Status Online Files (WIP) ")        
            print("5. Show Status Local Files vs Online Files (WIP) ")
            print("6. Start Download / Update Local Files ")
            print("0. Exit ")
            __printFullWidth("--")

        def __printFullWidth(printString, align="center"):
            spaces = menuWidth - len(printString)
            if spaces % 2 == 1:
                printString+= " "
                spaces = menuWidth - len(printString)

            if align == "center":
                filler = int(spaces / 2)
                print( filler * "-" + printString + filler * "-")
            elif align == "left":
                filler = int(spaces)
                print( printString + filler * "-")
            elif align == "right":
                filler = int(spaces)
                print( filler * "-" + printString)

        loop = True

        while loop:
            __print_menu()
            user_input = input("Choose an option [1-6] / [0]: ")
            val = 0

            try:
                val = int(user_input)
            except ValueError:
                print("No.. input is not a valid integer number! Press Enter to continue!")
                continue
        
            if val == 1:
                # Show Current Settings
                __printFullWidth("--")
                __printFullWidth(" Current Settings ")
                self.settings.showSettings()
                __printFullWidth("--")
            elif val == 2:
                # Reload Settings from file
                __printFullWidth("--")
                __printFullWidth(" Reload Settings From File settings.ini ")
                self.settings.readSettings()
                __printFullWidth("--")
            elif val == 3:
                # show status local files
                print("-3-")
            elif val == 4:
                # show status online files
                print("-4-")
                self.__startConnection()
            elif val == 5:
                # show status local vs online files
                print("-5-")
            elif val == 6:
                # start download of files
                print("-6-")
                self.__startConnection()
                self.__loadDocuments()
            elif val == 0:
                loop = False
            else:
                print("not a valid input")

            if not val == 0:
                input("Press Enter to Return to Menu!")

        return val

    def __startConnection(self):
        """
            ToDo: Check if all settings are set for connection!
        """
        if self.settings and not self.conn:
            try:
                self.conn = Connection(
                    username = self.settings.getValueForKey("user"),
                    password = self.settings.getValueForKey("pwd"),
                    client_id = self.settings.getValueForKey("clientId"),
                    client_secret = self.settings.getValueForKey("clientSecret")
                )
                self.conn.login()
            except Exception as err:
                print(err)
        else:
            print("You are already online!")

    def __loadDocuments(self):
        if not self.conn:
            raise NameError("conn not set!")
            return

        messagesMeta = self.conn.getMessagesList(0,1)
        x = 0
        overwrite = False # Only download new files
        while x < messagesMeta["paging"]["matches"]:
            # Process batches of 100. Max batchsize is 1000 (API restriction)
            messagesMeta = self.conn.getMessagesList(x,1000)
            x += 1000
            for idx, messageMeta in enumerate(messagesMeta["values"]):
                filename = messageMeta["name"]
                if messageMeta["mimeType"] == "application/pdf":
                    filename += ".pdf"
                elif messageMeta["mimeType"] == "text/html":
                    filename += ".html"
                filepath = os.path.join(self.settings.getValueForKey("outputDir"), sanitize_filename(filename))
                
                print(idx, messageMeta["dateCreation"], messageMeta["name"], messageMeta["mimeType"])

                if not overwrite:
                    if os.path.exists(filepath):
                        continue
                
                if not bool(self.settings.getBoolValueForKey('dryRun')):
                    docContent = self.conn.downloadMessage(messageMeta)
                    moddate = time.mktime(datetime.datetime.strptime(messageMeta["dateCreation"],"%Y-%m-%d").timetuple())
                    with open(filepath, "wb") as f:
                        f.write(docContent)
                        #shutil.copyfileobj(docContent, f)
                    os.utime(filepath, (moddate,moddate))


dirname = os.path.dirname(__file__)
main = Main(dirname)
