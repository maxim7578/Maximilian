# Telefonassistent

Du schickst deinem Telegram-Bot eine Sprachnachricht, zum Beispiel:

> „Ruf beim Restaurant Da Mario in Köln an und reservier einen Tisch für zwei Personen heute um 17 Uhr.“

Der Assistent sucht die Nummer heraus und fragt dich, ob er anrufen soll. Dann ruft er über deine
FRITZ!Box an, führt das Gespräch auf Deutsch und schickt dir danach einen Bericht samt Gesprächsprotokoll.
Auf Wunsch nimmt er auch Anrufe auf deiner Festnetznummer an und schickt dir eine Zusammenfassung.

**Kosten:** keine Gebühren. Die Anrufe laufen über deine Festnetz-Flatrate. Die KI nutzt das kostenlose
Kontingent von Groq, die Stimme (Piper) läuft auf deinem Laptop. Es fällt nur Strom für den Laptop an.
Anrufe auf Handynummern sind je nach Tarif nicht in jeder Festnetz-Flatrate enthalten.

## Wie es funktioniert

```
Telegram (Sprachnachricht) → Laptop: Assistent ─┬─ Groq: Sprache erkennen + Gespräch führen (kostenlos)
                                                 ├─ Piper: Sprachausgabe (lokal)
                                                 └─ Asterisk ── FRITZ!Box ── Telefonnetz
```

- Der Assistent stellt sich am Telefon immer als KI vor (EU AI Act).
- Es wird kein Ton aufgezeichnet, nur ein Text-Protokoll.
- Vor jedem Anruf musst du in Telegram auf „Anrufen“ tippen.
- Notrufe, Sonder- und Auslandsnummern wählt er nie.
- Nur dein eigener Telegram-Chat kann ihn steuern.

---

## Schritt 1: Telegram-Bot anlegen

1. In Telegram **@BotFather** suchen (blauer Haken), **Starten** tippen, `/newbot` schreiben.
2. Einen Namen eingeben (z. B. `Mein Assistent`), dann einen Benutzernamen, der auf `bot` endet.
3. Den **Token** (`123456789:ABC…`) notieren und geheim halten.

## Schritt 2: Kostenloses Groq-Konto

1. **console.groq.com** öffnen und anmelden. Eine Kreditkarte ist nicht nötig.
2. **API Keys → Create API Key**, dann den Schlüssel (`gsk_…`) sofort kopieren.

## Schritt 3: IP-Telefon in der FRITZ!Box

1. **http://fritz.box** öffnen → **Telefonie → Telefoniegeräte → Neues Gerät einrichten**.
2. **Telefon (mit und ohne Anrufbeantworter)** → **LAN/WLAN (IP-Telefon)**, Name `KI-Assistent`.
3. **Benutzername** (z. B. `kiassistent`) und ein langes **Kennwort** festlegen. Bitte nur Buchstaben und
   Ziffern verwenden. „Anmeldung aus dem Internet“ **nicht** erlauben.
4. Für ausgehende und ankommende Gespräche deine Festnetznummer wählen und die Einrichtung abschließen.

## Schritt 4: Software auf dem Laptop starten

Die Anleitung gilt für **Linux** (z. B. Ubuntu oder Linux Mint). Der Laptop muss per LAN oder WLAN mit
der FRITZ!Box verbunden sein; ein LAN-Kabel ist für die Gesprächsqualität besser.

**4.0 Nur wenn auf dem Gerät noch Windows läuft: Linux Mint installieren.** Dabei werden Windows und
**alle Daten auf dem Gerät gelöscht**. Sichere vorher, was du behalten willst. Du brauchst einen
USB-Stick mit mindestens 8 GB; auch dessen Inhalt wird gelöscht.

1. Unter Windows **linuxmint.com** öffnen → **Download** → die aktuelle Version **Cinnamon Edition**
   herunterladen (eine `.iso`-Datei, ca. 3 GB).
2. **rufus.ie** öffnen, Rufus herunterladen und starten. USB-Stick einstecken, bei **Laufwerk** den Stick
   wählen, bei **Startart** auf **AUSWAHL** klicken und die `.iso`-Datei wählen → **START**. Rückfragen mit
   **OK** bestätigen (ISO-Abbild-Modus).
3. Vom Stick starten: In Windows **Einstellungen → System → Wiederherstellung → Erweiterter Start →
   Jetzt neu starten**, dann **Ein Gerät verwenden** → den USB-Stick wählen.
4. Linux Mint startet zum Ausprobieren. Doppelklick auf **Install Linux Mint** auf dem Schreibtisch:
   Sprache **Deutsch**, Tastatur **German**, dann **Festplatte löschen und Linux Mint installieren**,
   Zeitzone **Berlin**, Name, Benutzername und Passwort festlegen.
5. Nach der Installation den Stick abziehen und neu starten. Danach in der Aktualisierungsverwaltung
   (Schild-Symbol unten rechts) alle Updates installieren.
