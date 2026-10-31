# bmw-cardata

Kommandozeilen-Client für die **offizielle BMW CarData API**. Er liest Kilometerstand,
Ladestand, Reichweite, Ladestatus, Tankfüllstand, Türschloss, 12-V-Batterie,
Service-Fälligkeit und Position deines BMW oder MINI.

## Warum nicht bimmer_connected?

`bimmer_connected` (und damit auch das ältere `BMW-i-Remote` in diesem Repo)
funktioniert seit dem 29. September 2025 nicht mehr: BMW sperrt seitdem
Drittanbieter-Zugriffe auf die My-BMW-Schnittstelle. Der offizielle Ersatz ist
BMW CarData.

## Was geht und was nicht

- **Nur lesen.** CarData kennt keine Befehle: kein Verriegeln, kein Hupen, keine
  Klimatisierung, kein Ladestart.
- **Nur EU-Konten.** Das CarData-Portal gibt es nicht in jedem Land.
- **50 Abrufe pro Tag** pro Konto. `fahrzeuge` und `basisdaten` kosten je 1 Abruf, `status`
  1 Abruf. Nur beim allerersten `status` ohne Fahrgestellnummer kommt 1 Abruf für die
  Fahrzeugliste dazu (danach ist das Fahrzeug gemerkt) und einmalig 1 bis 2 Abrufe für den
  Datencontainer. `verlauf` und `kontingent` kosten nichts. Ist das Limit erreicht, meldet BMW
  HTTP 429, der Client zeigt dann „Tageslimit erreicht“.
- Werte kommen nur, wenn das Auto Daten gesendet hat. Fehlen Werte, kurz die
  My-BMW-App öffnen oder ein Stück fahren.

## Einrichtung im BMW-Portal (einmalig)

