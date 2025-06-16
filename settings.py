import os
import configparser
import getpass
import json

class Settings:
    def __init__(self, dirname: str):
        self.dirname = dirname
        self.settingsFileName = "settings.ini"
        self.__config = configparser.ConfigParser()
        self.user_profiles: dict[str, dict[str, str]] = {}
        self._download_filenames_array_parsed = [] # Neues Attribut zum Speichern des geparsten Arrays

        self.readSettings()

    def readSettings(self):
        absSettingsDirName = os.path.join(self.dirname, self.settingsFileName)
        if not os.path.isfile(absSettingsDirName):
            raise FileNotFoundError("Die Datei settings.ini wurde nicht gefunden. Bitte erstellen Sie sie basierend auf dem Beispiel.")

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
                        value = self.__config[section].get(key)
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
                    print(f"ERROR beim Laden des Benutzerprofils '{profile_name}': {error}")
                    exit(-1)

        # Überprüfe und setze die globalen Einstellungen (die im DEFAULT-Abschnitt stehen)
        if "DEFAULT" not in self.__config:
            self.__config["DEFAULT"] = {}

        try:
            # Output Directory
            outputDir = self.__config["DEFAULT"].get("outputDir")
            if not outputDir:
                outputDir = self.__getInputForString("Bitte geben Sie das Zielverzeichnis an, in welches die Dokumente heruntergeladen werden sollen: ")
                self.__config["DEFAULT"]["outputDir"] = outputDir
            self.outputDir = self.__createIfNotExistDir(outputDir)

            # Dry Run
            dryRun_val = self.__config["DEFAULT"].get("dryRun")
            if not dryRun_val:
                dryRun_val = self.__getInputForString("Soll dies ein Testlauf sein (keine Dateien werden heruntergeladen)? [ja/nein]: ")
            self.__config["DEFAULT"]["dryRun"] = str(self.__isTruthy(dryRun_val))

            # Append If Name Exists
            appendIfNameExists_val = self.__config["DEFAULT"].get("appendIfNameExists")
            if not appendIfNameExists_val:
                 appendIfNameExists_val = self.__getInputForString("Wenn gleiche Dateinamen existieren, sollen Datum/Zähler angehängt werden? [ja/nein]: ")
            self.__config["DEFAULT"]["appendIfNameExists"] = str(self.__isTruthy(appendIfNameExists_val))

            # Use SubFolders
            useSubFolders_val = self.__config["DEFAULT"].get("useSubFolders")
            if not useSubFolders_val:
                useSubFolders_val = self.__getInputForString("Dokumente in Unterordner sortieren (pdf/html)? [ja/nein]: ")
            self.__config["DEFAULT"]["useSubFolders"] = str(self.__isTruthy(useSubFolders_val))

            # Download Only Filenames
            downloadOnlyFilenames_val = self.__config["DEFAULT"].get("downloadOnlyFilenames")
            if not downloadOnlyFilenames_val:
                downloadOnlyFilenames_val = self.__getInputForString("Nur spezifische Dateinamen herunterladen? [ja/nein]: ")
            self.__config["DEFAULT"]["downloadOnlyFilenames"] = str(self.__isTruthy(downloadOnlyFilenames_val))

            # Download Only Filenames Array
            download_list_str = self.__config["DEFAULT"].get("downloadOnlyFilenamesArray", "[]")
            try:
                # Versuche es als JSON zu parsen (z.B. ["Item1", "Item2"])
                self._download_filenames_array_parsed = json.loads(download_list_str.replace("'", '"')) if download_list_str else []
            except json.JSONDecodeError:
                # Fallback, wenn es kein gültiges JSON ist (z.B. altes Format {"Item1", "Item2"})
                # Hier parsen wir es als Set. Wichtig: convertiere es zurück in eine Liste für Konsistenz
                self._download_filenames_array_parsed = list({item.strip() for item in download_list_str.strip('{} ').split(',') if item.strip()})
            
            # WICHTIG: Wenn es interaktiv abgefragt wurde (also download_list_str leer war)
            # oder wenn das Format sich geändert hat, speichern wir es als gültigen JSON-String zurück
            # in der __config, um den "option values must be strings"-Fehler zu vermeiden.
            # Wenn es bereits korrekt als JSON-String vorhanden war, ändert sich nichts.
            # Die Einstellung muss für die Anzeige und für getValueForKey immer noch richtig geparst sein.
            if not download_list_str or not isinstance(self._download_filenames_array_parsed, list): # Wenn es leer war oder nicht als Liste geparst wurde
                self.__config["DEFAULT"]["downloadOnlyFilenamesArray"] = json.dumps(self._download_filenames_array_parsed)


            # Download Source
            downloadSource_val = self.__config["DEFAULT"].get("downloadSource")
            if not downloadSource_val:
                downloadSource_val = self.__getInputForString("Download-Quelle (archivedOnly/notArchivedOnly/all): ")
            self.__config["DEFAULT"]["downloadSource"] = downloadSource_val


        except Exception as error:
            # Jetzt, da alle Werte in self.__config als String gespeichert werden sollten,
            # tritt dieser Fehler hier hoffentlich nicht mehr auf.
            print(f"ERROR beim Laden der globalen Einstellungen: {error}")
            exit(-1)

    def getSettings(self):
        return self.__config["DEFAULT"]

    def getProfileNames(self) -> list[str]:
        return list(self.user_profiles.keys())

    def getProfileSettings(self, profile_name: str) -> dict[str, str]:
        if profile_name in self.user_profiles:
            return self.user_profiles[profile_name]
        raise ValueError(f"Benutzerprofil '{profile_name}' nicht gefunden.")

    def showSettings(self):
        print("\n[b]Globale Einstellungen[/b]")
        # Erstelle eine temporäre Sektion, um nur die DEFAULT-Werte anzuzeigen
        temp_config = configparser.ConfigParser()
        # Kopiere nur die relevanten Werte in ein Dict, um sie zu übergeben.
        # Vermeide, das configparser-Objekt direkt zu übergeben, da es die Anzeige von Listen verkompliziert.
        default_settings_for_display = {}
        for key, value in self.__config["DEFAULT"].items():
            if key == "downloadonlyfilenamesarray": # configparser keys are lowercase
                default_settings_for_display[key] = str(self._download_filenames_array_parsed)
            else:
                default_settings_for_display[key] = value
        
        for key, value in default_settings_for_display.items():
            output = f"{key}: {value}"
            self.__printMessage(output)

        print("\n[b]Benutzerprofile[/b]")
        if not self.user_profiles:
            self.__printMessage("Keine Benutzerprofile in settings.ini gefunden. Bitte legen Sie welche an (z.B. [USER_NAME]).")
        for profile_name, settings in self.user_profiles.items():
            self.__printMessage(f"  [cyan]{profile_name}[/cyan]:")
            for key, value in settings.items():
                if key in ["pwd", "clientSecret"]:
                    masked_value = "*" * len(value)
                    self.__printMessage(f"    {key}: {masked_value}")
                else:
                    self.__printMessage(f"    {key}: {value}")

    def getValueForKey(self, settingName: str, section: str = "DEFAULT"):
        if section == "DEFAULT" and settingName == "downloadOnlyFilenamesArray":
            return self._download_filenames_array_parsed # Gibt das geparste Python-Objekt zurück
        
        # configparser Keys sind immer lowercase
        settingName_lower = settingName.lower()

        if self.__config.has_option(section, settingName_lower) and self.__config[section][settingName_lower]:
            return self.__config[section][settingName_lower]
        else:
            raise NameError(f"Einstellung '{settingName}' in Sektion '{section}' nicht gesetzt oder leer.")

    def getBoolValueForKey(self, settingName: str, section: str = "DEFAULT"):
        settingName_lower = settingName.lower()
        if self.__config.has_option(section, settingName_lower) and self.__config[section][settingName_lower]:
            return self.__isTruthy(self.__config[section][settingName_lower])
        else:
            raise NameError(f"Einstellung '{settingName}' in Sektion '{section}' nicht gesetzt oder leer.")

    def __isSettingNameFilledInConfig(self, settingName: str, section: str = "DEFAULT"):
        # Diese Hilfsfunktion ist jetzt weniger relevant, da wir direkt get() verwenden
        # und die Werte immer als Strings in __config gespeichert werden.
        # Der ConfigParser macht Keys automatisch lowercase
        return self.__config.has_option(section, settingName.lower()) and bool(self.__config[section].get(settingName.lower()))

    def __getInputForString(self, printString: str):
        inp = input(printString)
        return inp

    def __printMessage(self, message: str):
        if hasattr(self, '_console') and self._console:
            self._console.print(message)
        else:
            print(message)

    def __isTruthy(self, inputString: str):
        return inputString.lower() in ["ja", "j", "true", "yes", "y", "1"]

    def __createIfNotExistDir(self, dir: str):
        if not os.path.isabs(dir):
            dir = os.path.join(self.dirname, dir)

        if not os.path.exists(dir):
            shouldCreateDir = self.__getInputForString("Zielverzeichnis nicht gefunden. Soll es erstellt werden? (ja/nein): ")
            if self.__isTruthy(shouldCreateDir):
                os.makedirs(dir)
            else:
                self.__printMessage("Zielverzeichnis wurde nicht erstellt. Bis zum nächsten Mal!")
                exit(0)
        return dir