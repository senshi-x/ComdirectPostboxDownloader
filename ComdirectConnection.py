from typing import Any
import requests
import json
import secrets
from datetime import datetime

baseUrl = "https://api.comdirect.de/"


class XOnceAuthenticationInfo:
    id: str
    typ: str
    challenge: str
    availableTypes: list[str]

    def __init__(self, data: dict[str, str]):
        self.id = data["id"]
        self.typ = data["typ"]
        if "challenge" in data:
            self.challenge = data["challenge"]
        self.availableTypes = []
        for x in data["availableTypes"]:
            self.availableTypes.append(x)


class DocumentMeta:
    archived: bool
    dateRead: datetime | None
    alreadyRead: bool
    predocumentExists: bool

    def __init__(self, data: dict[str, object]):
        # print(json.dumps(data, indent=4))
        self.archived = data["archived"]
        if "dateRead" in data:
            self.dateRead = datetime.strptime(data["dateRead"], "%Y-%m-%d")
        self.alreadyRead = data["alreadyRead"]
        self.predocumentExists = data["predocumentExists"]


class Document:
    documentId: str
    name: str
    dateCreation: datetime
    mimeType: str
    deleteable: bool
    advertisement: bool
    documentMetadata: DocumentMeta

    def __init__(self, data: dict[str, object]):
        self.documentId = data["documentId"]
        self.name = data["name"]
        self.dateCreation = datetime.strptime(data["dateCreation"], "%Y-%m-%d")
        self.mimeType = data["mimeType"]
        self.deletable = data["deletable"]
        self.advertisement = data["advertisement"]
        self.documentMetadata = DocumentMeta(data["documentMetaData"])


class DocumentList:
    index: int
    matches: int
    unreadMessages: int
    dateOldestEntry: datetime
    matchesInThisResponse: int
    allowedToSeeAllDocuments: bool
    documents: list[Document]

    def __init__(self, data: dict[str, object]):
        self.index = data["paging"]["index"]
        self.matches = data["paging"]["matches"]
        self.unreadMessages = data["aggregated"]["unreadMessages"]
        self.dateOldestEntry = datetime.strptime(data["aggregated"]["dateOldestEntry"], "%Y-%m-%d")
        self.matchesInThisResponse = data["aggregated"]["matchesInThisResponse"]
        self.allowedToSeeAllDocuments = data["aggregated"]["allowedToSeeAllDocuments"]
        self.documents = []
        for x in data["values"]:
            self.documents.append(Document(x))


class Connection:
    attempts: int = 0
    client_id: str
    client_secret: str
    username: str
    password: str
    sessionId: str = secrets.token_urlsafe(32)  # length must be <= 32
    requestId: str = datetime.now().strftime("%H%M%S%f")[:-3]  # length must be == 9

    def __init__(self, client_id: str, client_secret: str, username: str, password: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        # self.sessionId = ""
        # for _ in range(12):
        #     self.sessionId += random.choice(string.ascii_lowercase + string.digits)
        # self.requestId = datetime.now().strftime("%Y%m%d%H%M%S")

    def initSession(self):
        self.__getOAuth()
        self.__getSession()
        return self.__getTANChallenge()

    def __getHeaders(self, contentType: str = "application/json", requestId: str = ""):
        headers = {"Accept": "application/json", "Content-Type": contentType}

        if hasattr(self, "access_token"):
            headers["Authorization"] = "Bearer " + self.access_token

        if hasattr(self, "sessionId"):
            headers["x-http-request-info"] = str(
                {
                    "clientRequestId": {
                        "sessionId": self.sessionId,
                        "requestId": self.requestId,
                    }
                }
            )

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

        if r.status_code == 200:
            rjson = r.json()
            self.access_token = rjson["access_token"]
            self.refresh_token = rjson["refresh_token"]
        else:
            status = r.status_code
            reason = ""
            if status == 401:
                reason = "This usually means wrong clientID/clientSecret"
            elif status == 400:
                reason = "This usually means wrong username/pwd"
            print(f"HTTP Status: {r.status_code} | {r.json()['error_description']} | {reason}")
        r.raise_for_status()
        return r

    def __getSession(self):
        """
        Retrieve the current session, initializes if not existing.
        """
        headers = self.__getHeaders("application/x-www-form-urlencoded")
        r = requests.get(baseUrl + "api/session/clients/user/v1/sessions", headers=headers)
        if r.status_code == 200:
            self.sessionApiId = r.json()[0]["identifier"]
        r.raise_for_status()
        return r

    def __getTANChallenge(self):
        """
        POST a TAN Challenge. This will trigger a validation request that needs to be fulfilled with a valid TAN.
        WARNING: More than 5 failed/unverified attempts will lead the banking access to be locked and requires unlocking by customer support!!!
        """
        r = requests.post(
            baseUrl + "api/session/clients/user/v1/sessions/" + self.sessionApiId + "/validate",
            json={
                "identifier": self.sessionApiId,
                "sessionTanActive": True,
                "activated2FA": True,
            },
            headers=self.__getHeaders("application/json"),
        )
        r.raise_for_status()
        return r

    def getSessionTAN(self, challenge_id: str, challenge_tan: str):
        """
        Retrieves a valid TAN after the user has solved the challenge.
        """

        headers = self.__getHeaders("application/json")
        headers["x-once-authentication-info"] = json.dumps({"id": challenge_id})
        if challenge_tan != "":
            headers["x-once-authentication"] = challenge_tan

        r = requests.patch(
            baseUrl + "api/session/clients/user/v1/sessions/" + self.sessionApiId,
            json={
                "identifier": self.sessionApiId,
                "sessionTanActive": True,
                "activated2FA": True,
            },
            headers=headers,
        )
        return r

    def getCDSecondary(self):
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
            #            print("answer:")
            #            print(json.dumps(r.json()))

            rjson = r.json()
            self.access_token = rjson["access_token"]
            self.refresh_token = rjson["refresh_token"]
            self.scope = rjson["scope"]  # Currently always "full access"
            self.kdnr = rjson["kdnr"]
            # This is always a fixed 599 (seconds), so no need to process
            self.expires_in = rjson["expires_in"]
            # The following are provided, but serve no actual use.
            # self.bpid = rjson["bpid"]
            # self.kontaktId = rjson["kontaktId"]
        r.raise_for_status()
        return r

    def refresh(self):
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
        r.raise_for_status()

    def revoke(self):
        r = requests.delete(
            baseUrl + "oatuh/revoke",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": "Bearer " + self.access_token,
            },
        )
        r.raise_for_status()
        return r

    def getMessagesList(self, start: int = 0, count: int = 1000):
        headers = {
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
        }
        r = requests.get(
            baseUrl + "api/messages/clients/user/v2/documents?paging-first=" + str(start) + "&paging-count=" + str(count),
            headers=headers,
        )
        r.raise_for_status()
        return DocumentList(r.json())

    def downloadDocument(self, document: Document):
        r = requests.get(
            f"{baseUrl}api/messages/v2/documents/{document.documentId}",
            headers={
                "Accept": document.mimeType,
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
        try:
            r.raise_for_status()
            return r.content
        except requests.exceptions.HTTPError as e:
            # Return None on HTTP errors (including 500) to allow the process to continue
            print(f"HTTP Error {r.status_code} for document {document.documentId}: {str(e)}")
            return None
