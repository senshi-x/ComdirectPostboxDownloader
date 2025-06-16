import os
import configparser
import getpass
import json
from typing import Any # Import hinzugefügt

class Settings:
    def __init__(self, dirname: str):
        self.dirname = dirname
        self.settingsFileName = "settings.ini"
        self.__config = configparser.ConfigParser()
        self.user_profiles: dict[str, dict[str, str]] = {}
        self._download_filenames_array_parsed: list[str] = [] # Typ-Hinting verbessert
        self._console: Any = None # Für die Kommunikation mit dem Rich-Console-Objekt aus main.py

        self.readSettings()

    def readSettings(self):
        absSettingsDirName = os.path.join(self.dirname, self.settingsFileName)
        if not os.path.isfile(absSettingsDirName):
            # Nutze __printMessage, um die Fehlerbehandlung über die Rich-Console zu leiten
            self.__printMessage("[bold red]FEHLER:[/bold red] Die Datei settings.ini wurde nicht gefunden. Bitte erstellen Sie sie basierend auf dem Beispiel.")
            # Beende das Programm sauber, da keine Einstellungen geladen werden können
            exit(1) # exit(1) signalisiert einen Fehler

        self.__config.read(absSettingsDirName)

        # Lade alle Benutzerprofile
        self.user_profiles = {}
        for section in self.__config.sections():
            if section.startswith("USER_"):
                profile_name = section[5:]
                self.user_profiles[profile_name] = {}
                try:
                    for key in ["user", "pwd", "clientId", "clientSecret"]:
                        # Lese aus der config, falls vorhanden, sonst interaktive Abfrage
                        # configparser macht Schlüssel automatisch klein
                        value = self.__config[section].get(key.lower())
                        if not value:
                            if key == "pwd":
                                self.user_profiles[profile_name][key] = getpass.getpass(prompt=f"Bitte geben Sie das Passwort für Benutzer '{profile_name}' ein: ", stream=None)
                            elif key == "clientSecret":
                                self.user_profiles[profile_name][key] = getpass.getpass(prompt=f"Bitte geben Sie das oAuth clientSecret für Benutzer '{profile_name}' ein: ", stream=None)
                            else:
                                self.user_profiles[profile_name][key] = self.__getInputForString(f"Bitte geben Sie die {key} für Benutzer '{profile_name}' ein: ")
                        else:
                            self.user_profiles[profile_name][key] = value
                except Exception as error:
                    self.__printMessage(f"[bold red]ERROR beim Laden des Benutzerprofils '{profile_name}':[/bold red] {error}")
                    exit(-1)

        # Überprüfe und setze die globalen Einstellungen (die im DEFAULT-Abschnitt stehen)
        if "DEFAULT" not in self.__config:
            self.__config["DEFAULT"] = {}

        try:
            # Output Directory
            outputDir = self.__config["DEFAULT"].get("outputdir")
            if not outputDir:
                outputDir = self.__getInputForString("Bitte geben Sie das Zielverzeichnis an, in welches die Dokumente heruntergeladen werden sollen: ")
                self.__config["DEFAULT"]["outputdir"] = outputDir
            self.outputDir = self.__createIfNotExistDir(outputDir)

            # Dry Run
            dryRun_val = self.__config["DEFAULT"].get("dryrun")
            if not dryRun_val:
                dryRun_val = self.__getInputForString("Soll dies ein Testlauf sein (keine Dateien werden heruntergeladen)? [ja/nein]: ")
            self.__config["DEFAULT"]["dryrun"] = str(self.__isTruthy(dryRun_val))

            # Append If Name Exists
            appendIfNameExists_val = self.__config["DEFAULT"].get("appendifnameexists")
            if not appendIfNameExists_val:
                 appendIfNameExists_val = self.__getInputForString("Wenn gleiche Dateinamen existieren, sollen Datum/Zähler angehängt werden? [ja/nein]: ")
            self.__config["DEFAULT"]["appendifnameexists"] = str(self.__isTruthy(appendIfNameExists_val))

            # Use SubFolders
            useSubFolders_val = self.__config["DEFAULT"].get("usesubfolders")
            if not useSubFolders_val:
                useSubFolders_val = self.__getInputForString("Dokumente in Unterordner sortieren (pdf/html)? [ja/nein]: ")
            self.__config["DEFAULT"]["usesubfolders"] = str(self.__isTruthy(useSubFolders_val))

            # Download Only Filenames
            downloadOnlyFilenames_val = self.__config["DEFAULT"].get("downloadonlyfilenames")
            if not downloadOnlyFilenames_val:
                downloadOnlyFilenames_val = self.__getInputForString("Nur spezifische Dateinamen herunterladen? [ja/nein]: ")
            self.__config["DEFAULT"]["downloadonlyfilenames"] = str(self.__isTruthy(downloadOnlyFilenames_val))

            # Download Only Filenames Array
            # Configparser liest Schlüssel immer als lowercase
            download_list_str = self.__config["DEFAULT"].get("downloadonlyfilenamesarray", "[]")
            try:
                # Versuche es als JSON-Liste zu parsen (z.B. ["Item1", "Item2"])
                parsed_list = json.loads(download_list_str.replace("'", '"'))
                if not isinstance(parsed_list, list): # Sicherstellen, dass es wirklich eine Liste ist
                    raise ValueError("Parsed JSON is not a list")
                self._download_filenames_array_parsed = parsed_list
            except (json.JSONDecodeError, ValueError):
                # Fallback, wenn es kein gültiges JSON oder keine Liste ist (z.B. altes Format {"Item1", "Item2"})
                # Konvertiere ein Set zur Liste für Konsistenz
                self._download_filenames_array_parsed = sorted(list({item.strip() for item in download_list_str.strip('{} ').split(',') if item.strip()}))
            
            # WICHTIG: Speichere den geparsten Wert immer als JSON-String zurück im configparser,
            # um den "option values must be strings" Fehler zu vermeiden, falls er im falschen Format gelesen wurde.
            self.__config["DEFAULT"]["downloadonlyfilenamesarray"] = json.dumps(self._download_filenames_array_parsed)


            # Download Source
            downloadSource_val = self.__config["DEFAULT"].get("downloadsource")
            if not downloadSource_val:
                downloadSource_val = self.__getInputForString("Download-Quelle (archivedOnly/notArchivedOnly/all): ")
            self.__config["DEFAULT"]["downloadsource"] = downloadSource_val


        except Exception as error:
            self.__printMessage(f"[bold red]ERROR beim Laden der globalen Einstellungen:[/bold red] {error}")
            exit(-1)

    def getSettings(self):
        # Diese Methode gibt das config-Objekt zurück.
        # Für spezielle Werte wie downloadOnlyFilenamesArray sollte getValueForKey verwendet werden.
        return self.__config["DEFAULT"]

    def getProfileNames(self) -> list[str]:
        return list(self.user_profiles.keys())

    def getProfileSettings(self, profile_name: str) -> dict[str, str]:
        if profile_name in self.user_profiles:
            return self.user_profiles[profile_name]
        raise ValueError(f"Benutzerprofil '{profile_name}' nicht gefunden.")

    def showSettings(self):
        self.__printMessage("\n[b]Globale Einstellungen[/b]")
        
        # Zeige alle DEFAULT-Einstellungen, parsen, wo nötig
        for key, value in self.__config["DEFAULT"].items():
            display_value = value
            if key == "downloadonlyfilenamesarray":
                display_value = str(self._download_filenames_array_parsed)
            elif self.__isTruthy(value): # Bei booleschen Werten
                display_value = "Ja"
            elif not self.__isTruthy(value) and value.lower() in ["false", "nein", "n", "0"]:
                display_value = "Nein"

            self.__printMessage(f"{key}: {display_value}")

        self.__printMessage("\n[b]Benutzerprofile[/b]")
        if not self.user_profiles:
            self.__printMessage("Keine Benutzerprofile in settings.ini gefunden. Bitte legen Sie welche an (z.B. [USER_NAME]).")
        for profile_name, settings in self.user_profiles.items():
            self.__printMessage(f"  [cyan]{profile_name}[/cyan]:")
            for key, value in settings.items():
                if key in ["pwd", "clientSecret"]:
                    masked_value = "*" * len(value) if value else "[dim]Nicht gesetzt[/dim]"
                    self.__printMessage(f"    {key}: {masked_value}")
                else:
                    display_value = value if value else "[dim]Nicht gesetzt[/dim]"
                    self.__printMessage(f"    {key}: {display_value}")

    def getValueForKey(self, settingName: str, section: str = "DEFAULT"):
        # configparser Keys sind immer lowercase
        settingName_lower = settingName.lower()

        if section == "DEFAULT" and settingName_lower == "downloadonlyfilenamesarray":
            return self._download_filenames_array_parsed # Gibt das geparste Python-Objekt zurück
        
        if self.__config.has_option(section, settingName_lower):
            # Gib den Wert direkt zurück, er ist ja ein String im configparser
            return self.__config[section].get(settingName_lower)
        else:
            raise NameError(f"Einstellung '{settingName}' in Sektion '{section}' nicht gefunden oder leer.")

    def getBoolValueForKey(self, settingName: str, section: str = "DEFAULT"):
        settingName_lower = settingName.lower()
        if self.__config.has_option(section, settingName_lower):
            value = self.__config[section].get(settingName_lower)
            return self.__isTruthy(value) if value is not None else False # False, wenn nicht gesetzt
        else:
            raise NameError(f"Einstellung '{settingName}' in Sektion '{section}' nicht gefunden.")

    def __getInputForString(self, printString: str):
        # Nutze self._console.input, wenn verfügbar, sonst Standard-input
        if self._console:
            return self._console.input(printString)
        return input(printString)

    def __printMessage(self, message: str, highlight: bool = False):
        # Nutze self._console.print, wenn verfügbar, sonst Standard-print
        if self._console:
            self._console.print(message, highlight=highlight)
        else:
            print(message)

    def __isTruthy(self, inputString: str):
        if not isinstance(inputString, str):
            return False # Nur Strings können wahrheitsgemäß interpretiert werden
        return inputString.lower() in ["ja", "j", "true", "yes", "y", "1"]

    def __createIfNotExistDir(self, dir: str):
        if not os.path.isabs(dir):
            dir = os.path.join(self.dirname, dir)

        if not os.path.exists(dir):
            shouldCreateDir = self.__getInputForString("Zielverzeichnis nicht gefunden. Soll es erstellt werden? (ja/nein): ")
            if self.__isTruthy(shouldCreateDir):
                os.makedirs(dir)
                self.__printMessage(f"[green]Verzeichnis '{dir}' erstellt.[/green]")
            else:
                self.__printMessage("[bold yellow]Zielverzeichnis wurde nicht erstellt. Bis zum nächsten Mal![/bold yellow]")
                exit(0)
        return dir
