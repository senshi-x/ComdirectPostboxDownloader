# Comdirect Postbox Downloader

Lädt alle PDF-Dokumente aus einer beliebigen Zeitspanne herunter.
Anforderung: Läuft nur auf Windows. Erfordert zwingend den Chrome-Browser, der installiert sein muss.

Das Skript erfordert eine einzige Benutzereingabe (die PhotoTAN, die seit neustem für den Zugriff auf die Postbox erforderlich ist). Ansonsten gibt es optional eine Auswahlmöglichkeit der Zeitspanne in der Befehlszeile, sofern man diese nicht in der settings.ini festlegt.



## Settings
Hier gibt es drei Werte zu setzen:
**user** = Deine Zugangsnummer
**pass** = Deine PIN/Passwort
**range** = Welche Zeitspanne soll heruntergeladen werden. Entspricht der Position in der Zeitspanne-auswahlbox in der Postbox (1 bis x). Ist kein Wert angegeben (range=), wird das Programm den Benutzer eine interaktive Auswahl anbieten.
**outputdir** = Ausgabeverzeichnis, in das die heruntergeladenen Dateien gespeichert werden sollen.


Siehe settings.ini.example als Beispieldatei.

### Übliche Range-Werte (Stand Sep 2019)
1: Letzte 30 Tage-MONAT
2: Letztes halbes Jahr-HALBES_JAHR
3: Gesamter Zeitraum-GESAMTER_ZEITRAUM
4: 2019-2019
5: 2018-2018
6: 2017-2017
7: 2016-2016

### Outputdir
Es können relative Pfade angegeben werden. Diese werden ausgehend vom Skriptverzeichnis aufgelöst. Z.b. Dokumente als Unterverzeichnis.
Wird ein absoluter Pfad angegeben (z.b. C:\\Benutzer\\Annonymus\\Dokumente\\Bank\\Comdirect\\PDFs ), so wird dieser auch korrekt verwendet.
Wichtig: "\" als Pfad-Trenner muss immer doppelt angegeben werden wie in obigem Beispiel!
