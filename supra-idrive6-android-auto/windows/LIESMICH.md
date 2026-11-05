# NBT-AAD SSH-Werkzeug (Windows)

Kleines Menü-Programm für den Laptop am ENET-Kabel. Es verbindet sich per SSH mit der NBT-Evo-Headunit und
erledigt die Schritte aus `install.md`, ohne dass du Befehle abtippen musst.

## Start

1. ENET-Kabel an Auto und Laptop, Zündung an, USB-Stick im Auto.
2. Beide Dateien (`nbt-aad-ssh.ps1` und `NBT-AAD SSH.bat`) in denselben Ordner legen.
3. Doppelklick auf **`NBT-AAD SSH.bat`**.
4. Bei jedem Schritt fragt `ssh` nach dem Passwort der Headunit.

Andere Adresse (z. B. TurboCode-Proxy auf Port 6969):

```
powershell -ExecutionPolicy Bypass -File nbt-aad-ssh.ps1 -HeadUnit 127.0.0.1 -Port 6969
```

## Menü

| Nr. | Was | Ändert etwas? |
|-|-|-|
| 1 | Verbindung testen (Knoten, USB-Stick) | nein |
| 2 | Log holen: speichert `nbt-aad-log_<Datum>.txt` auf dem Desktop und zeigt die wichtigsten Zeilen | nein |
| 3 | Status: Daemon, iDrive-App, laufender Prozess, Einstellungen | nein |
| 4 | Installieren/Aktualisieren vom Stick (`nbt-aad` und `release/`); alte Dateien bleiben als `.old` | ja, fragt vorher |
| 5 | Dauerhaftes Log auf dem Stick (`NBT_LOG_FILE` in `/opt/aa/nbt-aad.env`) | ja, fragt vorher |
| 6 | iDrive neu starten (`OnOffDSICommander appreset`) | ja, fragt vorher |

Voraussetzung: Windows 10/11 mit dem eingebauten OpenSSH-Client (`ssh`). Fehlt er: Einstellungen > Apps >
Optionale Features > „OpenSSH-Client“ hinzufügen.

Nicht im Auto getestet: Das Werkzeug führt nur die Befehle aus der Anleitung des Projekts aus. Wenn ein Schritt
eine Fehlermeldung zeigt, die Ausgabe an Claude schicken.