1. Bei <https://www.bmw.de/de-de/mybmw/vehicle-overview> anmelden
   (MINI: <https://www.mini.de/de-de/mymini/vehicle-overview>).
2. Fahrzeug wählen, dann **BMW CarData**.
3. Unter **CARDATA API** eine **Client-ID** erzeugen und kopieren
   (Anleitung von BMW: <https://bmw-cardata.bmwgroup.com/customer/public/api-documentation/Id-Technical-registration_Step-1>).
   Den Knopf „Gerät authentifizieren“ im Portal **nicht** drücken, das übernimmt der Client.
4. **„Zugriff auf CarData API anfordern“** klicken und etwa eine Minute warten,
   bis BMW die Freigabe verteilt hat. Sonst gibt es HTTP 403.

Streaming (MQTT) braucht dieser Client nicht.

## Installation

```bash
cd bmw-cardata
python3 -m pip install .
```

Python 3.10 oder neuer.

## Benutzung

```bash
export BMW_CARDATA_CLIENT_ID="deine-client-id"
bmw-cardata anmelden          # Link öffnen, Code eingeben, bei BMW bestätigen
bmw-cardata fahrzeuge         # Fahrgestellnummern
bmw-cardata status            # Status deines einzigen Fahrzeugs
bmw-cardata status WBA…       # Status eines bestimmten Fahrzeugs
bmw-cardata status --speichern  # Status zeigen und im lokalen Verlauf ablegen
bmw-cardata status --json     # Status als JSON, z. B. für eigene Skripte
bmw-cardata basisdaten WBA…   # Basisdaten, so wie BMW sie liefert
bmw-cardata verlauf           # die letzten 10 gespeicherten Abrufe (--anzahl N für mehr)
bmw-cardata verlauf --csv > fahrten.csv   # alle Einträge für Excel/LibreOffice
bmw-cardata kontingent        # eigene Abrufe der letzten 24 Stunden
bmw-cardata abmelden          # gespeicherte Anmeldung löschen
```

Beispielausgabe:

```
Fahrzeug WBA12345678901234
Kilometerstand: 42000 km  (Stand: 2026-10-30T10:00:00Z)
Ladestand Hochvoltbatterie: 80 %
Elektrische Reichweite: 210 km
```

Hat BMW eine Position geliefert, steht am Ende ein Link zu OpenStreetMap
(`Karte: https://www.openstreetmap.org/?mlat=…`).

### Fahrzeug merken

Hat dein Konto genau ein Fahrzeug, merkt sich der Client dessen Fahrgestellnummer beim
ersten `status` und spart danach den Abruf der Fahrzeugliste. `fahrzeuge` frischt die
gemerkte Nummer auf (bei mehreren Fahrzeugen wird keine gemerkt). Lehnt BMW das gemerkte
Fahrzeug ab (z. B. nach einem Verkauf), vergisst der Client die Nummer, holt einmal die
aktuelle Fahrzeugliste und versucht es damit erneut.

### Verlauf

`status --speichern` hängt jeden Abruf an `verlauf.jsonl` an (im selben Ordner wie die
Anmeldung, Rechte 600, da die Position enthalten sein kann). `verlauf` zeigt die Einträge
mit den seit dem Eintrag davor gefahrenen Kilometern:

```
30.10.2026 17:30  Kilometerstand: 42000 km, Ladestand Hochvoltbatterie: 64 %  (+120 km)
31.10.2026 08:00  Kilometerstand: 42063 km, Ladestand Hochvoltbatterie: 51 %  (+63 km)
```

`verlauf --csv` gibt alle Einträge mit Semikolon getrennt aus, so öffnet ein deutsches
Excel sie direkt in Spalten. `abmelden` löscht den Verlauf nicht (es weist aber darauf hin);
zum Löschen die Datei `verlauf.jsonl` entfernen.

Für einen regelmäßigen Verlauf eignet sich ein Cron-Eintrag, z. B. zweimal am Tag
(`crontab -e`; den vollen Pfad liefert `command -v bmw-cardata`):

```
0 7,19 * * * /voller/pfad/zu/bmw-cardata status --speichern >/dev/null
```

### Kontingent

`kontingent` zählt die Abrufe dieses Programms in den letzten 24 Stunden und sagt, wie
viele der 50 noch frei sind. Ist alles verbraucht, nennt es den Zeitpunkt, ab dem der
älteste Abruf aus dem 24-Stunden-Fenster fällt. Zwei Einschränkungen: Abrufe anderer
Programme mit derselben Client-ID (z. B. Home Assistant) zählt es nicht mit, und wann
BMW den Zähler genau zurücksetzt, ist hier nicht bekannt. Die Anzeige ist also eine
Schätzung von unten.

Die Anmeldung (Client-ID, Tokens, ID des Datencontainers, gemerkte Fahrgestellnummer)
liegt in `~/.config/bmw-cardata/state.json`, nur für dich lesbar (Rechte 600). Daneben
liegen `abrufe.json` (Abrufzähler) und, falls genutzt, `verlauf.jsonl`. Anderer Ort:
`--state PFAD` oder Umgebungsvariable `BMW_CARDATA_STATE`. Abgelaufene Zugangstokens
werden automatisch erneuert; lehnt BMW die Erneuerung ab, einfach neu `anmelden`.

## Datencontainer

Für Telematikdaten verlangt BMW einen „Container“, der festlegt, welche Datenpunkte
geliefert werden. Der Client legt beim ersten `status` einen Container namens
`bmw-cardata-cli Status` an (oder nutzt einen vorhandenen gleichen Namens) und merkt
sich dessen ID. Welche Datenpunkte abgefragt werden, steht in
`src/bmw_cardata/descriptors.py`.

## Tests

```bash
python3 -m pip install -e '.[dev]'
python3 -m pytest
```

Die Tests laufen gegen einen simulierten BMW-Server, ohne Netzwerkzugriff.

## Herkunft der API-Details

Adressen, Anmeldeablauf und Antwortformate stammen aus der öffentlichen
BMW-CarData-Dokumentation und der Home-Assistant-Integration
[kvanbiesen/bmw-cardata-ha](https://github.com/kvanbiesen/bmw-cardata-ha). Der Code
hier ist eigenständig geschrieben.
