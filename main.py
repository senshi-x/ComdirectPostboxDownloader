#!/usr/bin/env python3

import json
import sys
import os
import shutil # Für Dateivergleich
from typing import Any
from enum import Enum

# --- Robuste rich-Initialisierung ---
# Versuche, rich zu importieren und Console zu initialisieren
try:
    from rich.console import Console
    from rich.table import Table
    from rich.prompt import IntPrompt, Prompt
    from rich.progress import (
        BarColumn,
        Progress,
        TextColumn,
        TimeRemainingColumn,
        TaskProgressColumn
    )
    # Wenn rich erfolgreich importiert wurde, initialisiere Console
    ui_width = 200
    console = Console(width=ui_width)

    # Überschreibe die print-Funktion nur, wenn rich verfügbar ist
    def print_rich(string: Any, highlight : bool| None= None):
        console.print(string, highlight=highlight)
    # Standard-Print-Funktion, die rich nutzt
    _print_func = print_rich

    # Rich-spezifische Prompt-Klassen
    class IntPromptDeutsch(IntPrompt):
        validate_error_message = "[prompt.invalid]Bitte einen gültigen Wert eingeben"
        illegal_choice_message = "[prompt.invalid.choice]Bitte eine der gültigen Optionen auswählen"

    class PromptDeutsch(Prompt):
        validate_error_message = "[prompt.invalid]Bitte einen gültigen Wert eingeben"

except ImportError as e:
    # Wenn rich nicht gefunden wird, nutze Standard-print
    print(f"WARNUNG: rich Bibliothek konnte nicht importiert werden ({e}). UI wird nur als einfacher Text angezeigt.")
    print("Bitte stellen Sie sicher, dass 'pip install rich' ausgeführt wurde.")
    
    # Definiere Dummy-Klassen und Funktionen, damit der Rest des Codes nicht abstürzt
    # und ein rudimentäres CLI funktioniert.
    class Console:
        def __init__(self, *args, **kwargs):
            pass
        def print(self, *args, **kwargs):
            # Fallback for console.print
            __builtins__.print(*args)
        def clear(self):
            # In einem einfachen Terminal macht clear keinen Sinn, daher leer
            pass
        def input(self, prompt=""):
            return __builtins__.input(prompt)

    class Table:
        def __init__(self, *args, **kwargs):
            # Dummy für Table, wird die Ausgabe nur als einfache Zeilen ausgeben
            self._rows = []
            self._headers = []
        def add_column(self, header, *args, **kwargs):
            self._headers.append(header)
        def add_row(self, *args):
            self._rows.append(list(args))
        def add_section(self):
            # Dummy, macht nichts in einfacher Ausgabe
            pass
        def __str__(self):
            # Einfache Textdarstellung der Tabelle
            output = " | ".join(self._headers) + "\n"
            output += "-" * len(output) + "\n"
            for row in self._rows:
                output += " | ".join(map(str, row)) + "\n"
            return output

    class IntPromptDeutsch: # Dummy, verwendet Standard-input
        @staticmethod
        def ask(prompt="", choices=None, default=None):
            if choices:
                return int(input(f"{prompt} ({'/'.join(choices)}) [{default}]: ") or default)
            return int(input(f"{prompt}: "))

    class PromptDeutsch: # Dummy, verwendet Standard-input
        @staticmethod
        def ask(prompt="", choices=None, default=None):
            if choices:
                return input(f"{prompt} ({'/'.join(choices)}) [{default}]: ") or default
            return input(f"{prompt}: ")

    class Progress: # Dummy, tut nichts
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
        def add_task(self, *args, **kwargs): return 0
        def advance(self, *args, **kwargs): pass
        def update(self, *args, **kwargs): pass

    # Setze _print_func auf die eingebaute print-Funktion
    _print_func = __builtins__.print

except Exception as e:
    # Andere unerwartete Fehler bei der Initialisierung von rich
    # Wenn selbst die Dummy-Definitionen fehlschlagen, dann ist hier ein ernstes Problem
    print(f"KRITISCHER FEHLER: Unerwarteter Fehler bei der Initialisierung der UI-Bibliothek ({e}).")
    print("Das Skript kann nicht fortgesetzt werden.")
    sys.exit(1) # Beende das Skript bei kritischem Fehler

