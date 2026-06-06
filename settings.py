import os
import configparser
import getpass
import re

from secrets_store import SecretStore


class Settings:
    def __init__(self, dirname: str):
        self.dirname = dirname
        self.settingsFileName = "settings.ini"
        self.readSettings()

    def readSettings(self):
        # If you want comfort, put your data into the settings.ini
        # If you understandably don't want to leave all credentials in a clear textfile,
        # just leave them out and you will be prompted for them.

        absSettingsDirName = os.path.join(self.dirname, self.settingsFileName)
        if os.path.isfile(absSettingsDirName):
            self.__config = configparser.ConfigParser()
            self.__config.read(absSettingsDirName)
            try:
                self.__setDefaultIfMissing("secretBackend", "auto")
                self.__setDefaultIfMissing("secretNamespace", "Banking/comdirect")
                self.__setDefaultIfMissing("useThematicSubFolders", "False")
                self.__setDefaultIfMissing("incrementalSync", "True")

                if not self.__isSettingNameFilledInConfig("user"):
                    self.__config["DEFAULT"]["user"] = self.__getInputForString("Bitte geben Sie Ihre Kundennummer ein: ")

                if not self.__isSettingNameFilledInConfig("pwd"):
                    self.__config["DEFAULT"]["pwd"] = self.__getSecretOrPrompt("pwd", "Bitte geben Sie das dazugehörige Passwort ein: ")

                if not self.__isSettingNameFilledInConfig("clientId"):
                    self.__config["DEFAULT"]["clientId"] = self.__getInputForString("Bitte geben Sie die oAuth clientId für den API-Zugang ein: ")

                if not self.__isSettingNameFilledInConfig("clientSecret"):
                    self.__config["DEFAULT"]["clientSecret"] = self.__getSecretOrPrompt("clientSecret", "Bitte geben Sie Ihr oAuth clientSecret für den API Zugang ein: ")

                self.__repairClientSecretIfItContainsPasswordPrefix()

                if not self.__isSettingNameFilledInConfig("outputDir"):
                    self.__config["DEFAULT"]["outputDir"] = self.__getInputForString("Bitte geben Sie das Zielverzeichnis an, in welches die Dokumente heruntergeladen werden sollen: ")

                if not self.__config.has_option("", "dryRun"):
                    self.__config["DEFAULT"]["dryRun"] = str(self.__isTruthy(self.__getInputForString("Soll dies ein Testlauf sein (keine Dateien werden heruntergeladen)? [ja/nein]: ")))
            except Exception as error:
                print("ERROR", error)
                exit(-1)

            # check out dir right away..
            self.outputDir = self.__createIfNotExistDir(self.__config["DEFAULT"]["outputDir"])
        else:
            raise NameError("please provide settings.ini to start program.")

    def getSettings(self):
        return self.__config["DEFAULT"]

    def showSettings(self):
        for key in self.__config["DEFAULT"]:
            output = key + ": "
            if key in ["pwd", "clientsecret"]:
                pwOut = ""
                for _ in range(len(self.__config["DEFAULT"][key])):
                    pwOut += "*"
                output += pwOut
            else:
                output += self.__config["DEFAULT"][key]
            print(output)

    def getValueForKey(self, settingName: str, section: str = "DEFAULT"):
        if self.__isSettingNameFilledInConfig(settingName, section):
            return self.__config[section][settingName]
        else:
            raise NameError("SettingName not set")

    def getBoolValueForKey(self, settingName: str, section: str = "DEFAULT"):
        if self.__isSettingNameFilledInConfig(settingName, section):
            return self.__isTruthy(self.__config[section][settingName])
        else:
            raise NameError("SettingName not set")

    def getDownloadOnlyFilenames(self) -> set[str]:
        if not self.__isSettingNameFilledInConfig("downloadOnlyFilenamesArray"):
            return set()
        return self.__parseStringList(self.__config["DEFAULT"]["downloadOnlyFilenamesArray"])

    def getOutputDir(self) -> str:
        return self.outputDir

    def __isSettingNameFilledInConfig(self, settingName: str, section: str = "DEFAULT"):
        if settingName not in self.__config[section]:
            return False
        elif not self.__config.has_option("", settingName):
            return False
        elif not self.__config[section][settingName]:
            return False
        return True

    def __getInputForString(self, printString: str):
        # print("----------------------------------------------------------------")
        inp = input(printString)
        # print("----------------------------------------------------------------")
        return inp

    def __printMessage(self, message: str):
        print(message)

    def __setDefaultIfMissing(self, settingName: str, value: str):
        if not self.__isSettingNameFilledInConfig(settingName):
            self.__config["DEFAULT"][settingName] = value

    def __getSecretOrPrompt(self, secretName: str, prompt: str):
        secretStore = SecretStore(
            self.dirname,
            self.__config["DEFAULT"]["secretBackend"],
            self.__config["DEFAULT"]["secretNamespace"],
        )
        secret = None
        backendError = False
        try:
            secret = secretStore.get_secret(secretName)
        except RuntimeError as error:
            backendError = True
            print(f"WARNUNG: {error}")
            print(f"Secret '{secretName}' wird interaktiv abgefragt.")

        if secret:
            return secret

        if not backendError:
            print(f"Secret '{secretName}' im Backend '{secretStore.backend}' nicht gefunden, frage interaktiv ab.")
        secret_value = getpass.getpass(prompt=prompt, stream=None).strip()
        if secret_value:
            try:
                secretStore.set_secret(secretName, secret_value)
            except RuntimeError as error:
                print(f"WARNUNG: {error}")
                print(f"Secret '{secretName}' konnte nicht gespeichert werden, wird aber im aktuellen Programmlauf verwendet.")
        return secret_value

    def __repairClientSecretIfItContainsPasswordPrefix(self):
        # Safety net for a previously observed keyring migration issue where
        # clientSecret was stored with the banking password as a prefix.
        pwd_value = self.__config["DEFAULT"].get("pwd", "").strip()
        client_secret_value = self.__config["DEFAULT"].get("clientSecret", "").strip()
        if not pwd_value or not client_secret_value:
            return
        if client_secret_value == pwd_value or not client_secret_value.startswith(pwd_value):
            return

        print("WARNUNG: Secret 'clientSecret' scheint das Passwort als Präfix zu enthalten.")
        print("Secret 'clientSecret' wird neu abgefragt und im Secret-Backend überschrieben.")
        new_client_secret_value = self.__promptAndStoreSecret(
            "clientSecret",
            "Bitte geben Sie Ihr oAuth clientSecret für den API Zugang erneut ein: ",
        )
        if new_client_secret_value:
            self.__config["DEFAULT"]["clientSecret"] = new_client_secret_value

    def __promptAndStoreSecret(self, secretName: str, prompt: str) -> str:
        secretStore = SecretStore(
            self.dirname,
            self.__config["DEFAULT"]["secretBackend"],
            self.__config["DEFAULT"]["secretNamespace"],
        )
        secret_value = getpass.getpass(prompt=prompt, stream=None).strip()
        if not secret_value:
            return secret_value
        try:
            secretStore.set_secret(secretName, secret_value)
        except RuntimeError as error:
            print(f"WARNUNG: {error}")
            print(f"Secret '{secretName}' konnte nicht gespeichert werden, wird aber im aktuellen Programmlauf verwendet.")
        return secret_value

    def __parseStringList(self, value: str) -> set[str]:
        cleaned_value = value.strip()
        if cleaned_value.startswith("{") and cleaned_value.endswith("}"):
            cleaned_value = cleaned_value[1:-1]

        entries = re.split(r"\s*,\s*", cleaned_value)
        return {
            entry.strip().strip("\"'")
            for entry in entries
            if entry.strip().strip("\"'")
        }

    def __isTruthy(self, inputString: str):
        return inputString.lower() in ["ja", "j", "true", "yes", "y", "1"]

    def __createIfNotExistDir(self, dir: str):
        if not os.path.isabs(dir):
            dir = os.path.join(self.dirname, dir)

        if not os.path.exists(dir):
            shouldCreateDir = self.__getInputForString("Zielverzeichnis nicht gefunden. Soll es erstell werden? (ja/nein): ")
            if self.__isTruthy(shouldCreateDir):
                os.makedirs(dir)
            else:
                self.__printMessage("Zielverzeichnis wurde nicht erstellt. Bis zum nächsten Mal!")
                exit(0)
        return dir
