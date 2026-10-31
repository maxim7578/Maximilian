# BMW HU Info

Lesender SSH-Diagnose-Client fuer BMW-Headunits (**NBT, NBTEVO, ENAVEVO, MGU**)
in zwei Varianten:

- **`windows/`** - Python-Software mit grafischer Oberflaeche (laeuft unter
  Windows, auch Linux/macOS) zum Ausprobieren am PC mit ENET-Kabel.
- **`android/`** - Android-App (Kotlin + Jetpack Compose) fuer unterwegs am
  Fahrzeug.

## Was das Tool tut (und was nicht)

Es liest ausschliesslich Informationen aus:

- System- und Hardware-Infos (Kernel, OS-Version, CPU, Speicher, Laufwerke)
- Netzwerkdaten der Headunit
- Fehlerspeicher / Logs (`dmesg`, `journalctl`)
- auf Wunsch geraete-spezifische Dateien (z. B. VIN, Software-/Teilenummer) ueber
  konfigurierbare Platzhalter

**Nur-Lesen ist per Konstruktion erzwungen:** Eine Sicherheitsschicht
(`safety.py` bzw. `Safety.kt`) laesst nur eine feste Positivliste lesender
Programme zu und weist Umleitungen (`>`), Verkettungen (`;`, `&&`),
Kommandosubstitution und schreibende Optionen (`sed -i`, `find -exec` ...) ab.

**Nicht enthalten:** kein FSC-Code-Generator, kein Coding-Schreiben, keine
Lizenz- oder Schutz-Umgehung. Das Tool veraendert am Fahrzeug nichts.

## Befehlskatalog

`shared/commands.json` ist die gemeinsame Quelle fuer beide Apps (die Android-App
bekommt eine Kopie unter `android/app/src/main/assets/`). Befehle mit
Platzhaltern wie `<PFAD_ZUR_VIN_DATEI>` sind bewusst leer gelassen - die exakten
Pfade unterscheiden sich je Headunit und muessen am Geraet eingetragen werden.
Befehle mit Platzhalter werden ausgelassen, bis sie ersetzt sind.

## Windows-Software (Python)

Voraussetzung: Python 3.10+ (unter Windows "Add python to PATH" anhaken).

```bash
cd windows
python -m pip install -r requirements.txt
```

GUI starten:

```bash
python -m bmw_hu_info
```

Oder per Kommandozeile (z. B. alles fuer eine NBTEVO auslesen):

```bash
python -m bmw_hu_info.cli --host 169.254.199.99 --benutzer root --headunit NBTEVO
```

Nur Befehle anzeigen, ohne Verbindung:

```bash
python -m bmw_hu_info.cli --host 0.0.0.0 --headunit MGU --liste
```

Tests laufen lassen:

```bash
cd windows
python -m pytest
```

### Eigenstaendige .exe (optional)

```bash
python -m pip install pyinstaller
pyinstaller --noconsole --onefile --name BMW-HU-Info ^
  --add-data "..\shared\commands.json;shared" bmw_hu_info\__main__.py
```

> Hinweis: Bei gebuendelter .exe muss der Katalogpfad ggf. angepasst werden,
> da `shared/` dann im temporaeren PyInstaller-Verzeichnis liegt.

## Android-App (Kotlin)

Voraussetzung: Android Studio (aktuell) mit Android SDK 34.

1. In Android Studio **Open** -> Ordner `android/` waehlen.
2. Gradle synchronisieren lassen (laedt JSch und Compose).
3. App auf Geraet/Emulator starten (**Run**).

Oder per Kommandozeile mit lokalem Gradle 8.9+:

```bash
cd android
gradle wrapper        # einmalig, erzeugt ./gradlew
./gradlew assembleDebug
```

Die fertige APK liegt dann unter
`android/app/build/outputs/apk/debug/app-debug.apk`.

Unit-Tests der Sicherheitslogik:

```bash
cd android
./gradlew testDebugUnitTest
```

## Ohne Fahrzeug testen (simulierte Headunit)

Damit du beide Apps vorab ausprobieren kannst, gibt es einen kleinen
SSH-Testserver, der sich wie eine Headunit verhaelt und Beispieldaten
liefert.

```bash
cd windows
python -m pip install -r requirements.txt
python tools/mock_headunit.py --port 2222 --passwort test
```

Dann in einem zweiten Fenster die Software dagegen laufen lassen:

```bash
python -m bmw_hu_info.cli --host 127.0.0.1 --port 2222 --benutzer root --passwort test --headunit NBTEVO
```

Oder die GUI (`python -m bmw_hu_info`) oeffnen und als IP `127.0.0.1`,
Port `2222`, Passwort `test` eintragen. Die Android-App kann ueber die
IP des PCs im selben Netz auf denselben Testserver zugreifen.

> Der Testserver akzeptiert jede Anmeldung (bzw. das gesetzte Passwort)
> und ist nur zum Ausprobieren gedacht. Die ausgegebenen Werte sind
> erfunden.

## Verbindung zum Fahrzeug (Kurzfassung)

1. ENET-Kabel (OBD <-> Ethernet) ans Fahrzeug, am PC Netzwerk auf DHCP oder
   passende APIPA-Adresse (169.254.x.x) stellen. Bei der Android-App ueber WLAN
   bzw. USB-Ethernet-Adapter ins selbe Netz.
2. IP der Headunit eintragen, Benutzer und Passwort **oder** privaten Schluessel
   angeben.
3. Headunit-Typ waehlen und "Alle lesen" oder einen einzelnen Eintrag antippen.

Welche IP, welcher Benutzer und welche Authentifizierung gelten, haengt vom
Fahrzeug und der Headunit ab - diese Daten gibst du selbst ein, das Tool bringt
keine fahrzeugspezifischen Zugangsdaten mit.

## Status

Fruehe Version (0.1.0). Sicherheitsschicht, Katalog und der komplette
SSH-Weg sind durch Tests abgedeckt (29 Python-Tests, inkl. echtem
Integrationstest gegen die simulierte Headunit; dazu JUnit-Tests fuer die
Android-Sicherheitslogik). Geraete-spezifische Pfade (VIN,
Software-/Teilenummer) sind Platzhalter und am realen Fahrzeug zu ergaenzen.