# Die globale print-Funktion, die im gesamten Skript verwendet wird
def print(string: Any, highlight : bool| None= None):
    _print_func(string, highlight=highlight)

# --- Ende der robusten rich-Initialisierung ---

# Importe, die von rich abhängen, müssen nach der rich-Initialisierung stehen
from ComdirectConnection import Connection, Document, XOnceAuthenticationInfo
from settings import Settings
from pathvalidate._filename import sanitize_filename # Hier sollte es importiert sein

class DownloadSource(Enum):
    archivedOnly = "archivedOnly"
    notArchivedOnly = "notArchivedOnly"
    all = "all"

class Main:
    conn: Connection | None = None
    onlineDocumentsDict: dict[int, Document] = {}
    onlineAdvertismentIndicesList: list[int] = []
    onlineArchivedIndicesList: list[int] = []
    onlineUnreadIndicesList: list[int] = []
    onlineFileNameMatchingIndicesList: list[int] = []
    onlineNotYetDownloadedIndicesList: list[int] = []
    onlineAlreadyDownloadedIndicesList: list[int] = []
    current_user_profile: dict[str, str] | None = None

    def __init__(self, dirname: str):
        self.dirname = dirname
        try:
            self.settings = Settings(dirname)
            # Übergebe das Rich-Console-Objekt an die Settings-Klasse, falls es erfolgreich initialisiert wurde
            if 'console' in globals() and isinstance(console, Console):
                self.settings._console = console
            
        except Exception as error: # Fange alle Exceptions beim Laden der Settings ab
            print(f"[bold red]FEHLER beim Laden der Einstellungen:[/bold red] {error}")
            input("Press ENTER to close.") # Nutze hier die Standard-input, da rich evtl. nicht geht
            sys.exit(1) # Beende das Skript bei einem Fehler

        self.showMenu()

    def showMenu(self):
        def __print_menu():
            onlineStatus = "[green]ONLINE[/green]"
            if not self.conn:
                onlineStatus = "[red]OFFLINE[/red]"

            current_user_display = "[dim](Kein Benutzer ausgewählt)[/dim]"
            if self.current_user_profile and 'user' in self.current_user_profile:
                current_user_display = f"[bold green]{self.current_user_profile['user']}[/bold green]"

            # rich.console.Console().clear() aufrufen, wenn rich aktiv ist, sonst passiert nichts
            if 'console' in globals() and isinstance(console, Console):
                console.clear()

            header = Table(box=None, width= int(ui_width / 2)) # Nutze die globale ui_width
            header.add_column(justify="left", width=5)
            header.add_column(justify="center")
            header.add_row("", "[b]Comdirect Documents Downloader", "")
            header.add_row("", "[dim]by [cyan]Senshi_x[/cyan] and [cyan]retiredHero[/cyan]", "")
            header.add_row("", f"Status: {onlineStatus} | Aktueller Benutzer: {current_user_display}", "")
            table = Table(width= int(ui_width / 2)) # Nutze die globale ui_width
            table.add_column("", no_wrap=True, width=3, style="blue b")
            table.add_column("Aktion", style="cyan", ratio=999)
            table.add_row("(1)", "Einstellungen anzeigen (globale & Benutzerprofile)")
            table.add_row("(2)", "Einstellungen neu aus Datei laden")
            table.add_row("(3)", "Status verfügbarer Dateien anzeigen (online)")
            table.add_row("(4)", "Verfügbare Dateien herunterladen (online)")
            table.add_row("(0)", "Beenden")

            print(header) # print die Tabelle
            print(table) # print die Tabelle

        loop = True
        val = 0
        while loop:
            __print_menu()
            # Nutze die korrekte Prompt-Klasse (IntPromptDeutsch oder Dummy)
            val = IntPromptDeutsch.ask("Wählen Sie eine Aktion", choices=["1", "2", "3", "4", "0"])

            if val == 1:
                self.settings.showSettings()
            elif val == 2:
                print("[i][cyan]Einstellungen wurden neu aus der settings.ini eingelesen.[/cyan][/i]")
                self.conn = None
                self.current_user_profile = None
                self.onlineDocumentsDict = {} # Dokumente leeren, da Einstellungen neu geladen werden
                self.settings.readSettings()
            elif val == 3:
                self.__selectUserAndConnect()
                if self.conn:
                    self.__loadDocuments()
                    self.__showStatusOnlineDocuments()
            elif val == 4:
                self.__selectUserAndConnect()
                if self.conn:
                    self.__loadDocuments()
                    self.__processOnlineDocuments()
            elif val == 0:
                loop = False

            if not val == 0:
                # Nutze die korrekte input-Funktion (console.input oder Standard-input)
                if 'console' in globals() and isinstance(console, Console):
                    console.input("[b][blue]Enter[/blue][/b] drücken, um ins Menü zurückzukehren!")
                else:
                    input("Enter drücken, um ins Menü zurückzukehren!")

        return val

    def __selectUserAndConnect(self):
        user_profiles = self.settings.getProfileNames()
        if not user_profiles:
            print("[bold red]FEHLER:[/bold red] Keine Benutzerprofile in der settings.ini gefunden (Abschnitte beginnend mit 'USER_').")
            self.conn = None
            return

        if self.conn and self.current_user_profile and 'user' in self.current_user_profile:
            print(f"[green]Bereits mit Benutzer '{self.current_user_profile['user']}' verbunden.[/green]")
            choice = PromptDeutsch.ask("Möchten Sie die Verbindung mit diesem Benutzer fortsetzen oder einen anderen Benutzer auswählen?", choices=["fortsetzen", "wechseln"], default="fortsetzen")
            if choice == "fortsetzen":
                return
            else:
                self.conn = None
                self.current_user_profile = None
                self.onlineDocumentsDict = {}

        if 'console' in globals() and isinstance(console, Console):
            console.clear()
        
        print("[b]Verfügbare Benutzerprofile:[/b]")
        user_table = Table(width=int(ui_width / 2))
        user_table.add_column("Nr.", style="blue b", width=5)
        user_table.add_column("Benutzername", style="cyan", ratio=999)
        for i, profile_name in enumerate(user_profiles):
            profile_settings = self.settings.getProfileSettings(profile_name)
            user_table.add_row(str(i + 1), profile_settings.get("user", profile_name))
        print(user_table)

        selected_index = IntPromptDeutsch.ask("Bitte wählen Sie ein Benutzerprofil aus", choices=[str(i + 1) for i in range(len(user_profiles))])
        selected_profile_name = user_profiles[selected_index - 1]
        self.current_user_profile = self.settings.getProfileSettings(selected_profile_name)

        print(f"[yellow]Verbinde mit Benutzer:[/yellow] {self.current_user_profile['user']}")

        self.__startConnection()

    def __startConnection(self):
        if not self.current_user_profile:
            print("[bold red]FEHLER:[/bold red] Kein Benutzerprofil ausgewählt.")
            self.conn = None
            return

        if self.conn and hasattr(self.conn, 'username') and self.conn.username == self.current_user_profile["user"]:
            print(f"[green]Bereits mit '{self.current_user_profile['user']}' verbunden.[/green]")
            return

        print(f"Versuche Verbindung für Benutzer: [bold]{self.current_user_profile['user']}[/bold]")
        
        try:
            self.conn = Connection(
                username=self.current_user_profile["user"],
                password=self.current_user_profile["pwd"],
                client_id=self.current_user_profile["clientId"],
                client_secret=self.current_user_profile["clientSecret"],
            )
        except Exception as e:
            print(f"[bold red]Fehler bei der Initialisierung der Verbindung: [/bold red]{e}")
            self.conn = None
            return

        attempts = 0
        while attempts < 3:
            try:
                xauthinfoheaders: XOnceAuthenticationInfo = XOnceAuthenticationInfo(json.loads(self.conn.initSession().headers["x-once-authentication-info"]))
                attempts += 1
                tan = ""
                if xauthinfoheaders.typ == "P_TAN_PUSH":
                    print("Sie verwenden PushTAN. Bitte nutzen Sie nun die comdirect photoTAN app auf Ihrem Smartphone, um die Zugriffsanfrage namens 'Login persönlicher Bereich' zu genehmigen.")
                    print("Bitte fahren Sie erst fort, wenn Sie dies getan haben! Nach dem fünften aufeinanderfolgenden Fehlversuch sperrt Comdirect den Zugang aus Sicherheitsgründen.")
                    if 'console' in globals() and isinstance(console, Console):
                        console.input("Drücken Sie ENTER, nachdem Sie die PushTAN Anfrage auf Ihrem Gerät genehmigt haben.")
                    else:
                        input("Drücken Sie ENTER, nachdem Sie die PushTAN Anfrage auf Ihrem Gerät genehmigt haben.")

                elif xauthinfoheaders.typ == "P_TAN" and hasattr(xauthinfoheaders, "challenge"):
                    from PIL import Image
                    import base64
                    import io
                    img_data = base64.b64decode(xauthinfoheaders.challenge)
                    img = Image.open(io.BytesIO(img_data))
                    try:
                        img.show()
                        print("Bitte führen Sie die PhotoTAN Freigabe wie gewohnt mit ihrem Lesegerät oder App durch.")
                    except Exception:
                        print("Konnte PhotoTAN-Bild nicht automatisch anzeigen. Bitte prüfen Sie die Konsole oder versuchen Sie es manuell.")
                    tan = PromptDeutsch.ask("Geben Sie die TAN ein")
                elif xauthinfoheaders.typ == "M_TAN" and hasattr(xauthinfoheaders, "challenge"):
                    print(f"Bitte prüfen Sie Ihr Smartphone mit der Nummer {xauthinfoheaders.challenge} auf die erhaltene M-TAN")
                    tan = PromptDeutsch.ask("Geben Sie die TAN ein")
                else:
                    print(f"Tut mir Leid, das TAN-Verfahren [bold red]{xauthinfoheaders.typ}[/bold red] wird (noch?) nicht unterstützt.")
                    self.conn = None
                    return
                
                r = self.conn.getSessionTAN(xauthinfoheaders.id, tan)
                rjson = r.json()
                if r.status_code == 422 and rjson.get("code") == "expired":
                    print("[bold yellow]Der Zeitraum für die TAN-Freigabeanforderung ist abgelaufen. Bitte erneut versuchen.[/bold yellow]")
                elif r.status_code == 400 and rjson.get("code") == "TAN_UNGUELTIG":
                    print(f"[bold yellow]{rjson['messages'][0]['message']}[/bold yellow]")
                elif r.status_code != 200:
                    print(f"[bold red]HTTP Status:[/bold red] {r.status_code} | {r.json()}")
                    if attempts >= 3:
                        print("---")
                        print(
                            "[bold red]Es sind drei Freigabeversuche in Folge fehlgeschlagen. Bitte vergewissern Sie sich, dass Sie korrekt arbeiten. "
                            "Sollten Sie unsicher sein, melden Sie sich einmal regulär auf der Comdirect-Webseite an, um eine Sperrung nach fünf aufeinanderfolgenden Fehlversuchen zu vermeiden.[/bold red]"
                        )
                        print("---")
                        self.conn = None
                        return
                else:
                    self.conn.getCDSecondary()
                    print("[green]Login erfolgreich![/green]")
                    return
            
            except Exception as e:
                print(f"[bold red]Fehler bei der Verbindung oder TAN-Challenge:[/bold red] {e}")
                if attempts >= 3:
                    print("[bold red]Maximale Anzahl von Verbindungsversuchen erreicht.[/bold red]")
                    self.conn = None
                    return

        print("[bold red]Verbindung konnte nicht hergestellt werden.[/bold red]")
        self.conn = None


    def __loadDocuments(self):
        if not self.conn:
            print("[bold red]FEHLER:[/bold red] Keine aktive Verbindung. Bitte zuerst anmelden.")
            self.onlineDocumentsDict = {}
            return

        if self.onlineDocumentsDict:
            print("[yellow]Dokumente sind bereits geladen. Lade nicht erneut.[/yellow]")
            return

        print("[green]Lade Dokumentenliste von Comdirect...[/green]")
        try:
            messagesMeta = self.conn.getMessagesList(0, 1)
            total_documents = messagesMeta.matches
            
            self.onlineDocumentsDict = {}
            batchSize = 1000
            x = 0

            # Nur Progress Bar anzeigen, wenn rich geladen wurde
            if 'Progress' in globals() and isinstance(Progress, type) and Progress != object: # Prüfen, ob Progress die rich-Klasse ist
                with Progress(
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    TimeRemainingColumn(),
                    console=console,
                ) as progress:
                    task = progress.add_task(f"[cyan]Lade Dokumente ({total_documents} gesamt)...[/cyan]", total=total_documents)
                    
                    while x < total_documents:
                        current_batch = self.conn.getMessagesList(x, batchSize)
                        for idx, document in enumerate(current_batch.documents):
                            self.onlineDocumentsDict[x + idx] = document
                        x += len(current_batch.documents)
                        progress.update(task, completed=x)
            else: # Fallback, wenn rich Progress Bar nicht verfügbar ist
                print(f"Lade Dokumente ({total_documents} gesamt)...")
                while x < total_documents:
                    current_batch = self.conn.getMessagesList(x, batchSize)
                    for idx, document in enumerate(current_batch.documents):
                        self.onlineDocumentsDict[x + idx] = document
                    x += len(current_batch.documents)
                    print(f"  Geladen: {x}/{total_documents}")


            print(f"[green]Dokumentenliste erfolgreich geladen. {len(self.onlineDocumentsDict)} Dokumente gefunden.[/green]")

        except Exception as e:
            print(f"[bold red]FEHLER beim Laden der Dokumentenliste:[/bold red] {e}")
            self.onlineDocumentsDict = {}


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

        self.__processOnlineDocuments(isCountRun=True)

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
            print("[yellow]Keine Dokumente zum Verarbeiten/Herunterladen geladen.[/yellow]")
            return
        if not self.conn and not isCountRun:
             print("[bold red]FEHLER:[/bold red] Keine aktive Verbindung zum Herunterladen. Bitte zuerst anmelden.")
             return


        def __printStatus(idx: int, document: Document, status: str = ""):
            if isCountRun:
                return
            printLeftString = f"{str(idx):>5} | [cyan]{document.dateCreation.strftime('%Y-%m-%m')}[/cyan] | {sanitize_filename(document.name)}"
            printRightString = status
            filler: str = " "
            spaces = ui_width - len(printLeftString) - len(printRightString)
            # Nutze die globale print-Funktion
            print(printLeftString + (spaces * filler) + printRightString, highlight=False)

        def __isFileEqual(filepath : str, newdata : bytes):
            if not os.path.exists(filepath):
                return False
            try:
                with open(filepath, 'rb') as f:
                    data = f.read()
                    return data == newdata
            except IOError as e:
                print(f"[bold red]FEHLER beim Lesen von Datei für Vergleich {filepath}: {e}[/bold red]")
                return False
        
        progress_description = "Zähle Dokumente..." if isCountRun else "Lade Dokumente herunter..."

        # Nur Progress Bar anzeigen, wenn rich geladen wurde
        if 'Progress' in globals() and isinstance(Progress, type) and Progress != object:
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn( bar_width= 150 ),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                console = console,
                transient=isCountRun
            ) as progress:
                countAll = len(self.onlineDocumentsDict)
                countProcessed = 0
                countSkipped = 0
                countDownloaded = 0

                task = progress.add_task(progress_description, total=countAll)
                
                for idx in self.onlineDocumentsDict:
                    progress.advance(task)
                    document = self.onlineDocumentsDict[idx]
                    # Sicherstellen, dass document.name ein String ist
                    firstFilename = str(document.name).split(" ", 1)[0]
                    subFolder = ""
                    myOutputDir = self.settings.outputDir # Direkt aus settings-Objekt
                    countProcessed += 1

                    # counting (always done)
                    if document.advertisement:
                        self.onlineAdvertismentIndicesList.append(idx)
                    if document.documentMetadata.archived:
                        self.onlineArchivedIndicesList.append(idx)
                    # downloadFilenameList ist bereits eine geparste Python-Liste
                    downloadFilenameList = self.settings.getValueForKey("downloadOnlyFilenamesArray")
                    if firstFilename in downloadFilenameList:
                        self.onlineFileNameMatchingIndicesList.append(idx)
                    if not document.documentMetadata.alreadyRead:
                        self.onlineUnreadIndicesList.append(idx)

                    # Filtering (only skip if not count run)
                    if not isCountRun:
                        downloadSource = self.settings.getValueForKey("downloadSource")
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
                        if not isCountRun:
                            __printStatus(idx, document, f"ÜBERSPRUNGEN - Unbekannter MIME-Typ {document.mimeType}")
                            countSkipped += 1
                        continue

                    filename = filename_base + file_extension

                    if self.settings.getBoolValueForKey("useSubFolders"):
                        myOutputDir = os.path.join(self.settings.outputDir, sanitize_filename(subFolder))
                        if not os.path.exists(myOutputDir):
                            os.makedirs(myOutputDir) # Sicherstellen, dass der Unterordner existiert

                    filepath = os.path.join(myOutputDir, sanitize_filename(filename))

                    if isCountRun:
                        if os.path.exists(filepath):
                            self.onlineAlreadyDownloadedIndicesList.append(idx)
                        else:
                            self.onlineNotYetDownloadedIndicesList.append(idx)
                        continue

                    # ---- Ab hier beginnt der tatsächliche Download-Prozess (nicht im isCountRun-Modus) ----
                    
                    # Dry Run Check
                    if self.settings.getBoolValueForKey("dryRun"):
                        __printStatus(idx, document, "SIMULIERT - Testlauf, kein tatsächlicher Download")
                        countDownloaded += 1
                        continue

                    docDate = document.dateCreation.timestamp()
                    docContent = None
                    final_filepath = filepath
                    appendIfNameExists = self.settings.getBoolValueForKey("appendIfNameExists")
                    
                    # Prüfe, ob die Datei existiert und ob appendIfNameExists aktiv ist
                    if os.path.exists(filepath):
                        if appendIfNameExists:
                            try:
                                if not docContent: # Nur laden, wenn noch nicht geladen
                                    docContent = self.conn.downloadDocument(document)
                            except Exception as e:
                                __printStatus(idx, document, f"FEHLER beim Download für Vergleich: {e}")
                                countSkipped += 1
                                continue

                            if __isFileEqual(filepath, docContent):
                                __printStatus(idx, document, "ÜBERSPRUNGEN - Datei bereits existiert (Inhalt gleich)")
                                countSkipped += 1
                                self.onlineAlreadyDownloadedIndicesList.append(idx)
                                continue

                            # Inhalt ist ungleich, versuche Umbenennung mit Datum
                            path_without_ext, suffix = os.path.splitext(filepath)
                            new_path_base = f"{path_without_ext}_{document.dateCreation.strftime('%Y-%m-%d')}"
                            final_filepath = f"{new_path_base}{suffix}"
                            
                            counter = 1
                            while os.path.exists(final_filepath):
                                if not docContent: # Sicherstellen, dass docContent für den Vergleich vorhanden ist
                                    docContent = self.conn.downloadDocument(document) # Erneuter Versuch, falls vorheriger Download fehlschlug
                                
                                if __isFileEqual(final_filepath, docContent):
                                    __printStatus(idx, document, "ÜBERSPRUNGEN - Datei existiert bereits (Inhalt gleich)")
                                    countSkipped += 1
                                    self.onlineAlreadyDownloadedIndicesList.append(idx)
                                    break # Breche innere Schleife ab
                                
                                counter += 1
                                final_filepath = f"{new_path_base}_{counter}{suffix}"
                            else: # Nur wenn die while-Schleife normal durchläuft (d.h. kein break)
                                 # Nach der Schleife, falls die Datei immer noch existiert und gleich ist (z.B. erster Versuch in der Schleife war gleich)
                                 if os.path.exists(final_filepath) and __isFileEqual(final_filepath, docContent):
                                     __printStatus(idx, document, "ÜBERSPRUNGEN - Datei existiert bereits (Inhalt gleich)")
                                     countSkipped += 1
                                     self.onlineAlreadyDownloadedIndicesList.append(idx)
                                     continue
                            
                            # Wenn wir hier ankommen und die innere Schleife NICHT durch break verlassen wurde,
                            # haben wir einen eindeutigen final_filepath gefunden oder müssen die erste nicht-identische überschreiben
                            # (falls appendIfNameExists=False war, was hier nicht der Fall ist)
                            # Oder die Datei existiert immer noch am final_filepath, ist aber nicht identisch
                            if os.path.exists(final_filepath) and not __isFileEqual(final_filepath, docContent):
                                # Hier könnten wir eine Logik hinzufügen, wenn wir nicht appenden können
                                # und die Datei nicht gleich ist, was dann? Überspringen oder überschreiben?
                                # Aktuell würde es versuchen zu schreiben und einen Fehler werfen, wenn es keine Berechtigung hat.
                                pass # Weiter zum Download-Block

                        else: # appendIfNameExists ist False und Datei existiert bereits
                            __printStatus(idx, document, "ÜBERSPRUNGEN - Datei existiert bereits (Überschreiben deaktiviert)")
                            countSkipped += 1
                            self.onlineAlreadyDownloadedIndicesList.append(idx)
                            continue
                    
                    # Wenn wir hier ankommen, muss die Datei heruntergeladen und gespeichert werden.
                    # docContent könnte bereits vom Vergleich gesetzt sein
                    if not docContent:
                        try:
                            docContent = self.conn.downloadDocument(document)
                        except Exception as e:
                            __printStatus(idx, document, f"FEHLER beim Download: {e}")
                            countSkipped += 1
                            continue
                    
                    try:
                        with open(final_filepath, "wb") as f:
                            f.write(docContent)
                        os.utime(final_filepath, (docDate, docDate))
                        __printStatus(idx, document, f"HERUNTERGELADEN (zu {os.path.basename(final_filepath)})")
                        countDownloaded += 1
                    except Exception as e:
                        __printStatus(idx, document, f"FEHLER beim Speichern der Datei {os.path.basename(final_filepath)}: {e}")
                        countSkipped += 1

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
        else: # Fallback, wenn rich Progress Bar nicht verfügbar ist
            print(f"Verarbeite Dokumente ({len(self.onlineDocumentsDict)} gesamt)...")
            countAll = len(self.onlineDocumentsDict)
            countProcessed = 0
            countSkipped = 0
            countDownloaded = 0

            for idx in self.onlineDocumentsDict:
                document = self.onlineDocumentsDict[idx]
                firstFilename = str(document.name).split(" ", 1)[0]
                subFolder = ""
                myOutputDir = self.settings.outputDir
                countProcessed += 1

                if document.advertisement: self.onlineAdvertismentIndicesList.append(idx)
                if document.documentMetadata.archived: self.onlineArchivedIndicesList.append(idx)
                downloadFilenameList = self.settings.getValueForKey("downloadOnlyFilenamesArray")
                if firstFilename in downloadFilenameList: self.onlineFileNameMatchingIndicesList.append(idx)
                if not document.documentMetadata.alreadyRead: self.onlineUnreadIndicesList.append(idx)

                if not isCountRun:
                    downloadSource = self.settings.getValueForKey("downloadSource")
                    if (downloadSource == DownloadSource.archivedOnly.value and not document.documentMetadata.archived) or \
                       (downloadSource == DownloadSource.notArchivedOnly.value and document.documentMetadata.archived):
                        __printStatus(idx, document, "SKIPPED - nicht in gewählter Download-Quelle")
                        countSkipped += 1
                        continue
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
                    if not isCountRun:
                        __printStatus(idx, document, f"ÜBERSPRUNGEN - Unbekannter MIME-Typ {document.mimeType}")
                        countSkipped += 1
                    continue

                filename = filename_base + file_extension
                if self.settings.getBoolValueForKey("useSubFolders"):
                    myOutputDir = os.path.join(self.settings.outputDir, sanitize_filename(subFolder))
                    if not os.path.exists(myOutputDir):
                        os.makedirs(myOutputDir)
                filepath = os.path.join(myOutputDir, sanitize_filename(filename))

                if isCountRun:
                    if os.path.exists(filepath): self.onlineAlreadyDownloadedIndicesList.append(idx)
                    else: self.onlineNotYetDownloadedIndicesList.append(idx)
                    continue

                if self.settings.getBoolValueForKey("dryRun"):
                    __printStatus(idx, document, "SIMULIERT - Testlauf, kein tatsächlicher Download")
                    countDownloaded += 1
                    continue

                docDate = document.dateCreation.timestamp()
                docContent = None
                final_filepath = filepath
                appendIfNameExists = self.settings.getBoolValueForKey("appendIfNameExists")

                if os.path.exists(filepath):
                    if appendIfNameExists:
                        try:
                            if not docContent: docContent = self.conn.downloadDocument(document)
                        except Exception as e:
                            __printStatus(idx, document, f"FEHLER beim Download für Vergleich: {e}")
                            countSkipped += 1
                            continue
                        if __isFileEqual(filepath, docContent):
                            __printStatus(idx, document, "ÜBERSPRUNGEN - Datei bereits existiert (Inhalt gleich)")
                            countSkipped += 1
                            self.onlineAlreadyDownloadedIndicesList.append(idx)
                            continue
                        path_without_ext, suffix = os.path.splitext(filepath)
                        new_path_base = f"{path_without_ext}_{document.dateCreation.strftime('%Y-%m-%d')}"
                        final_filepath = f"{new_path_base}{suffix}"
                        counter = 1
                        while os.path.exists(final_filepath):
                            if not docContent: docContent = self.conn.downloadDocument(document)
                            if __isFileEqual(final_filepath, docContent):
                                __printStatus(idx, document, "ÜBERSPRUNGEN - Datei existiert bereits (Inhalt gleich)")
                                countSkipped += 1
                                self.onlineAlreadyDownloadedIndicesList.append(idx)
                                break
                            counter += 1
                            final_filepath = f"{new_path_base}_{counter}{suffix}"
                        else:
                             if os.path.exists(final_filepath) and __isFileEqual(final_filepath, docContent):
                                 __printStatus(idx, document, "ÜBERSPRUNGEN - Datei existiert bereits (Inhalt gleich)")
                                 countSkipped += 1
                                 self.onlineAlreadyDownloadedIndicesList.append(idx)
                                 continue
                    else:
                        __printStatus(idx, document, "ÜBERSPRUNGEN - Datei existiert bereits (Überschreiben deaktiviert)")
                        countSkipped += 1
                        self.onlineAlreadyDownloadedIndicesList.append(idx)
                        continue
                
                if not docContent:
                    try: docContent = self.conn.downloadDocument(document)
                    except Exception as e:
                        __printStatus(idx, document, f"FEHLER beim Download: {e}")
                        countSkipped += 1
                        continue
                
                try:
                    with open(final_filepath, "wb") as f: f.write(docContent)
                    os.utime(final_filepath, (docDate, docDate))
                    __printStatus(idx, document, f"HERUNTERGELADEN (zu {os.path.basename(final_filepath)})")
                    countDownloaded += 1
                except Exception as e:
                    __printStatus(idx, document, f"FEHLER beim Speichern der Datei {os.path.basename(final_filepath)}: {e}")
                    countSkipped += 1

            if not isCountRun:
                print("\n[bold]Zusammenfassung des Downloads:[/bold]")
                print(f"Dokumente gesamt: {countAll}")
                print(f"Davon verarbeitet: {countProcessed}")
                print(f"Davon heruntergeladen: {countDownloaded}")
                print(f"Davon übersprungen: {countSkipped}")


dirname = os.path.dirname(__file__)
main = Main(dirname)
