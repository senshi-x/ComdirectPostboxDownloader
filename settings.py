import os
import configparser
import getpass


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
                if not self.__isSettingNameFilledInConfig("user"):
                    self.__config["DEFAULT"]["user"] = self.__getInputForString("Bitte geben Sie Ihre Kundennummer ein: ")

                if not self.__isSettingNameFilledInConfig("pwd"):
                    self.__config["DEFAULT"]["pwd"] = getpass.getpass(prompt="Bitte geben Sie das dazugehörige Passwort ein: ", stream=None)

                if not self.__isSettingNameFilledInConfig("clientId"):
                    self.__config["DEFAULT"]["clientId"] = self.__getInputForString("Bitte geben Sie die oAuth clientId für den API-Zugang ein: ")

                if not self.__isSettingNameFilledInConfig("clientSecret"):
                    self.__config["DEFAULT"]["clientSecret"] = getpass.getpass(prompt="Bitte geben Sie Ihr oAuth clientSecret für den API Zugang ein: ", stream=None)

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
