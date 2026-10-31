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
  1 Abruf (2 ohne Fahrgestellnummer); beim ersten `status` kommen einmalig 1 bis 2 Abrufe
  für den Datencontainer dazu. Danach meldet BMW HTTP 429, der Client zeigt dann „Tageslimit erreicht“.
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
bmw-cardata basisdaten WBA…   # Basisdaten, so wie BMW sie liefert
bmw-cardata abmelden          # gespeicherte Anmeldung löschen
```

Beispielausgabe:

```
Fahrzeug WBA12345678901234
Kilometerstand: 42000 km  (Stand: 2026-10-30T10:00:00Z)
Ladestand Hochvoltbatterie: 80 %
Elektrische Reichweite: 210 km
```

Die Anmeldung (Client-ID, Tokens, ID des Datencontainers) liegt in
`~/.config/bmw-cardata/state.json`, nur für dich lesbar (Rechte 600). Anderer Ort:
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
