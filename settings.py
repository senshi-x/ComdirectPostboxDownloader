import os
import configparser
import getpass
import json # Importieren, um downloadOnlyFilenamesArray korrekt zu parsen

class Settings:
    def __init__(self, dirname: str):
        self.dirname = dirname
        self.settingsFileName = "settings.ini"
        self.__config = configparser.ConfigParser()
        self.user_profiles: dict[str, dict[str, str]] = {}
        self.readSettings()

    def readSettings(self):
        # Lese die allgemeine Konfiguration
        absSettingsDirName = os.path.join(self.dirname, self.settingsFileName)
        if not os.path.isfile(absSettingsDirName):
            raise FileNotFoundError("Die Datei settings.ini wurde nicht gefunden. Bitte erstellen Sie sie basierend auf dem Beispiel.")

        self.__config.read(absSettingsDirName)

        # Lade alle Benutzerprofile
        self.user_profiles = {}
        for section in self.__config.sections():
            if section.startswith("USER_"):
                profile_name = section[5:] # Entferne "USER_" Präfix
                self.user_profiles[profile_name] = {}
                try:
                    # Sammle Benutzerdaten oder frage danach
                    for key in ["user", "pwd", "clientId", "clientSecret"]:
                        if not self.__config.has_option(section, key) or not self.__config[section][key]:
                            # Spezifische Abfragen für sensible Daten
                            if key == "pwd":
                                self.user_profiles[profile_name][key] = getpass.getpass(prompt=f"Bitte geben Sie das Passwort für Benutzer '{profile_name}' ein: ", stream=None)
                            elif key == "clientSecret":
                                self.user_profiles[profile_name][key] = getpass.getpass(prompt=f"Bitte geben Sie das oAuth clientSecret für Benutzer '{profile_name}' ein: ", stream=None)
                            else:
                                self.user_profiles[profile_name][key] = self.__getInputForString(f"Bitte geben Sie die {key} für Benutzer '{profile_name}' ein: ")
                        else:
                            self.user_profiles[profile_name][key] = self.__config[section][key]

                except Exception as error:
                    print(f"ERROR beim Laden des Benutzerprofils '{profile_name}': {error}")
                    exit(-1)

        # Überprüfe und setze die globalen Einstellungen (die im DEFAULT-Abschnitt stehen)
        try:
            # Output Directory
            outputDir = self.__config["DEFAULT"].get("outputDir")
            if not outputDir:
                outputDir = self.__getInputForString("Bitte geben Sie das Zielverzeichnis an, in welches die Dokumente heruntergeladen werden sollen: ")
                self.__config["DEFAULT"]["outputDir"] = outputDir
            self.outputDir = self.__createIfNotExistDir(outputDir)

            # Dry Run
            if not self.__config.has_option("DEFAULT", "dryRun") or not self.__config["DEFAULT"]["dryRun"]:
                self.__config["DEFAULT"]["dryRun"] = str(self.__isTruthy(self.__getInputForString("Soll dies ein Testlauf sein (keine Dateien werden heruntergeladen)? [ja/nein]: ")))

            # Append If Name Exists
            if not self.__config.has_option("DEFAULT", "appendIfNameExists") or not self.__config["DEFAULT"]["appendIfNameExists"]:
                 self.__config["DEFAULT"]["appendIfNameExists"] = str(self.__isTruthy(self.__getInputForString("Wenn gleiche Dateinamen existieren, sollen Datum/Zähler angehängt werden? [ja/nein]: ")))

            # Use SubFolders
            if not self.__config.has_option("DEFAULT", "useSubFolders") or not self.__config["DEFAULT"]["useSubFolders"]:
                self.__config["DEFAULT"]["useSubFolders"] = str(self.__isTruthy(self.__getInputForString("Dokumente in Unterordner sortieren (pdf/html)? [ja/nein]: ")))

            # Download Only Filenames
            if not self.__config.has_option("DEFAULT", "downloadOnlyFilenames") or not self.__config["DEFAULT"]["downloadOnlyFilenames"]:
                self.__config["DEFAULT"]["downloadOnlyFilenames"] = str(self.__isTruthy(self.__getInputForString("Nur spezifische Dateinamen herunterladen? [ja/nein]: ")))

            # Download Only Filenames Array - parsing as JSON list
            download_list_str = self.__config["DEFAULT"].get("downloadOnlyFilenamesArray", "[]")
            try:
                # configparser liest es als String, muss manuell in Python-Liste geparst werden
                # Sicherstellen, dass es als gültiges JSON interpretiert wird (z.B. ["Item1", "Item2"])
                # Derzeit ist es im Beispiel in geschweiften Klammern {} was es zu einem Set macht.
                # Für configparser und JSON müsste es eine Liste [] sein.
                # Passe das im Beispiel an, oder parse es hier als Set, wenn es so bleiben soll.
                # Aktuell ist es als Set im Beispiel, also parsen wir es als Set.
                self.__config["DEFAULT"]["downloadOnlyFilenamesArray"] = json.loads(download_list_str.replace("'", '"')) if download_list_str else []
            except json.JSONDecodeError:
                # Fallback, wenn es kein gültiges JSON ist (z.B. altes Format)
                self.__config["DEFAULT"]["downloadOnlyFilenamesArray"] = [item.strip() for item in download_list_str.strip('{} ').split(',') if item.strip()]
            
            # Download Source
            if not self.__config.has_option("DEFAULT", "downloadSource") or not self.__config["DEFAULT"]["downloadSource"]:
                self.__config["DEFAULT"]["downloadSource"] = self.__getInputForString("Download-Quelle (archivedOnly/notArchivedOnly/all): ")


        except Exception as error:
            print(f"ERROR beim Laden der globalen Einstellungen: {error}")
            exit(-1)

    def getSettings(self):
        # Gibt die DEFAULT-Einstellungen zurück, wie zuvor.
        # Für Benutzerspezifische Einstellungen muss getProfileSettings verwendet werden.
        return self.__config["DEFAULT"]

    def getProfileNames(self) -> list[str]:
        return list(self.user_profiles.keys())

    def getProfileSettings(self, profile_name: str) -> dict[str, str]:
        if profile_name in self.user_profiles:
            return self.user_profiles[profile_name]
        raise ValueError(f"Benutzerprofil '{profile_name}' nicht gefunden.")

    def showSettings(self):
        print("\n[b]Globale Einstellungen[/b]")
        table = configparser.ConfigParser()
        table["DEFAULT"] = self.__config["DEFAULT"] # Kopiere nur den DEFAULT-Abschnitt für die Anzeige
        for key in table["DEFAULT"]:
            output = key + ": "
            # downloadOnlyFilenamesArray muss speziell behandelt werden, da es eine Liste/Set ist
            if key == "downloadOnlyFilenamesArray":
                output += str(table["DEFAULT"][key])
            else:
                output += table["DEFAULT"][key]
            self.__printMessage(output)

        print("\n[b]Benutzerprofile[/b]")
        if not self.user_profiles:
            self.__printMessage("Keine Benutzerprofile in settings.ini gefunden. Bitte legen Sie welche an (z.B. [USER_NAME]).")
        for profile_name, settings in self.user_profiles.items():
            self.__printMessage(f"  [cyan]{profile_name}[/cyan]:")
            for key, value in settings.items():
                if key in ["pwd", "clientSecret"]: # Sensible Daten maskieren
                    masked_value = "*" * len(value)
                    self.__printMessage(f"    {key}: {masked_value}")
                else:
                    self.__printMessage(f"    {key}: {value}")

    def getValueForKey(self, settingName: str, section: str = "DEFAULT"):
        # Diese Methode bleibt, um weiterhin auf DEFAULT-Einstellungen zugreifen zu können
        if self.__config.has_option(section, settingName) and self.__config[section][settingName]:
            # Spezielle Behandlung für downloadOnlyFilenamesArray
            if settingName == "downloadOnlyFilenamesArray":
                # Da es in readSettings bereits als Liste/Set geparst wurde, direkt zurückgeben
                return self.__config[section][settingName]
            return self.__config[section][settingName]
        else:
            raise NameError(f"Einstellung '{settingName}' in Sektion '{section}' nicht gesetzt oder leer.")

    def getBoolValueForKey(self, settingName: str, section: str = "DEFAULT"):
        # Diese Methode bleibt, um weiterhin auf DEFAULT-Einstellungen zugreifen zu können
        if self.__config.has_option(section, settingName) and self.__config[section][settingName]:
            return self.__isTruthy(self.__config[section][settingName])
        else:
            raise NameError(f"Einstellung '{settingName}' in Sektion '{section}' nicht gesetzt oder leer.")


    def __isSettingNameFilledInConfig(self, settingName: str, section: str = "DEFAULT"):
        # Diese Hilfsfunktion ist für die interne Verwendung, um zu prüfen, ob eine Option existiert und einen Wert hat.
        # Im Kontext der user_profiles-Verarbeitung wird direkt auf das Dict zugegriffen.
        return self.__config.has_option(section, settingName) and bool(self.__config[section][settingName])


    def __getInputForString(self, printString: str):
        inp = input(printString)
        return inp

    def __printMessage(self, message: str):
        # Verwende rich.console.print, falls vorhanden, sonst Standard print
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