6. Damit das Gerät nie einschläft: **Menü → Einstellungen → Energieverwaltung** → Ruhezustand **Nie**;
   bei einem Laptop zusätzlich „Beim Zuklappen des Deckels“ → **Nichts tun**.
7. Ein Terminal öffnest du mit **Strg + Alt + T**. Dort geht es mit 4.1 weiter.

**4.1 Docker installieren** (einmalig, im Terminal):

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

Danach einmal ab- und wieder anmelden.

**4.2 Programm herunterladen:**

```bash
sudo apt install -y git
git clone -b claude/gracious-sagan-dus97i https://github.com/maxim7578/Maximilian.git
cd Maximilian/telefon-assistent
```

**4.3 Einstellungen eintragen:**

```bash
cp .env.beispiel .env
nano .env
```

Trag Token, Groq-Schlüssel, FRITZ!Box-Benutzer und -Kennwort sowie deinen Namen ein. Bei `ARI_KENNWORT`
denkst du dir ein beliebiges langes Passwort aus. `TELEGRAM_CHAT_ID` bleibt vorerst leer.
Speichern mit `Strg+O`, `Enter`, beenden mit `Strg+X`.

**4.4 Starten:**

```bash
docker compose up -d --build
```

Beim ersten Mal dauert das einige Minuten.

**4.5 Chat-ID eintragen:** Schick deinem Bot in Telegram `/start`. Er antwortet mit deiner Chat-ID.
Trag sie in `.env` bei `TELEGRAM_CHAT_ID` ein und starte neu:

```bash
docker compose up -d --force-recreate
```

Der Bot meldet sich mit „✅ Dein Telefonassistent ist gestartet.“

**4.6 Prüfen:** In der FRITZ!Box sollte bei **Telefonie → Telefoniegeräte** jetzt **KI-Assistent** grün
bzw. „angemeldet“ sein. In Telegram zeigt `/status`, ob alles läuft.

**4.7 Laptop wach halten:** Stell in den Energieeinstellungen ein, dass der Laptop nie in den Ruhezustand
geht, auch nicht bei zugeklapptem Deckel. Nach einem Neustart startet der Assistent von selbst.

---

## Benutzung

| Du schickst | Der Assistent |
|---|---|
| Sprachnachricht oder Text mit einem Auftrag | versteht ihn, fragt bei Unklarheiten nach, sucht die Nummer und fragt „Soll ich anrufen?“ |
| `/merken Da Mario: 0221 123456` | speichert die Nummer für spätere Aufträge |
| `/auflegen` | beendet den laufenden Anruf sofort |
| `/status` | zeigt, ob alles läuft |
| `/abbrechen` | verwirft eine offene Rückfrage |

Findet der Assistent keine Nummer (die Suche läuft über OpenStreetMap), schick ihm einfach die Nummer.

**Eingehende Anrufe annehmen:** In `.env` `EINGEHENDE_ANRUFE=an` setzen und
`docker compose up -d --force-recreate` ausführen. Dann nimmt der Assistent Anrufe auf deiner
Festnetznummer an, fragt nach Name, Anliegen und Rückrufnummer und schickt dir die Notiz in Telegram.
Klingelt eines deiner anderen Telefone und du gehst schneller ran, hast du das Gespräch.

## Wenn etwas nicht klappt

- **Protokoll ansehen:** `docker compose logs -f assistent` bzw. `docker compose logs -f asterisk`
- **FRITZ!Box-Anmeldung prüfen:** `docker compose exec asterisk asterisk -rx "pjsip show registrations"`.
  Dort sollte `Registered` stehen. Wenn nicht: Benutzername und Kennwort in `.env` mit der FRITZ!Box
  vergleichen. `FRITZBOX_ADRESSE` ist meist `192.168.178.1`.
- **Anruf kommt nicht durch:** Prüf in der FRITZ!Box, ob dem IP-Telefon eine Rufnummer für ausgehende
  Gespräche zugewiesen ist.
- **Kein Ton oder nur in eine Richtung:** Die Firewall des Laptops muss UDP-Port 5060 und die Ports
  10000–10100 im Heimnetz erlauben (`sudo ufw allow 5060/udp` und `sudo ufw allow 10000:10100/udp`).
- **Groq-Limit erreicht:** Das kostenlose Kontingent hat Tageslimits. Für ein paar Anrufe am Tag reicht es
  gut. Aktuelle Limits: console.groq.com → Settings → Limits.

## Grenzen

- Die Stimme klingt erkennbar künstlich, und Antworten kommen mit ungefähr 1–2 Sekunden Verzögerung.
  Manche Gesprächspartner legen bei KI-Anrufen auf.
- Die kostenlosen Kontingente von Groq können sich ändern.
- Was dein Gesprächspartner sagt, wird zur Spracherkennung an Groq geschickt.
- Läuft nur auf Linux. Docker Desktop unter Windows oder macOS unterstützt das hier nötige Host-Netzwerk
  nicht zuverlässig. Auf einem übrigen Windows-PC installiert man am besten Linux Mint (Schritt 4.0).

## Entwicklung

```bash
pip install -r requirements.txt pytest pytest-asyncio websockets
python -m pytest
```
