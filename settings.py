import os
import configparser
import getpass


class Settings:
    SETTINGS_FILENAME = "settings.ini"

    def __init__(self, settings_parameter):
        if os.path.isfile(settings_parameter):
            self.absSettingsDirName = (
                settings_parameter
                if os.path.isabs(settings_parameter)
                else os.path.join(os.getcwd(), settings_parameter)
            )
        elif os.path.isdir(settings_parameter):
            self.absSettingsDirName = (
                os.path.join(settings_parameter, self.SETTINGS_FILENAME)
                if os.path.isabs(settings_parameter)
                else os.path.join(
                    os.getcwd(), settings_parameter, self.SETTINGS_FILENAME
                )
            )
        else:
            raise NameError("please provide settings.ini or path ")

        self.readSettings()

    def readSettings(self):
        # If you want comfort, put your data into the settings.ini
        # If you understandably don't want to leave all credentials in a clear textfile,
        # just leave them out and you will be prompted for them.
        print("loading settings...")

        if os.path.isfile(self.absSettingsDirName):
            self.__config = configparser.ConfigParser()
            self.__config.read(self.absSettingsDirName)
            try:
                if not self.__isSettingNameFilledInConfig("user"):
                    self.__config["DEFAULT"]["user"] = self.__getInputForString(
                        "Please enter your user number / Kundennummer: "
                    )

                if not self.__isSettingNameFilledInConfig("pwd"):
                    self.__config["DEFAULT"]["pwd"] = getpass.getpass(
                        prompt="Please enter your password: ", stream=None
                    )

                if not self.__isSettingNameFilledInConfig("clientId"):
                    self.__config["DEFAULT"]["clientId"] = self.__getInputForString(
                        "Please enter your clientId for API access: "
                    )

                if not self.__isSettingNameFilledInConfig("clientSecret"):
                    self.__config["DEFAULT"]["clientSecret"] = self.__getInputForString(
                        "Please enter your clientSecret for API access: "
                    )

                if not self.__isSettingNameFilledInConfig("outputDir"):
                    self.__config["DEFAULT"]["outputDir"] = self.__getInputForString(
                        "Please enter the path to the folder you want reports to be downloaded to: "
                    )

                if not self.__config.has_option(None, "dryRun"):
                    self.__config["DEFAULT"][
                        "dryRun"
                    ] = self.__checkInputForBoolTrueString(
                        self.__getInputForString(
                            "Should the run a test run? (no files get downloaded) [yes/no]: "
                        )
                    )
            except Exception as error:
                print("ERROR", error)
                exit(-1)

            # check out dir right away..
            self.outputDir = self.__createIfNotExistDir(
                self.__config["DEFAULT"]["outputDir"]
            )

            print("settings set.")
        else:
            raise NameError("please provide settings.ini to start program.")

    def showSettings(self):
        for key in self.__config["DEFAULT"]:
            output = key + ": "
            if key == "pwd":
                pwOut = ""
                for _ in range(len(self.__config["DEFAULT"][key])):
                    pwOut += "*"
                output += pwOut
            else:
                output += self.__config["DEFAULT"][key]
            print(output)

    def getValueForKey(self, settingName, section="DEFAULT"):
        if self.__isSettingNameFilledInConfig(settingName, section):
            return self.__config[section][settingName]
        else:
            raise NameError("SettingName not set")

    def getBoolValueForKey(self, settingName, section="DEFAULT"):
        if self.__isSettingNameFilledInConfig(settingName, section):
            return self.__checkInputForBoolTrue(self.__config[section][settingName])
        else:
            raise NameError("SettingName not set")

    def __isSettingNameFilledInConfig(self, settingName, section="DEFAULT"):
        isAvailAndFilled = True

        if settingName not in self.__config[section]:
            isAvailAndFilled = False

        if not self.__config.has_option(None, settingName):
            isAvailAndFilled = False

        if not self.__config[section][settingName]:
            isAvailAndFilled = False

        return isAvailAndFilled

    def __getInputForString(self, printString):
        # print("----------------------------------------------------------------")
        inp = input(printString)
        # print("----------------------------------------------------------------")
        return inp

    def __printMessage(self, message):
        print(message)

    def __checkInputForBoolTrue(self, inputString):
        retValue = False
        if inputString.lower() in ["true", "yes", "y", "1"]:
            retValue = True
        return retValue

    def __checkInputForBoolTrueString(self, inputString):
        retValue = "False"
        if inputString.lower() in ["true", "yes", "y", "1"]:
            retValue = "True"
        return retValue

    def __createIfNotExistDir(self, dir):
        self.__printMessage("Checking if given outputDir exists...")

        if not os.path.isabs(dir):
            dir = os.path.join(os.path.dirname(self.absSettingsDirName), dir)

        if not os.path.exists(dir):
            shouldCreateDir = self.__getInputForString(
                "Path not found. Should I create it? (yes/no):"
            )
            if shouldCreateDir.lower() in ["true", "yes", "y", "1"]:
                os.makedirs(dir)
                self.__printMessage("Path created: " + dir)
            else:
                self.__printMessage("Path not created, script exited 0")
                exit
        else:
            self.__printMessage("Moving on. Path exists: " + dir)
        return dir
