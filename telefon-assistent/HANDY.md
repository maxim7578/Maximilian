# Telefonassistent auf dem Android-Handy (z. B. Samsung Galaxy A36)

Ein übriges Android-Handy liegt zu Hause am Ladekabel im WLAN und arbeitet als „Motor“:

- Es meldet sich als IP-Telefon an deiner FRITZ!Box an und telefoniert über deine Festnetz-Flatrate.
- Steuern tust du alles per Telegram, zum Beispiel vom iPhone.

**Zwei Gesprächs-Varianten:**
- **Gemini Live (empfohlen, am menschlichsten):** Ein Google-Modell hört, denkt und spricht in einem. Es
  antwortet fast ohne Pause, betont natürlich und lässt sich unterbrechen wie ein Mensch.
  Kosten: siehe unten.
- **Klassisch (kostenlos):** Groq erkennt die Sprache und denkt, die Stimme kommt extra. Zwischen Frage
  und Antwort liegen ungefähr 1–2 Sekunden.

Ist Gemini einmal nicht erreichbar, etwa weil ein Limit erreicht ist, übernimmt für diesen Anruf
automatisch die klassische Variante. Du bekommst dann einen Hinweis in Telegram.

**Stimme (klassische Variante):** Standardmäßig spricht der Assistent mit einer sehr natürlichen Microsoft-Neural-Stimme
(„Seraphina“, auswählbar mit `/stimmen`). Fällt sie aus, übernimmt automatisch die lokale Piper-Stimme. Die klingt künstlicher, läuft
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

4. *Für Gemini Live (optional, empfohlen):* **aistudio.google.com** öffnen, mit deinem Google-Konto
   anmelden → **Get API key** bzw. **API-Schlüssel abrufen** → **Schlüssel erstellen** und aufschreiben.
   Das Einrichtungsskript fragt danach; lässt du es leer, läuft alles klassisch.

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
   apt update && yes | apt full-upgrade && pkg install -y curl && curl -sL https://raw.githubusercontent.com/maxim7578/Maximilian/claude/gracious-sagan-dus97i/telefon-assistent/einrichten-handy.sh | bash
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
6. **Ton klingt nach einer Weile roboterhaft oder langsam?** Dann bremst Android das Handy bei
   ausgeschaltetem Bildschirm aus. Abhilfe: Entwickleroptionen freischalten (siehe Punkt 7) und dort
   „**Aktiv lassen**“ einschalten. Dann bleibt der Bildschirm beim Laden an (ganz dunkel stellen).
   Der Bericht nach jedem Anruf warnt, wenn der Ton gestockt hat.
7. *Falls der Assistent trotzdem nach einiger Zeit verschwindet:* **Einstellungen → Telefoninfo →
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
| `/status` | zeigt, ob die FRITZ!Box-Anmeldung steht und welche Stimme spricht |
| `/stimmen` | Stimmen anhören und auswählen |
| `/abbrechen` | offene Rückfrage verwerfen |

**Gemini Live nachträglich ein- oder ausschalten:** In `.env` `GESPRAECH=gemini` bzw.
`GESPRAECH=klassisch` setzen; für Gemini zusätzlich `GEMINI_API_KEY` eintragen. Danach den Assistenten
neu starten. Die Gemini-Stimme wechselst du mit `GEMINI_STIMME`, z. B. `Aoede` oder `Puck`. Am besten
probierst du ein paar aus, indem der Assistent dich selbst anruft.

**Was kostet Gemini Live?**
- Google rechnet nach Gesprächsdauer ab. Laut Vergleichsseiten kostet es grob 2 Cent pro Minute, bei
  30 Anrufen à 2 Minuten also etwa 1–2 $ im Monat.
- Es gibt ein begrenztes Gratis-Kontingent. Ob es in Deutschland für Gemini Live gilt, ist nicht sicher.
- Kommt beim ersten Anruf die Meldung „Gemini Live ist gerade nicht verfügbar“, musst du in AI Studio
  unter **Billing** ein Zahlungsmittel hinterlegen. Dort siehst du auch die aktuellen Preise und
  kannst ein Ausgabenlimit festlegen.

**Andere Stimme (klassisch):** Schick dem Bot `/stimmen`. Du bekommst von jeder Microsoft-Stimme eine
Hörprobe in Telefonqualität und tippst unter deiner Lieblingsstimme auf **„… nehmen“**. Der Assistent
nennt den Vornamen nur, wenn jemand danach fragt.
Klingt es sehr künstlich, zeigt `/status`, ob gerade die Ersatzstimme Piper spricht, weil Microsoft
nicht erreichbar war. Nach fünf Minuten probiert der Assistent Microsoft automatisch wieder.
Zu langsam oder zu schnell? In `.env` z. B. `MICROSOFT_TEMPO=+15%` (schneller) oder `-5%` eintragen.

**Eingehende Anrufe annehmen:** In `.env` `EINGEHENDE_ANRUFE=an` setzen und neu starten.

## Wenn etwas nicht klappt

- **Protokoll ansehen:** In Termux `tail -f ~/telefon-daten/assistent.log` eingeben (beenden mit Strg+C;
  die Strg-Taste ist in der Leiste über der Tastatur).
- **„FRITZ!Box-Anmeldung ❌“:**
  - Benutzername und Kennwort neu eintragen und gleich testen:
    `~/Maximilian/telefon-assistent/fritzbox-zugang.sh`. Der Benutzername steht in der FRITZ!Box
    beim Gerät im Reiter **„Anmeldedaten“**, nicht im Feld „Name“.
  - Prüfe, ob das Handy im WLAN der FRITZ!Box ist.
  - Prüfe, ob das IP-Telefon in der FRITZ!Box eingerichtet ist.
- **Neu starten:** Termux öffnen, mit Strg+C stoppen, dann `./start-handy.sh`.
- **Update holen:** Das Einrichtungsskript aus Teil C einfach noch einmal ausführen. Deine `.env` bleibt
  erhalten.

## Grenzen

- Klassisch kommen Antworten mit ungefähr 1–2 Sekunden Verzögerung, mit Gemini Live deutlich schneller.
  Manche Gesprächspartner legen bei KI-Anrufen auf.
- Was dein Gesprächspartner sagt, geht an Google (Gemini Live) bzw. an Groq (klassisch). Bei der
  klassischen Variante gehen die Antworten zum Vorlesen an Microsoft.
- Es wird kein Ton gespeichert, nur ein Text-Protokoll. Der Assistent sagt immer, dass er eine KI ist.
