# Telefonassistent auf dem Android-Handy (z. B. Samsung Galaxy A36)

Ein übriges Android-Handy liegt zu Hause am Ladekabel im WLAN und arbeitet als „Motor“:

- Es meldet sich als IP-Telefon an deiner FRITZ!Box an und telefoniert über deine Festnetz-Flatrate.
- Steuern tust du alles per Telegram, zum Beispiel vom iPhone.

**Stimme:** Standardmäßig spricht der Assistent mit einer sehr natürlichen Microsoft-Neural-Stimme
(„Katja“). Fällt sie aus, übernimmt automatisch die lokale Piper-Stimme. Die klingt künstlicher, läuft
aber ohne Internet.

**Kosten:**
- keine Gebühren: Anrufe über deine Flatrate, Spracherkennung und KI über das kostenlose Groq-Kontingent.
- Die Microsoft-Stimme nutzt den kostenlosen Vorlesedienst des Edge-Browsers. Den bietet Microsoft nicht
  offiziell dafür an, er kann sich also jederzeit ändern. Dann springt Piper ein.

---

## Teil A: Vorbereitung (einmalig)

1. **Telegram-Bot anlegen:** In Telegram **@BotFather** öffnen, `/newbot` schreiben, Namen und
   Benutzernamen (endet auf `bot`) vergeben. Den **Token** aufschreiben.
2. **Groq-Konto:** **console.groq.com** öffnen und anmelden (ohne Kreditkarte). Dann **API Keys → Create
   API Key** und den Schlüssel (`gsk_…`) aufschreiben.
3. **FRITZ!Box:** **http://fritz.box** öffnen → **Telefonie → Telefoniegeräte → Neues Gerät einrichten**
   → **Telefon** → **LAN/WLAN (IP-Telefon)**, Name `KI-Assistent`.
   - Benutzername (z. B. `kiassistent`) und Kennwort festlegen und aufschreiben.
   - Als ausgehende und ankommende Rufnummer deine Festnetznummer wählen.

## Teil B: Apps auf dem Handy installieren

1. Öffne auf dem Samsung im Browser **f-droid.org** und tippe auf **F-Droid herunterladen**.
2. Öffne die heruntergeladene Datei. Wenn Android fragt, erlaube **Installation aus dieser Quelle** und
   installiere F-Droid.
3. Such in F-Droid **Termux** und installiere es. Dann such **Termux:Boot** und installiere es ebenfalls.
   *Wichtig:* beide aus F-Droid nehmen, nicht Termux aus dem Play Store.
4. Öffne **Termux:Boot** einmal. Das schaltet den Autostart frei.

## Teil C: Assistent einrichten

1. Öffne **Termux**.
2. Tippe diesen Befehl ein. Du kannst ihn dir auch per Telegram ans Samsung schicken, dort kopieren und in
   Termux lange tippen → **Einfügen**.

   ```
   pkg install -y curl && curl -sL https://raw.githubusercontent.com/maxim7578/Maximilian/claude/gracious-sagan-dus97i/telefon-assistent/einrichten-handy.sh | bash
   ```

3. Das Skript installiert alles. Das dauert einige Minuten. Danach fragt es nach:
   - Telegram-Token, Groq-Schlüssel, FRITZ!Box-Benutzername und -Kennwort,
   - deinem Namen (wie im Satz „der digitale Assistent von **Herrn Mustermann**“) und Wohnort.
4. Dann bittet es dich, deinem Bot in Telegram **/start** zu schicken. Die Chat-ID trägt es selbst ein.
5. Starte den Assistenten:

   ```
   cd ~/Maximilian/telefon-assistent && ./start-handy.sh
   ```

   In Telegram kommt: „✅ Dein Telefonassistent ist gestartet. FRITZ!Box-Anmeldung: ✅“.

Termux kannst du danach einfach im Hintergrund lassen. Nach einem Neustart des Handys startet der
Assistent von selbst.

## Teil D: Samsung so einstellen, dass es dauerhaft läuft

