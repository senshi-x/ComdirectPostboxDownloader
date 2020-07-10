from ComdirectConnection import Connection
from settings import Settings
from pathvalidate import sanitize_filename
import os
import time
import datetime


class Main:
    def __init__(self, dirname):
        self.dirname = dirname
        try:
            self.settings = Settings(dirname)
        except Exception as error:
            print(error)
            exit(0)

        self.conn = False

        self.onlineDocumentsDict = {}
        self.onlineAdvertismentIndicesList = []
        self.onlineArchivedIndicesList = []
        self.onlineUnreadIndicesList = []
        self.onlineFileNameMatchingIndicesList = []
        self.onlineNotYetDownloadedIndicesList = []
        self.onlineAlreadyDownloadedIndicesList = []

        self.showMenu()

    def __printFullWidth(self, printString, align="center", filler="-", width=74):
        printString = str(printString)
        spaces = width - len(printString)
        if spaces % 2 == 1:
            printString += " "
            spaces = width - len(printString)

        if align == "center":
            filler = int(spaces / 2)
            print(filler * "-" + printString + filler * "-")
        elif align == "left":
            filler = int(spaces)
            print(printString + filler * "-")
        elif align == "right":
            filler = int(spaces)
            print(filler * "-" + printString)

    def __printLeftRight(self, printLeftString, printRightString, filler=".", width=74):
        printLeftString = str(printLeftString)
        printRightString = str(printRightString)
        spaces = width - len(printLeftString) - len(printRightString)
        print(printLeftString + (spaces * filler) + printRightString)

    def showMenu(self):
        def __print_menu():
            self.__printFullWidth("--")
            self.__printFullWidth(" Comdirect Documents Downloader ")
            self.__printFullWidth(" by WGPSenshi & retiredHero ")
            self.__printFullWidth("--")
            onlineStatus = " online "
            if not self.conn:
                onlineStatus = " not online "
            self.__printFullWidth("Current Status: " + onlineStatus, "left")
            self.__printFullWidth("--")
            print("1. Show Current Settings ")
            print("2. Reload Settings From File settings.ini ")
            print("3. Show Status Local Files (WIP) ")
            print("4. Show Status Online Files ")
            #            print("5. (WIP) ")
            print("6. Start Download / Update Local Files ")
            print("0. Exit ")
            self.__printFullWidth("--")

        loop = True

        while loop:
            __print_menu()
            user_input = input("Choose an option [1-6] / [0]: ")
            val = 0

            try:
                val = int(user_input)
            except ValueError:
                print(
                    "No.. input is not a valid integer number! Press Enter to continue!"
                )
                continue

            if val == 1:
                # Show Current Settings
                self.__printFullWidth("--")
                self.__printFullWidth(" Current Settings ")
                self.settings.showSettings()
                self.__printFullWidth("--")
            elif val == 2:
                # Reload Settings from file
                self.__printFullWidth("--")
                self.__printFullWidth(" Reload Settings From File settings.ini ")
                self.settings.readSettings()
                self.__printFullWidth("--")
            elif val == 3:
                # show status local files
                print("-3-")
            elif val == 4:
                # show status online files
                print("-4-")
                self.__startConnection()
                self.__loadDocuments()
                self.__showStatusOnlineDocuments()
            elif val == 5:
                # -
                print("-5-")
            elif val == 6:
                # start download of files
                print("-6-")
                self.__startConnection()
                self.__loadDocuments()
                self.__processOnlineDocuments()
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
                    username=self.settings.getValueForKey("user"),
                    password=self.settings.getValueForKey("pwd"),
                    client_id=self.settings.getValueForKey("clientId"),
                    client_secret=self.settings.getValueForKey("clientSecret"),
                )
                self.conn.login()
            except Exception as err:
                print(err)
        else:
            print("You are already online!")

    def __loadDocuments(self):
        if not self.conn:
            raise NameError("conn not set!")

        if self.onlineDocumentsDict:
            return

        messagesMeta = self.conn.getMessagesList(0, 1)
        x = 0
        # Process batches of 1000. Max batchsize is 1000 (API restriction)
        batchSize = 1000
        self.onlineDocumentsDict = {}

        while x < messagesMeta["paging"]["matches"]:
            messagesMeta = self.conn.getMessagesList(x, batchSize)

            for idx, documentMeta in enumerate(messagesMeta["values"]):
                self.onlineDocumentsDict[x + idx] = messagesMeta["values"][idx]

            x += batchSize

    def __showStatusOnlineDocuments(self):

        self.onlineAdvertismentIndicesList = []
        self.onlineArchivedIndicesList = []
        self.onlineFileNameMatchingIndicesList = []
        self.onlineNotYetDownloadedIndicesList = []
        self.onlineAlreadyDownloadedIndicesList = []
        self.onlineUnreadIndicesList = []

        if not self.onlineDocumentsDict:
            return

        self.countOnlineAll = len(self.onlineDocumentsDict)

        # do the count run!
        self.__processOnlineDocuments(True)

        # show result:
        self.__printFullWidth("--")
        self.__printFullWidth(" Status Online Files  ")
        self.__printFullWidth("--")
        onlineStatus = " online "
        if not self.conn:
            onlineStatus = " not online "
        self.__printFullWidth("Current Status: " + onlineStatus, "left")
        self.__printFullWidth("--")
        self.__printLeftRight(
            "Files online all count: ", str(self.countOnlineAll), ".", 20
        )
        self.__printLeftRight(
            "Files online advertisment count: ",
            str(len(self.onlineAdvertismentIndicesList)),
            ".",
            20,
        )
        self.__printLeftRight(
            "Files online not yet read count: ",
            str(len(self.onlineUnreadIndicesList)),
            ".",
            20,
        )
        self.__printLeftRight(
            "Files online in archive count: ",
            str(len(self.onlineArchivedIndicesList)),
            ".",
            20,
        )
        self.__printLeftRight(
            "Files online filename matches count: ",
            str(len(self.onlineFileNameMatchingIndicesList)),
            ".",
            20,
        )
        self.__printLeftRight(
            "Files online already downloaded count: ",
            str(len(self.onlineAlreadyDownloadedIndicesList)),
            ".",
            20,
        )
        self.__printLeftRight(
            "Files online not yet downloaded count: ",
            str(len(self.onlineNotYetDownloadedIndicesList)),
            ".",
            20,
        )
        self.__printFullWidth("--")

    def __processOnlineDocuments(self, isCountRun=False):

        if not self.onlineDocumentsDict:
            return

        menuWidth = 200

        def __printStatus(idx, document, status=""):
            # fill idx to 5 chars
            idx = str(idx)
            idx = idx.zfill(5)
            if not isCountRun:
                self.__printLeftRight(
                    idx
                    + " - "
                    + document["dateCreation"]
                    + " - "
                    + document["name"]
                    + " - "
                    + document["mimeType"],
                    status,
                    ".",
                    menuWidth,
                )

        overwrite = False  # Only download new files
        useSubFolders = self.settings.getBoolValueForKey("useSubFolders")
        outputDir = self.settings.getValueForKey("outputDir")
        isDownloadOnlyFilename = self.settings.getBoolValueForKey(
            "downloadOnlyFilenames"
        )
        downloadFilenameList = self.settings.getValueForKey(
            "downloadOnlyFilenamesArray"
        )
        downloadOnlyFromOnlineArchive = self.settings.getBoolValueForKey(
            "downloadOnlyFromOnlineArchive"
        )

        countAll = len(self.onlineDocumentsDict)
        countProcessed = 0
        countSkipped = 0
        countDownloaded = 0

        # for idx in range(len(self.onlineDocumentsDict)): # documentMeta in enumerate(self.onlineDocumentsDict):
        for idx in self.onlineDocumentsDict:
            documentMeta = self.onlineDocumentsDict[idx]
            docName = documentMeta["name"]
            firstFilename = docName.split(" ", 1)[0]
            docMimeType = documentMeta["mimeType"]
            docCreateDate = documentMeta["dateCreation"]
            isDocAdvertisement = (
                True if str(documentMeta["advertisement"]).lower() == "true" else False
            )
            isDocArchived = (
                True
                if str(documentMeta["documentMetaData"]["archived"]).lower() == "true"
                else False
            )
            isAlreadyRead = (
                True
                if str(documentMeta["documentMetaData"]["alreadyRead"]).lower()
                == "true"
                else False
            )

            subFolder = ""
            myOutputDir = outputDir
            countProcessed += 1

            # counting
            if isDocAdvertisement:
                self.onlineAdvertismentIndicesList.append(idx)

            if isDocArchived:
                self.onlineArchivedIndicesList.append(idx)

            if firstFilename in downloadFilenameList:
                self.onlineFileNameMatchingIndicesList.append(idx)

            if not isAlreadyRead:
                self.onlineUnreadIndicesList.append(idx)

            # check for setting "only download if filename is in filename list"
            if downloadOnlyFromOnlineArchive and not isDocArchived:
                __printStatus(idx, documentMeta, "SKIPPED - not in archive")
                countSkipped += 1
                continue

            # check for setting "only download if filename is in filename list"
            if isDownloadOnlyFilename and not firstFilename in downloadFilenameList:
                __printStatus(
                    idx, documentMeta, "SKIPPED - filename not in filename list"
                )
                countSkipped += 1
                continue

            if docMimeType == "application/pdf":
                subFolder = firstFilename
                docName += ".pdf"
            elif docMimeType == "text/html":
                docName += ".html"
                subFolder = "html"

            if useSubFolders:
                myOutputDir = os.path.join(outputDir, subFolder)
                if not os.path.exists(myOutputDir):
                    os.makedirs(myOutputDir)

            filepath = os.path.join(myOutputDir, sanitize_filename(docName))

            # check if already downloaded
            if os.path.exists(filepath):
                self.onlineAlreadyDownloadedIndicesList.append(idx)
                if not overwrite:
                    __printStatus(idx, documentMeta, "SKIPPED - no overwrite")
                    countSkipped += 1
                    continue
            else:
                self.onlineNotYetDownloadedIndicesList.append(idx)

            # do the download
            if not bool(self.settings.getBoolValueForKey("dryRun")) and not isCountRun:
                docContent = self.conn.downloadMessage(documentMeta)
                moddate = time.mktime(
                    datetime.datetime.strptime(docCreateDate, "%Y-%m-%d").timetuple()
                )
                with open(filepath, "wb") as f:
                    f.write(docContent)
                    # shutil.copyfileobj(docContent, f)
                os.utime(filepath, (moddate, moddate))
                __printStatus(idx, documentMeta, "DOWNLOADED")
                countDownloaded += 1
            else:
                __printStatus(
                    idx, documentMeta, "DOWNLOADED - dry run, so not really downloaded"
                )
                countDownloaded += 1

        # last line, summary status:
        if not isCountRun:
            menuWidth = 74
            self.__printFullWidth("--", "center", "-", menuWidth)
            self.__printFullWidth("Status Files Downloading", "left", "-", menuWidth)
            print("All: " + str(countAll) + " files")
            print("Processed: " + str(countProcessed) + " files")
            print("Downloaded: " + str(countDownloaded) + " files")
            print("Skipped: " + str(countSkipped) + " files")


dirname = os.path.dirname(__file__)
main = Main(dirname)
