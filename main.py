#!/usr/bin/env python3

import json
from ComdirectConnection import Connection, Document, XOnceAuthenticationInfo
from settings import Settings
from pathvalidate._filename import sanitize_filename
from enum import Enum
from rich.console import Console
from rich.table import Table
from rich.prompt import IntPrompt
from rich.progress import (
    BarColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TaskProgressColumn
)
import os

ui_width=  200
console = Console(width=ui_width)

class IntPromptDeutsch(IntPrompt):
    validate_error_message = "[prompt.invalid]Bitte einen gültigen Wert eingeben"
    illegal_choice_message = "[prompt.invalid.choice]Bitte eine der gültigen Optionen auswählen"


def print(string: object, highlight : bool | None = None):
    console.print(string, highlight=highlight)


class DownloadSource(Enum):
    archivedOnly = "archivedOnly"
    notArchivedOnly = "notArchivedOnly"
    all = "all"


class Main:
    conn: Connection
    onlineDocumentsDict: dict[int, Document] = {}
    onlineAdvertismentIndicesList: list[int] = []
    onlineArchivedIndicesList: list[int] = []
    onlineUnreadIndicesList: list[int] = []
    onlineFileNameMatchingIndicesList: list[int] = []
    onlineNotYetDownloadedIndicesList: list[int] = []
    onlineAlreadyDownloadedIndicesList: list[int] = []

    def __init__(self, dirname: str):
        self.dirname = dirname
        try:
            self.settings = Settings(dirname)
        except Exception as error:
            print(error)
            input("Press ENTER to close. Create settings.ini from the example before trying again.")
            exit(0)

        self.showMenu()

    def showMenu(self):
        def __print_menu():
            onlineStatus = "[green]ONLINE[/green]"
            if not hasattr(self, "conn"):
                onlineStatus = "[red]OFFLINE[/red]"

            console.clear()
            header = Table(box=None, width= int(ui_width / 2))
            header.add_column(justify="left", width=5)
            header.add_column(justify="center")
            header.add_row("", "[b]Comdirect Documents Downloader", "")
            header.add_row("", "[dim]by [cyan]Senshi_x[/cyan] and [cyan]retiredHero[/cyan]", "")
            header.add_row("", f"{onlineStatus}", "")
            table = Table(width= int(ui_width / 2))
            table.add_column("", no_wrap=True, width=3, style="blue b")
            table.add_column("Aktion", style="cyan", ratio=999)
            table.add_row("(1)", "Einstellungen anzeigen")
            table.add_row("(2)", "Einstellungen neu aus Datei laden")
            table.add_row("(3)", "Status verfügbarer Dateien anzeigen (online)")
            table.add_row("(4)", "Verfügbare Dateien herunterladen (online)")
            table.add_row("(0)", "Beenden")

            print(header)
            print(table)

        loop = True
        val = 0
        __print_menu()
        # user_input = Prompt.ask("Wählen Sie eine Aktion", choices=["1", "2", "3", "4", "0"])

        while loop:
            __print_menu()
            val = IntPromptDeutsch.ask("Wählen Sie eine Aktion", choices=["1", "2", "3", "4", "0"])

            if val == 1:
                # Show Current Settings
                tSettings = Table()
                tSettings.add_column("Schlüssel")
                tSettings.add_column("Wert")
                settings = self.settings.getSettings()
                for key in settings:
                    value = settings[key]
                    if key in ["clientsecret", "pwd"]:
                        value = "******"
                    tSettings.add_row(key, value)
                console.print(tSettings)
            elif val == 2:
                # Reload Settings from file
                print("[i][cyan]Einstellungen wurden neu aus der settings.ini eingelesen.")
                self.settings.readSettings()
            elif val == 3:
                # show status online files
                self.__startConnection()
                self.__loadDocuments()
                self.__showStatusOnlineDocuments()
            elif val == 4:
                # start download of files
                self.__startConnection()
                self.__loadDocuments()
                self.__processOnlineDocuments()
            elif val == 0:
                loop = False

            if not val == 0:
                console.input("[b][blue]Enter[/blue][/b] drücken, um ins Menü zurückzukehren!")

        return val

    def __startConnection(self):
        """
        ToDo: Check if all settings are set for connection!
        """
        if not self.settings or hasattr(self, "conn"):
            print("Sie sind bereits angemeldet!")
            return
        self.conn = Connection(
            username=self.settings.getValueForKey("user"),
            password=self.settings.getValueForKey("pwd"),
            client_id=self.settings.getValueForKey("clientId"),
            client_secret=self.settings.getValueForKey("clientSecret"),
        )

        attempts = 0
        while attempts < 3:
            xauthinfoheaders: XOnceAuthenticationInfo = XOnceAuthenticationInfo(json.loads(self.conn.initSession().headers["x-once-authentication-info"]))
            attempts += 1
            tan = ""
            if xauthinfoheaders.typ == "P_TAN_PUSH":
                tan = ""
                print("Sie verwenden PushTAN. Bitte nutzen Sie nun die comdirect photoTAN app auf Ihrem Smartphone, um die Zugriffsanfrage namens 'Login persönlicher Bereich' zu genehmigen.")
                print("Bitte fahren Sie erst fort, wenn Sie dies getan haben! Nach dem fünften aufeinanderfolgenden Fehlversuch sperrt Comdirect den Zugang aus Sicherheitsgründen.")
                console.input("Drücken Sie ENTER, nachdem Sie die PushTAN Anfrage auf Ihrem Gerät genehmigt haben.")
            elif xauthinfoheaders.typ == "P_TAN" and hasattr(xauthinfoheaders, "challenge"):
                from PIL import Image
                import base64
                import io
                Image.open(io.BytesIO(base64.b64decode(xauthinfoheaders.challenge))).show()
                print("Bitte führen Sie die PhotoTAN Freigabe wie gewohnt mit ihrem Lesegerät oder App durch.")
                tan = input("Geben Sie die TAN ein: ")
            elif xauthinfoheaders.typ == "M_TAN" and hasattr(xauthinfoheaders, "challenge"):
                print(f"Bitte prüfen Sie Ihr Smartphone mit der Nummer {xauthinfoheaders.challenge} auf die erhaltene M-TAN")
                tan = input("Geben Sie die TAN ein: ")
            else:
                print(f"Tut mir Leid, das TAN-Verfahren {xauthinfoheaders.typ} wird (noch?) nicht unterstützt.")
                exit(1)
            r = self.conn.getSessionTAN(xauthinfoheaders.id, tan)
            rjson = r.json()
            if r.status_code == 422 and rjson["code"] == "expired":
                print("Der Zeitraum für die TAN-Freigabeanforderung ist abgelaufen. Bitte erneut versuchen.")
            elif r.status_code == 400 and rjson["code"] == "TAN_UNGUELTIG":
                print(rjson["messages"][0]["message"])
            elif r.status_code != 200:
                try:
                    j = r.json()
                    msg = j.get("message") if isinstance(j, dict) else None
                except Exception:
                    msg = None
                if msg:
                    print(f"HTTP Status: {r.status_code} | {msg}")
                else:
                    print(f"HTTP Status: {r.status_code}")
                if attempts > 2:
                    print("---")
                    print(
                        "Es sind drei Freigabeversuche in Folge fehlgeschlagen. Bitte vergewissern Sie sich, dass Sie korrekt arbeiten. "
                        "Sollten Sie unsicher sein, melden Sie sich einmal regulär auf der Comdirect-Webseite an, um eine Sperrung nach fünf aufeinanderfolgenden Fehlversuchen zu vermeiden."
                    )
                    print("---")
                    exit(1)
            # If successful, we trigger the secondary workflow to finish login
            self.conn.getCDSecondary()
            break
        print("Login erfolgreich!")

    def __loadDocuments(self):
        if not hasattr(self, "conn"):
            raise NameError("conn not set!")

        if self.onlineDocumentsDict:
            return

        # Getting a single value is needed to grab pagination info
        messagesMeta = self.conn.getMessagesList(0, 1)
        x = 0
        # Process batches of 1000. Max batchsize is 1000 (API restriction)
        batchSize = 1000
        self.onlineDocumentsDict = {}

        while x < messagesMeta.matches:
            messagesMeta = self.conn.getMessagesList(x, batchSize)

            for idx, document in enumerate(messagesMeta.documents):
                self.onlineDocumentsDict[x + idx] = document

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
        table = Table(width= int(ui_width / 2))
        table.add_column("", no_wrap=True, ratio = 999)
        table.add_column("Anzahl", style="blue b", width = 10, justify="right")
        table.add_row("Online-Dokumente gesamt", str(self.countOnlineAll))
        table.add_section()
        table.add_row("Davon ungelesen", str(len(self.onlineUnreadIndicesList)))
        table.add_row("Davon bereits heruntergeladen", str(len(self.onlineAlreadyDownloadedIndicesList)), style="dim")
        table.add_row("Davon noch nicht heruntergeladen", str(len(self.onlineNotYetDownloadedIndicesList)), style="dim")
        table.add_row("Davon Werbung", str(len(self.onlineAdvertismentIndicesList)), style="dim")
        table.add_row("Davon archiviert", str(len(self.onlineArchivedIndicesList)), style="dim")
        if self.settings.getBoolValueForKey("downloadOnlyFilenames"):
            table.add_row("Davon in der Liste gewünschter Dateinamen", str(len(self.onlineFileNameMatchingIndicesList)), style="dim")
        print(table)

    def __processOnlineDocuments(self, isCountRun: bool = False):
        if not self.onlineDocumentsDict:
            return

        def __printStatus(idx: int, document: Document, status: str = ""):
            # fill idx to 5 chars
            if isCountRun:
                return
            printLeftString = f"{str(idx):>5} | [cyan]{document.dateCreation.strftime('%Y-%m-%d')}[/cyan] | {sanitize_filename(document.name)}"
            printRightString = status
            filler: str = " "
            spaces = ui_width - len(printLeftString) - len(printRightString)
            if isinstance(console, Console):
                progress.console.print(printLeftString + (spaces * filler) + printRightString, highlight=False)
            else:
                print(printLeftString + (spaces * filler) + printRightString, highlight=False)

        def __isFileEqual(filepath : str, newdata : bytes):
            with open(filepath, 'rb') as f:
                data = f.read()
                return data == newdata
        progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn( bar_width= 150 ),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console = console,
            transient=isCountRun
        )
        with progress:
            overwrite = False  # Only download new files
            useSubFolders = self.settings.getBoolValueForKey("useSubFolders")
            outputDir = self.settings.getValueForKey("outputDir")
            downloadFilenameList = self.settings.getValueForKey("downloadOnlyFilenamesArray")
            downloadSource = self.settings.getValueForKey("downloadSource")

            countAll = len(self.onlineDocumentsDict)
            countProcessed = 0
            countSkipped = 0
            countDownloaded = 0

            task =progress.add_task("Downloading...",total=countAll)
            # for idx in range(len(self.onlineDocumentsDict)): # documentMeta in enumerate(self.onlineDocumentsDict):
            for idx in self.onlineDocumentsDict:
                progress.advance(task)
                document = self.onlineDocumentsDict[idx]
                firstFilename = document.name.split(" ", 1)[0]
                subFolder = ""
                myOutputDir = outputDir
                countProcessed += 1

                # counting
                if document.advertisement:
                    self.onlineAdvertismentIndicesList.append(idx)
                if document.documentMetadata.archived:
                    self.onlineArchivedIndicesList.append(idx)
                if firstFilename in downloadFilenameList:
                    self.onlineFileNameMatchingIndicesList.append(idx)
                if not document.documentMetadata.alreadyRead:
                    self.onlineUnreadIndicesList.append(idx)

                # check for setting "download source"
                if downloadSource == DownloadSource.archivedOnly.value and not document.documentMetadata.archived or downloadSource == DownloadSource.notArchivedOnly.value and document.documentMetadata.archived:
                    __printStatus(idx, document, "SKIPPED - not in selected download source")
                    countSkipped += 1
                    continue

                # check for setting "only download if filename is in filename list"
                if self.settings.getBoolValueForKey("downloadOnlyFilenames") and not firstFilename in downloadFilenameList:
                    __printStatus(idx, document, "SKIPPED - filename not in filename list")
                    countSkipped += 1
                    continue
                filename = document.name
                if document.mimeType == "application/pdf":
                    subFolder = "pdf"
                    filename += ".pdf"
                elif document.mimeType == "text/html":
                    subFolder = "html"
                    filename += ".html"
                else:
                    __printStatus(idx, document, f"Unknown mimeType {document.mimeType}")

                if useSubFolders:
                    myOutputDir : str = os.path.join(outputDir, sanitize_filename(subFolder))
                    if not os.path.exists(myOutputDir):
                        os.makedirs(myOutputDir)

                filepath = os.path.join(myOutputDir, sanitize_filename(filename))

                # do the download
                if bool(self.settings.getBoolValueForKey("dryRun")) or isCountRun:
                    __printStatus(idx, document, "HERUNTERGELADEN - Testlauf, kein tatsächlicher Download")
                    countDownloaded += 1
                    continue

                docDate = document.dateCreation.timestamp()
                docContent = None

                # check if already downloaded
                if os.path.exists(filepath):
                    if (self.settings.getBoolValueForKey("appendIfNameExists")):
                        if (docDate!= os.path.getmtime(filepath)): # If not the same, we simply append the date
                            # print(document.name)
                            # print(f"{docDate} {document.dateCreation.strftime("%Y-%m-%d")}")
                            # print(filepath)
                            # print(f"{os.path.getmtime(filepath)} {datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d")}")
                            path, suffix = filepath.rsplit(".",1)
                            filepath = f"{path}_{document.dateCreation.strftime('%Y-%m-%d')}.{suffix}"
                            # print("New filepath" + filepath)
                            if os.path.exists(filepath): # If there's multiple per same day, we append a counter
                                docContent = self.conn.downloadDocument(document) # Gotta load early to check if content is same
                                if __isFileEqual(filepath, docContent):
                                    __printStatus(idx, document, "ÜBERSPRUNGEN - Datei bereits heruntergeladen")
                                    countSkipped += 1
                                    self.onlineAlreadyDownloadedIndicesList.append(idx)
                                    continue
                                path, suffix = filepath.rsplit(".",1)
                                if path[-3] == "-" and path[-1].isdigit(): # We assume this is the day split YYYY-mm-dd, so no duplicate existed yet
                                    path += "_1"
                                else:
                                    counter = int(path[-1]) + 1 # We increase the counter by 1
                                    path = path[:-1] + str(counter)
                                filepath = f"{path}.{suffix}"
                                # print("New filepath" + filepath)
                                if os.path.exists(filepath): # Enough is enough...
                                    __printStatus(idx, document, "ÜBERSPRUNGEN - Datei bereits heruntergeladen")
                                    self.onlineNotYetDownloadedIndicesList.append(idx)
                                    continue
                        elif not overwrite:
                            __printStatus(idx, document, "ÜBERSPRUNGEN - Datei bereits heruntergeladen")
                            countSkipped += 1
                            self.onlineAlreadyDownloadedIndicesList.append(idx)
                            continue
                    elif not overwrite:
                        __printStatus(idx, document, "ÜBERSPRUNGEN - appendIfNameExists ist FALSE")
                        countSkipped += 1
                        self.onlineAlreadyDownloadedIndicesList.append(idx)
                        continue
                if not docContent: # Ensure data is loaded
                    docContent = self.conn.downloadDocument(document)
                with open(filepath, "wb") as f:
                    f.write(docContent)
                    # shutil.copyfileobj(docContent, f)
                os.utime(filepath, (docDate, docDate))
                __printStatus(idx, document, "HERUNTERGELADEN")
                countDownloaded += 1

            # last line, summary status:
            if not isCountRun:
                table = Table(width= int(ui_width / 2))
                table.add_column("Zusammenfassung", no_wrap=True, ratio = 999)
                table.add_column("Anzahl", style="blue b", width = 10, justify="right")
                table.add_row("Dokumente gesamt", str(countAll))
                table.add_section()
                table.add_row("Davon verarbeitet", str(countProcessed))
                table.add_row("Davon heruntergeladen", str(countDownloaded))
                table.add_row("Davon übersprungen", str(countSkipped), style="dim")
                print(table)


dirname = os.path.dirname(__file__)
main = Main(dirname)
