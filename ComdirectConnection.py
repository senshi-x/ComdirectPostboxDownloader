import requests
import random
import string
import json
from datetime import datetime, timedelta
from threading import Timer

baseUrl = "https://api.comdirect.de/"


class Connection:
    def __init__(self, client_id, client_secret, username, password):
        self.client_id : str = client_id
        self.client_secret : str = client_secret
        self.username = username
        self.password = password
        self.sessionId = ""
        for _ in range(12):
            self.sessionId += random.choice(string.ascii_lowercase + string.digits)
        self.requestId = datetime.now().strftime("%Y%m%d%H%M%S")
        self.refreshTimer : Timer = None
        self.refreshTimerRunning = False

    def login(self):
        result = self.__loadData()
        if result == False:
            self.__getOAuth()
            self.__getSession()
            self.__getTANChallenge()
            self.__getCDSecondary()
            self.__storeData()
        self.__startRefreshTimer()

    def logout(self):
        self.__revoke()
        self.__deleteData()

    def __getHeaders(self, contentType="application/json", requestId=""):

        if not requestId:
            self.requestId = datetime.now().strftime("%Y%m%d%H%M%S")

        headers = {"Accept": "application/json", "Content-Type": contentType}

        try:

            if self.access_token:
                headers["Authorization"] = "Bearer " + self.access_token
        except Exception as err:
            pass

        try:
            if self.sessionId:
                headers["x-http-request-info"] = str(
                    {
                        "clientRequestId": {
                            "sessionId": self.sessionId,
                            "requestId": self.requestId,
                        }
                    }
                )
        except Exception as err:
            print(err)
            print("no self.sessionId set")
            pass

        return headers

    def __getOAuth(self):
        r = requests.post(
            baseUrl + "oauth/token",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "password",
                "username": self.username,
                "password": self.password,
            },
            headers=self.__getHeaders("application/x-www-form-urlencoded"),
        )

        try:
            rjson = r.json()
            self.access_token = rjson["access_token"]
            self.refresh_token = rjson["refresh_token"]
        except Exception as err:
            raise err

    def __getSession(self):
        """
        Retrieve the current session, initializes if not existing.
        """
        headers = self.__getHeaders("application/x-www-form-urlencoded")
        r = requests.get(
            baseUrl + "api/session/clients/user/v1/sessions", headers=headers
        )
        if r.status_code == 200:
            try:
                self.sessionApiId = r.json()[0]["identifier"]
            except Exception as err:
                raise err
        else:
            print(r.status_code)
            print(r.json())

    def __getTANChallenge(self):
        """
        POST a TAN Challenge. This will trigger a validation request that needs to be fulfilled with a valid TAN.
        WARNING: More than 5 failed/unverified attempts will lead the banking access to be locked and requires unlocking by customer support!!!
        """
        r = requests.post(
            baseUrl
            + "api/session/clients/user/v1/sessions/"
            + self.sessionApiId
            + "/validate",
            json={
                "identifier": self.sessionApiId,
                "sessionTanActive": True,
                "activated2FA": True,
            },
            headers=self.__getHeaders("application/json"),
        )

        if r.status_code == 201:
            self.__getSessionTAN(r.headers)
        else:
            print(r.status_code)
            print(r.json)

    def __getSessionTAN(self, validationHeaders):
        """
        Retrieves a valid TAN after the user has solved the challenge.
        """

        xauthinfoheaders = json.loads(validationHeaders["x-once-authentication-info"])
        headers = self.__getHeaders("application/json")
        headers["x-once-authentication-info"] = json.dumps(
            {"id": xauthinfoheaders["id"]}
        )
        if xauthinfoheaders["typ"] == "P_TAN_PUSH":
            # If Push-TAN, user needs to approve the TAN in app, that's it.
            print(
                "You are using PushTAN. Please use your smartphone's Comdirect photoTAN app to validate the access request to your 'personal area'."
            )
            print(
                "Please only continue once you have done so! Failure to validate this request for 5 consecutive times will result in your access being blocked."
            )
            input(
                "Press ENTER after you have cleared the PushTAN challenge on your phone."
            )
        elif xauthinfoheaders["typ"] == "P_TAN":
            # If photoTAN, user needs to solve the challenge and provide the tan manually.
            tan = self.__challenge_ptan(xauthinfoheaders["challenge"])
            headers["x-once-authentication"] = tan
        elif xauthinfoheaders["typ"] == "M_TAN":
            # If mobile TAN, user gets TAN via mobile.
            tan = self.__challenge_mtan(xauthinfoheaders["challenge"])
            headers["x-once-authentication"] = tan
        else:
            print(
                "Sorry, the TAN type "
                + xauthinfoheaders["typ"]
                + " is not yet supported"
            )
            exit(1)

        r = requests.patch(
            baseUrl + "api/session/clients/user/v1/sessions/" + self.sessionApiId,
            json={
                "identifier": self.sessionApiId,
                "sessionTanActive": True,
                "activated2FA": True,
            },
            headers=headers,
        )
        if r.status_code != 200:
            print(r.status_code)
            print(r.json())

    def __challenge_ptan(self, challenge):
        """
        Challenge to solve for photo TAN
        challenge : Base64 encoded image data
        """
        from PIL import Image
        import base64
        import io

        Image.open(io.BytesIO(base64.b64decode(challenge))).show()
        print(" Please follow the usual photo TAN challenge process.")
        tan = input("Enter the TAN code: ")
        return tan

    def __challenge_mtan(self, challenge):
        """
        Challenge to get the mobile TAN
        """

        print(" Please follow the usual mobile TAN challenge process.")
        tan = input("Enter the TAN code: ")
        return tan

    def __getCDSecondary(self):
        r = requests.post(
            baseUrl + "oauth/token",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "cd_secondary",
                "token": self.access_token,
            },
        )

        if r.status_code == 200:
            #print(json.dumps(r.json()))

            rjson = r.json()
            self.access_token = rjson["access_token"]
            self.refresh_token = rjson["refresh_token"]
            self.scope = rjson["scope"]  # Currently always "full access"
            self.kdnr = rjson["kdnr"]
            self.expires_in = rjson["expires_in"]
            # The following are provided, but serve no actual use.
            # self.bpid = rjson["bpid"]
            # self.kontaktId = rjson["kontaktId"]
        else:
            raise RuntimeWarning(
                r.request.url
                + " exited with "
                + str(r.status_code)
                + ": "
                + json.dumps(r.json())
            )

    def __storeData(self):
        with open('cache','w') as f:
            data = self.__dict__.copy()
            data.pop("refreshTimer")
            data.pop("refreshTimerRunning")
            data['expirationtime'] = (datetime.now() + timedelta(seconds = self.expires_in)).isoformat()
            f.write(json.dumps(data, indent=4))

    def __loadData(self):
        try:
            with open('cache', 'r') as f:
                data = json.loads(f.read())
                expires_in = datetime.fromisoformat(data['expirationtime']) - datetime.now()
                # If token expires very soon, just return False to indicate a regular startup/login sequence should occur.
                if 'expires_in' not in data:
                    return False
                if expires_in.total_seconds() > 10:
                    data['expires_in'] = expires_in.total_seconds()
                else:
                    return False
                data['refreshTimerRunning'] = False
                self.__dict__ = data
                return True
        except (IOError, json.JSONDecodeError) :
            return False

    def __deleteData(self):
        import os
        if os.path.exists('cache'):
            os.remove('cache')


    def refresh(self):
        self.refreshTimerRunning = False
        r = requests.post(
            baseUrl + "oauth/token",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
        )
        if r.status_code == 200:
            rjson = r.json()
            self.access_token = rjson["access_token"]
            self.refresh_token = rjson["refresh_token"]
            self.scope = rjson["scope"]  # Currently always "full access"
            self.__storeData()
            self.__startRefreshTimer()
        

    def __revoke(self):
        self.__stopRefreshTimer()
        r = requests.delete(
            baseUrl + "oauth/revoke",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": "Bearer " + self.access_token,
            },
        )
        if r.status_code != 204:
            print("Something went wrong trying to revoke your access token.")

    def __startRefreshTimer(self):
        if not self.refreshTimerRunning:
            # When logging in, we get told how long tokens may live. We refresh 10 seconds before that.
            self.refreshTimer = Timer(self.expires_in - 10, self.refresh)
            self.refreshTimer.daemon = True
            self.refreshTimer.start()
            self.refreshTimerRunning = True

    def __stopRefreshTimer(self):
        self.refreshTimer.cancel()
        self.refreshTimerRunning = False
        
    def getMessagesList(self, start=0, count=1000):
        r = requests.get(
            baseUrl
            + "api/messages/clients/user/v2/documents?paging-first="
            + str(start)
            + "&paging-count="
            + str(count),
            headers={
                "Accept": "application/json",
                "Authorization": "Bearer " + self.access_token,
                "x-http-request-info": str(
                    {
                        "clientRequestId": {
                            "sessionId": self.sessionId,
                            "requestId": self.requestId,
                        },
                    }
                ),
            },
        )
        if r.status_code != 200:
            raise RuntimeWarning(
                r.request.url
                + " exited with "
                + str(r.status_code)
                + ": "
                + json.dumps(r.json())
            )
        # print(json.dumps(r.json(), indent=4))
        return r.json()

    def downloadMessage(self, document):
        r = requests.get(
            baseUrl + "api/messages/v2/documents/" + document["documentId"],
            headers={
                "Accept": document["mimeType"],
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": "Bearer " + self.access_token,
                "x-http-request-info": str(
                    {
                        "clientRequestId": {
                            "sessionId": self.sessionId,
                            "requestId": self.requestId,
                        },
                    }
                ),
            },
        )
        if r.status_code == 200:
            return r.content
        else:
            print(r.status_code)
            # print(json.dumps(r.json(), indent=4))
            print(r.json())
            raise RuntimeWarning("Document could not be retrieved!")

    def getBalances(self):
        r = requests.get(
            baseUrl + "api/banking/clients/user/v2/accounts/balances",
            headers = self.__getHeaders()
        )
        if r.status_code == 200:
            return r.json()
        else:
            print(r.status_code)
            print(json.dumps(r.json(), indent=4))
            raise RuntimeWarning("Document could not be retrieved!")