Samsung beendet Hintergrund-Apps gern zum Akkusparen. Das schaltest du für Termux ab. Je nach
One-UI-Version heißen die Menüpunkte leicht anders; die Suche (Lupe) in den Einstellungen hilft.

1. **Einstellungen → Akku → Hintergrundnutzungsgrenzen → Nie im Standby-Modus befindliche Apps** → **+**
   → **Termux** und **Termux:Boot** hinzufügen.
2. **Einstellungen → Apps → Termux → Akku** → **Nicht eingeschränkt**. Dasselbe für **Termux:Boot**.
3. **Akku schonen:** **Einstellungen → Akku → Akkuschutz** einschalten und **Maximal** wählen. Das Handy
   lädt dann nur bis 80 %, das schont den Akku im Dauerbetrieb.
4. Das Handy bleibt am **Ladekabel** und im **WLAN**.
5. *Empfohlen:* In der FRITZ!Box unter **Heimnetz → Netzwerk** beim Samsung „**Diesem Netzwerkgerät immer
   die gleiche IPv4-Adresse zuweisen**“ einschalten.
6. *Falls der Assistent trotzdem nach einiger Zeit verschwindet:* **Einstellungen → Telefoninfo →
   Softwareinformationen** → 7× auf **Buildnummer** tippen. Dann unter **Einstellungen →
   Entwickleroptionen** „**Einschränkungen für untergeordnete Prozesse deaktivieren**“ einschalten.

## Benutzung

Schick deinem Bot eine Sprachnachricht, zum Beispiel:

> „Ruf beim Restaurant Da Mario in Köln an und reservier einen Tisch für zwei Personen heute um 17 Uhr.“

Der Ablauf:
1. Der Bot fragt nach, wenn etwas fehlt.
2. Er sucht die Nummer und fragt „Soll ich anrufen?“.
3. Nach deinem Tipp auf **📞 Anrufen** ruft er an.
4. Danach schickt er dir einen Bericht mit Gesprächsprotokoll.

| Befehl | Wirkung |
|---|---|
| `/merken Da Mario: 0221 123456` | Nummer für später speichern |
| `/auflegen` | laufenden Anruf beenden |
| `/status` | zeigt, ob die FRITZ!Box-Anmeldung steht |
| `/abbrechen` | offene Rückfrage verwerfen |

**Andere Stimme:** In `~/Maximilian/telefon-assistent/.env` bei `MICROSOFT_STIMME` z. B.
`de-DE-ConradNeural` (männlich) oder `de-DE-SeraphinaMultilingualNeural` eintragen. Danach den
Assistenten neu starten.

**Eingehende Anrufe annehmen:** In `.env` `EINGEHENDE_ANRUFE=an` setzen und neu starten.

## Wenn etwas nicht klappt

- **Protokoll ansehen:** In Termux `tail -f ~/telefon-daten/assistent.log` eingeben (beenden mit Strg+C;
  die Strg-Taste ist in der Leiste über der Tastatur).
- **„FRITZ!Box-Anmeldung ❌“:**
  - Prüfe Benutzername und Kennwort in `.env`; bearbeiten mit `nano ~/Maximilian/telefon-assistent/.env`.
  - Prüfe, ob das Handy im WLAN der FRITZ!Box ist.
  - Prüfe, ob das IP-Telefon in der FRITZ!Box eingerichtet ist.
- **Neu starten:** Termux öffnen, mit Strg+C stoppen, dann `./start-handy.sh`.
- **Update holen:** Das Einrichtungsskript aus Teil C einfach noch einmal ausführen. Deine `.env` bleibt
  erhalten.

## Grenzen

- Antworten kommen mit ungefähr 1–2 Sekunden Verzögerung. Manche Gesprächspartner legen bei KI-Anrufen auf.
- Was dein Gesprächspartner sagt, geht zur Spracherkennung an Groq. Gesprochene Antworten gehen an
  Microsoft, solange die Microsoft-Stimme aktiv ist.
- Es wird kein Ton gespeichert, nur ein Text-Protokoll. Der Assistent sagt immer, dass er eine KI ist.
