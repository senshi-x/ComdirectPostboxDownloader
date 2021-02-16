# Comdirect Postbox Downloader

Lädt alle PDF-Dokumente aus einer beliebigen Zeitspanne herunter.

Benötigt wird Python 3.x

Das Tool muss mittels Kommandozeile gestartet und bedient werden. Es ist zwingend erforderlich, die `settings.ini` anzulegen.
Aktuell wir nur das Photo-PushTAN-Verfahren unterstützt. Das klassische PhotoTAN-Verfahren ist implementiert, aber noch nicht getestet.

# Setup
Im Verzeichnis einmalig ausführen.
> pip install -r requirements.txt

Die `settings.ini` konfigurieren und bereitstellen (siehe Kapitel unten).

Anschließend die **main.py** starten, z.B. mit
> python main.py


## Settings
Hier gibt es mehrere Werte zu setzen. Die folgenden sind optional. Sind diese nicht gesetzt, werden sie jedes Mal bei der Ausführung abgefragt. Jeder Wert kann einzeln gesetzt oder freigelassen werden. Das Speichern aller Zugangsdaten im Klartext kann ein Sicherheitsrisiko bedeuten, hier also mit Vernunft herangehen. Als Minimum empfiehlt es sich, zumindest das Passwort hier NICHT zu hinterlegen.
- **user** = Deine Zugangsnummer
- **pwd** = Deine PIN/Passwort
- **clientId** = ClientID, die via API Access erhaltbar ist (https://kunde.comdirect.de/itx/oauth/privatkunden)
- **clientSecret** = ClientSecret, welches ebenfalls in vorigem Link verfügbar ist

Die folgenden Einstellungen erlauben es, das Verhalten des Downloads zu konfigurieren:
- **outputDir** = Ausgabeverzeichnis, in das die heruntergeladenen Dateien gespeichert werden sollen.
- **dryRun** = Leerlauf, das Herunterladen wird nur simuliert
- **useSubFolders** = Legt die Dateien je nach Dateiname in Unterordner ab (alle Finanzreporte unter Finanzreporte, etc.)
- **downloadOnlyFilenames** = Lädt nur Dateien herunter, deren Dateiname mit einem der hier angegeben Wörter beginnt. Bei False wird alles heruntergeladen.
- **downloadOnlyFilenamesArray** = Liste der gewünschten Dateinamen
- **downloadOnlyFromOnlineArchive** = Lädt nur Dateien aus dem Postbox-Archiv herunter.


Siehe settings.ini.example als Beispieldatei.

### Outputdir
Es können relative Pfade angegeben werden. Diese werden ausgehend vom Skriptverzeichnis aufgelöst. Z.b. Dokumente als Unterverzeichnis.
Wird ein absoluter Pfad angegeben (z.b. *C:\\Benutzer\\Annonymus\\Dokumente\\Bank\\Comdirect\\PDFs* ), so wird dieser auch korrekt verwendet.

Wichtig: "\" als Pfad-Trenner muss immer doppelt angegeben werden wie in obigem Beispiel!


## Verwendet:
- Python 3.x
- Python-Bibliotheken:
  - Pathvalidate (für Validierung der Ausgabedateinamen)
  - Requests (für REST-Anfragen)
