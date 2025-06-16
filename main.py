#!/usr/bin/env python3

import json
from ComdirectConnection import Connection, Document, XOnceAuthenticationInfo
from settings import Settings
from pathvalidate._filename import sanitize_filename
from typing import Any
from enum import Enum
from rich.console import Console
from rich.table import Table
from rich.prompt import IntPrompt, Prompt # Importiere Prompt für String-Eingaben
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

class PromptDeutsch(Prompt):
    validate_error_message = "[prompt.invalid]Bitte einen gültigen Wert eingeben"

def print(string: Any, highlight : bool| None= None):
    console.print(string, highlight=highlight)


class DownloadSource(Enum):
    archivedOnly = "archivedOnly"
    notArchivedOnly = "notArchivedOnly"
    all = "all"


class Main:
    conn: Connection | None = None # Setze auf None initial
    onlineDocumentsDict: dict[int, Document] = {}
    onlineAdvertismentIndicesList: list[int] = []
    onlineArchivedIndicesList: list[int] = []
    onlineUnreadIndicesList: list[int] = []
    onlineFileNameMatchingIndicesList: list[int] = []
    onlineNotYetDownloadedIndicesList: list[int] = []
    onlineAlreadyDownloadedIndicesList: list[int] = []
    current_user_profile: dict[str, str] | None = None # Speichert das aktuell ausgewählte Benutzerprofil

    def __init__(self, dirname: str):
        self.dirname = dirname
        try:
            self.settings = Settings(dirname)
            # Setze die console für die Settings-Klasse, damit __printMessage korrekt funktioniert
            self.settings._console = console
        except FileNotFoundError as error: # Fange spezifisch FileNotFoundError ab
            print(f"[bold red]FEHLER:[/bold red] {error}")
            input("Press ENTER to close. Create settings.ini from the example before trying again.")
            exit(0)
        except Exception as error:
            print(f"[bold red]FEHLER beim Laden der Einstellungen:[/bold red] {error}")
            input("Press ENTER to close.")
            exit(0)


        self.showMenu()

    def showMenu(self):
        def __print_menu():
            onlineStatus = "[green]ONLINE[/green]"
            if not self.conn: # Prüfe auf self.conn statt hasattr
                onlineStatus = "[red]OFFLINE[/red]"

            current_user_display = "[dim](Kein Benutzer ausgewählt)[/dim]"
            if self.current_user_profile:
                current_user_display = f"[bold green]{self.current_user_profile['user']}[/bold green]"

            console.clear()
            header = Table(box=None, width= int(ui_width / 2))
            header.add_column(justify="left", width=5)
            header.add_column(justify="center")
            header.add_row("", "[b]Comdirect Documents Downloader", "")
            header.add_row("", "[dim]by [cyan]Senshi_x[/cyan] and [cyan]retiredHero[/cyan]", "")
            header.add_row("", f"Status: {onlineStatus} | Aktueller Benutzer: {current_user_display}", "") # Zeigt den aktuellen Benutzer
            table = Table(width= int(ui_width / 2))
            table.add_column("", no_wrap=True, width=3, style="blue b")
            table.add_column("Aktion", style="cyan", ratio=999)
            table.add_row("(1)", "Einstellungen anzeigen (globale & Benutzerprofile)")
            table.add_row("(2)", "Einstellungen neu aus Datei laden")
            table.add_row("(3)", "Status verfügbarer Dateien anzeigen (online)")
            table.add_row("(4)", "Verfügbare Dateien herunterladen (online)")
            table.add_row("(0)", "Beenden")

            print(header)
            print(table)

        loop = True
        val = 0
        while loop:
            __print_menu()
            val = IntPromptDeutsch.ask("Wählen Sie eine Aktion", choices=["1", "2", "3", "4", "0"])

            if val == 1:
                self.settings.showSettings() # Ruft die aktualisierte showSettings in settings.py auf
            elif val == 2:
                print("[i][cyan]Einstellungen wurden neu aus der settings.ini eingelesen.")
                # Verbindung zurücksetzen, da sich Credentials geändert haben könnten
                self.conn = None
                self.current_user_profile = None
                self.settings.readSettings()
            elif val == 3:
                # show status online files
                self.__selectUserAndConnect() # Zuerst Benutzer auswählen und verbinden
                if self.conn: # Nur fortfahren, wenn Verbindung erfolgreich war
                    self.__loadDocuments()
                    self.__showStatusOnlineDocuments()
            elif val == 4:
                # start download of files
                self.__selectUserAndConnect() # Zuerst Benutzer auswählen und verbinden
                if self.conn: # Nur fortfahren, wenn Verbindung erfolgreich war
                    self.__loadDocuments()
                    self.__processOnlineDocuments()
            elif val == 0:
                loop = False

            if not val == 0:
                console.input("[b][blue]Enter[/blue][/b] drücken, um ins Menü zurückzukehren!")

        return val

    def __selectUserAndConnect(self):
        """
        Ermöglicht dem Benutzer, ein Profil auszuwählen, und versucht, eine Verbindung herzustellen.
        """
        user_profiles = self.settings.getProfileNames()
        if not user_profiles:
            print("[bold red]FEHLER:[/bold red] Keine Benutzerprofile in der settings.ini gefunden (Abschnitte beginnend mit 'USER_').")
            self.conn = None # Stelle sicher, dass die Verbindung zurückgesetzt ist
            return

        if self.conn and self.current_user_profile:
            print(f"[green]Bereits mit Benutzer '{self.current_user_profile['user']}' verbunden.[/green]")
            # Frage, ob die Verbindung mit diesem Benutzer fortgesetzt oder gewechselt werden soll
            choice = PromptDeutsch.ask("Möchten Sie die Verbindung mit diesem Benutzer fortsetzen oder einen anderen Benutzer auswählen?", choices=["fortsetzen", "wechseln"], default="fortsetzen")
            if choice == "fortsetzen":
                return
            else:
                self.conn = None # Alte Verbindung trennen
                self.current_user_profile = None

        console.clear()
        print("[b]Verfügbare Benutzerprofile:[/b]")
        user_table = Table(width=int(ui_width / 2))
        user_table.add_column("Nr.", style="blue b", width=5)
        user_table.add_column("Benutzername", style="cyan", ratio=999)
        for i, profile_name in enumerate(user_profiles):
            # Zeige nur den Profilnamen, nicht die Credentials
            profile_settings = self.settings.getProfileSettings(profile_name)
            user_table.add_row(str(i + 1), profile_settings.get("user", profile_name)) # Zeige 'user' oder Profilnamen
        print(user_table)

        selected_index = IntPromptDeutsch.ask("Bitte wählen Sie ein Benutzerprofil aus", choices=[str(i + 1) for i in range(len(user_profiles))])
        selected_profile_name = user_profiles[selected_index - 1]
        self.current_user_profile = self.settings.getProfileSettings(selected_profile_name)

        print(f"[yellow]Verbinde mit Benutzer:[/yellow] {self.current_user_profile['user']}")

        self.__startConnection()


    def __startConnection(self):
        """
        Stellt die tatsächliche Verbindung zum Comdirect Server her, basierend auf dem ausgewählten Benutzerprofil.
        """
        if not self.current_user_profile:
            print("[bold red]FEHLER:[/bold red] Kein Benutzerprofil ausgewählt.")
            return

        # Wenn bereits eine Verbindung besteht und es der gleiche Benutzer ist, nichts tun
        if self.conn and hasattr(self.conn, 'username') and self.conn.username == self.current_user_profile["user"]:
            print(f"[green]Bereits mit '{self.current_user_profile['user']}' verbunden.[/green]")
            return

        print(f"Versuche Verbindung für Benutzer: [bold]{self.current_user_profile['user']}[/bold]")
        self.conn = Connection(
            username=self.current_user_profile["user"],
            password=self.current_user_profile["pwd"],
            client_id=self.current_user_profile["clientId"],
            client_secret=self.current_user_profile["clientSecret"],
        )

        attempts = 0
        while attempts < 3:
            try:
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
                    self.conn = None # Verbindung bei nicht unterstützter TAN-Methode zurücksetzen
                    return # Verbindung fehlgeschlagen, zurück zum Menü
                
                r = self.conn.getSessionTAN(xauthinfoheaders.id, tan)
                rjson = r.json()
                if r.status_code == 422 and rjson["code"] == "expired":
                    print("Der Zeitraum für die TAN-Freigabeanforderung ist abgelaufen. Bitte erneut versuchen.")
                elif r.status_code == 400 and rjson["code"] == "TAN_UNGUELTIG":
                    print(rjson["messages"][0]["message"])
                elif r.status_code != 200:
                    print(f"HTTP Status: {r.status_code} | {r.json()}")
                    if attempts > 2:
                        print("---")
                        print(
                            "Es sind drei Freigabeversuche in Folge fehlgeschlagen. Bitte vergewissern Sie sich, dass Sie korrekt arbeiten. "
                            "Sollten Sie unsicher sein, melden Sie sich einmal regulär auf der Comdirect-Webseite an, um eine Sperrung nach fünf aufeinanderfolgenden Fehlversuchen zu vermeiden."
                        )
                        print("---")
                        self.conn = None # Verbindung bei zu vielen Fehlversuchen zurücksetzen
                        return # Verbindung fehlgeschlagen, zurück zum Menü
                
                # Wenn erfolgreich, den Secondary Workflow abschließen
                self.conn.getCDSecondary()
                print("Login erfolgreich!")
                return # Verbindung erfolgreich hergestellt
            
            except Exception as e:
                print(f"[bold red]Fehler bei der Verbindung:[/bold red] {e}")
                if attempts > 2:
                    print("[bold red]Maximale Anzahl von Verbindungsversuchen erreicht.[/bold red]")
                    self.conn = None
                    return # Verbindung fehlgeschlagen, zurück zum Menü

        print("[bold red]Verbindung konnte nicht hergestellt werden.[/bold red]")
        self.conn = None # Sicherstellen, dass die Verbindung im Fehlerfall None ist


    def __loadDocuments(self):
        if not self.conn:
            print("[bold red]FEHLER:[/bold red] Keine aktive Verbindung. Bitte zuerst anmelden.")
            return

        if self.onlineDocumentsDict:
            print("[yellow]Dokumente sind bereits geladen. Lade nicht erneut.[/yellow]")
            return

        print("[green]Lade Dokumentenliste von Comdirect...[/green]")
        try:
            # Getting a single value is needed to grab pagination info
            messagesMeta = self.conn.getMessagesList(0, 1)
            x = 0
            # Process batches of 1000. Max batchsize is 1000 (API restriction)
            batchSize = 1000
            self.onlineDocumentsDict = {}

            total_documents = messagesMeta.matches
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(f"[cyan]Lade Dokumente ({total_documents} gesamt)...[/cyan]", total=total_documents)
                
                while x < messagesMeta.matches:
                    current_batch = self.conn.getMessagesList(x, batchSize)
                    for idx, document in enumerate(current_batch.documents):
                        self.onlineDocumentsDict[x + idx] = document
                    x += batchSize
                    progress.update(task, completed=x if x <= total_documents else total_documents)
            
            print(f"[green]Dokumentenliste erfolgreich geladen. {len(self.onlineDocumentsDict)} Dokumente gefunden.[/green]")

        except Exception as e:
            print(f"[bold red]FEHLER beim Laden der Dokumentenliste:[/bold red] {e}")
            self.onlineDocumentsDict = {} # Sicherstellen, dass das Dict leer ist im Fehlerfall


    def __showStatusOnlineDocuments(self):
        if not self.onlineDocumentsDict:
            print("[yellow]Keine Dokumente geladen. Bitte zuerst Dokumente laden (Option 3 oder 4).[/yellow]")
            return

        self.onlineAdvertismentIndicesList = []
        self.onlineArchivedIndicesList = []
        self.onlineFileNameMatchingIndicesList = []
        self.onlineNotYetDownloadedIndicesList = []
        self.onlineAlreadyDownloadedIndicesList = []
        self.onlineUnreadIndicesList = []

        self.countOnlineAll = len(self.onlineDocumentsDict)

        # do the count run!
        self.__processOnlineDocuments(isCountRun=True)

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
        
        # Achtung: hier wird immer noch die DEFAULT Einstellung abgerufen. Das ist korrekt,
        # da downloadOnlyFilenames eine globale Einstellung ist, kein user-spezifischer Filter.
        # Wenn downloadOnlyFilenamesArray user-spezifisch sein soll, muss es in user_profiles verschoben werden.
        if self.settings.getBoolValueForKey("downloadOnlyFilenames"):
            table.add_row("Davon in der Liste gewünschter Dateinamen", str(len(self.onlineFileNameMatchingIndicesList)), style="dim")
        print(table)

    def __processOnlineDocuments(self, isCountRun: bool = False):
        if not self.onlineDocumentsDict:
            print("[yellow]Keine Dokumente zum Verarbeiten/Herunterladen geladen.[/yellow]")
            return
        if not self.conn and not isCountRun:
             print("[bold red]FEHLER:[/bold red] Keine aktive Verbindung zum Herunterladen. Bitte zuerst anmelden.")
             return


        def __printStatus(idx: int, document: Document, status: str = ""):
            # fill idx to 5 chars
            if isCountRun:
                return
            printLeftString = f"{str(idx):>5} | [cyan]{document.dateCreation.strftime('%Y-%m-%d')}[/cyan] | {sanitize_filename(document.name)}"
            printRightString = status
            filler: str = " "
            spaces = ui_width - len(printLeftString) - len(printRightString)
            # Direkt die Progress Console verwenden, um Überschneidungen zu vermeiden
            progress.console.print(printLeftString + (spaces * filler) + printRightString, highlight=False)

        def __isFileEqual(filepath : str, newdata : bytes):
            with open(filepath, 'rb') as f:
                data = f.read()
                return data == newdata
        
        progress_description = "Zähle Dokumente..." if isCountRun else "Lade Dokumente herunter..."
        progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn( bar_width= 150 ),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console = console,
            transient=isCountRun # Fortschrittsbalken verschwindet nach Abschluss im Zählmodus
        )
        with progress:
            # Einstellungen, die hier genutzt werden, sind globale Einstellungen aus DEFAULT
            overwrite = False  # Bleibt auf False, da appendIfNameExists die Strategie ist
            useSubFolders = self.settings.getBoolValueForKey("useSubFolders")
            outputDir = self.settings.getValueForKey("outputDir")
            downloadFilenameList = self.settings.getValueForKey("downloadOnlyFilenamesArray")
            downloadSource = self.settings.getValueForKey("downloadSource")
            appendIfNameExists = self.settings.getBoolValueForKey("appendIfNameExists")


            countAll = len(self.onlineDocumentsDict)
            countProcessed = 0
            countSkipped = 0
            countDownloaded = 0

            task = progress.add_task(progress_description, total=countAll)
            
            for idx in self.onlineDocumentsDict:
                progress.advance(task)
                document = self.onlineDocumentsDict[idx]
                firstFilename = document.name.split(" ", 1)[0]
                subFolder = ""
                myOutputDir = outputDir
                countProcessed += 1

                # counting (always done)
                if document.advertisement:
                    self.onlineAdvertismentIndicesList.append(idx)
                if document.documentMetadata.archived:
                    self.onlineArchivedIndicesList.append(idx)
                if firstFilename in downloadFilenameList:
                    self.onlineFileNameMatchingIndicesList.append(idx)
                if not document.documentMetadata.alreadyRead:
                    self.onlineUnreadIndicesList.append(idx)

                # Filtering (only skip if not count run)
                if not isCountRun:
                    # check for setting "download source"
                    if (downloadSource == DownloadSource.archivedOnly.value and not document.documentMetadata.archived) or \
                       (downloadSource == DownloadSource.notArchivedOnly.value and document.documentMetadata.archived):
                        __printStatus(idx, document, "SKIPPED - nicht in gewählter Download-Quelle")
                        countSkipped += 1
                        continue

                    # check for setting "only download if filename is in filename list"
                    if self.settings.getBoolValueForKey("downloadOnlyFilenames") and firstFilename not in downloadFilenameList:
                        __printStatus(idx, document, "SKIPPED - Dateiname nicht in der Filterliste")
                        countSkipped += 1
                        continue
                
                filename_base = document.name
                file_extension = ""

                if document.mimeType == "application/pdf":
                    subFolder = "pdf"
                    file_extension = ".pdf"
                elif document.mimeType == "text/html":
                    subFolder = "html"
                    file_extension = ".html"
                else:
                    # Wenn unbekannter MIME-Typ und nicht im Zählmodus, dann springe über
                    if not isCountRun:
                        __printStatus(idx, document, f"ÜBERSPRUNGEN - Unbekannter MIME-Typ {document.mimeType}")
                        countSkipped += 1
                    continue # Überspringe diesen Dokumenttyp im Zählmodus und im Download-Modus

                filename = filename_base + file_extension

                if useSubFolders:
                    myOutputDir : str = os.path.join(outputDir, sanitize_filename(subFolder))
                    if not os.path.exists(myOutputDir):
                        os.makedirs(myOutputDir)

                filepath = os.path.join(myOutputDir, sanitize_filename(filename))

                # If it's just a count run, we only populate lists and don't download
                if isCountRun:
                    if os.path.exists(filepath):
                        # Im Zählmodus ist es nur eine Annahme, ob die Datei existiert
                        self.onlineAlreadyDownloadedIndicesList.append(idx)
                    else:
                        self.onlineNotYetDownloadedIndicesList.append(idx)
                    continue # Beende die Iteration für den Zählmodus hier

                # ---- Ab hier beginnt der tatsächliche Download-Prozess (nicht im isCountRun-Modus) ----
                
                # Dry Run Check
                if self.settings.getBoolValueForKey("dryRun"):
                    __printStatus(idx, document, "SIMULIERT - Testlauf, kein tatsächlicher Download")
                    countDownloaded += 1 # Als "heruntergeladen" zählen im Dry Run
                    continue

                docDate = document.dateCreation.timestamp()
                docContent = None # Muss hier initialisiert werden

                # Check if already downloaded and handle `appendIfNameExists`
                final_filepath = filepath
                if os.path.exists(filepath):
                    if appendIfNameExists:
                        # Lade den Inhalt frühzeitig, um Dateigleichheit zu prüfen
                        try:
                            docContent = self.conn.downloadDocument(document)
                        except Exception as e:
                            __printStatus(idx, document, f"FEHLER beim Download für Vergleich: {e}")
                            countSkipped += 1
                            continue

                        if __isFileEqual(filepath, docContent):
                            __printStatus(idx, document, "ÜBERSPRUNGEN - Datei bereits existiert (Inhalt gleich)")
                            countSkipped += 1
                            self.onlineAlreadyDownloadedIndicesList.append(idx)
                            continue # Überspringe, da identisch

                        # Inhalt ist ungleich oder Datum ungleich, versuche Umbenennung
                        path_without_ext, suffix = filepath.rsplit(".", 1)
                        new_path_base = f"{path_without_ext}_{document.dateCreation.strftime('%Y-%m-%d')}"
                        final_filepath = f"{new_path_base}.{suffix}"
                        
                        counter = 1
                        while os.path.exists(final_filepath):
                            if docContent and __isFileEqual(final_filepath, docContent):
                                __printStatus(idx, document, "ÜBERSPRUNGEN - Datei existiert bereits (Inhalt gleich)")
                                countSkipped += 1
                                self.onlineAlreadyDownloadedIndicesList.append(idx)
                                break # Breche innere Schleife ab, da Datei existiert und identisch ist
                            
                            counter += 1
                            final_filepath = f"{new_path_base}_{counter}.{suffix}"
                        else: # Only runs if the while loop completes without a break
                            if os.path.exists(final_filepath) and docContent and __isFileEqual(final_filepath, docContent):
                                # Doppelte Prüfung, falls der letzte Loop-Check fehlschlägt, aber Datei doch existiert und gleich ist
                                __printStatus(idx, document, "ÜBERSPRUNGEN - Datei existiert bereits (Inhalt gleich)")
                                countSkipped += 1
                                self.onlineAlreadyDownloadedIndicesList.append(idx)
                                continue
                            
                            # Wenn wir hier ankommen, haben wir einen eindeutigen Pfad gefunden oder die Datei existiert nicht
                            if not docContent: # Falls noch nicht geladen für Vergleich
                                try:
                                    docContent = self.conn.downloadDocument(document)
                                except Exception as e:
                                    __printStatus(idx, document, f"FEHLER beim Download: {e}")
                                    countSkipped += 1
                                    continue
                            
                            with open(final_filepath, "wb") as f:
                                f.write(docContent)
                            os.utime(final_filepath, (docDate, docDate))
                            __printStatus(idx, document, f"HERUNTERGELADEN (umbenannt zu {os.path.basename(final_filepath)})")
                            countDownloaded += 1
                            continue # Gehe zum nächsten Dokument
                        
                        if counter > 1 and os.path.exists(final_filepath) and docContent and __isFileEqual(final_filepath, docContent):
                             # Dies fängt den Fall ab, dass die äußere Schleife durchlaufen wurde
                             # und wir bereits einen Treffer hatten (break in innerer while-Schleife)
                            continue
                        elif os.path.exists(final_filepath):
                            # Wenn wir hier ankommen und die Datei immer noch existiert und nicht identisch ist, überspringen wir
                            __printStatus(idx, document, "ÜBERSPRUNGEN - Datei existiert bereits und konnte nicht eindeutig gespeichert werden")
                            countSkipped += 1
                            self.onlineNotYetDownloadedIndicesList.append(idx) # zählt als nicht heruntergeladen
                            continue
                            

                    else: # appendIfNameExists ist False und Datei existiert bereits, überspringe
                        __printStatus(idx, document, "ÜBERSPRUNGEN - Datei existiert bereits (Überschreiben deaktiviert)")
                        countSkipped += 1
                        self.onlineAlreadyDownloadedIndicesList.append(idx)
                        continue
                
                # Wenn wir hier ankommen, muss die Datei heruntergeladen werden
                if not docContent: # Falls noch nicht für Vergleich geladen
                    try:
                        docContent = self.conn.downloadDocument(document)
                    except Exception as e:
                        __printStatus(idx, document, f"FEHLER beim Download: {e}")
                        countSkipped += 1
                        continue

                with open(final_filepath, "wb") as f:
                    f.write(docContent)
                os.utime(final_filepath, (docDate, docDate))
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