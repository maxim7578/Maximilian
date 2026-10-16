# Fahrer App – Präsentationsvideo (Arbeitsstand)

Quelle: `assets/source.pptx` (27 Folien, Rica Service GmbH).

## Fertig
- **2-Minuten-Fassung** (`hyperframes/index.html`): 20 Folien, Zoom + Überblendungen,
  Fortschrittsbalken; Platzhalter auf Folie 1 und 26 ausgeblendet. Folienplan:
  `artifacts/scene_plan.json`. Kurzer Sprechertext: `artifacts/narration.json`.
- **Vorlese-Fassung** (`hyperframes-read/index.html`): gleiche 20 Folien, jede Folie so lang,
  wie ihr Text gesprochen dauert. Vorlesetext je Folie: `artifacts/slide_reading.json`
  (für lokale Stimmen ohne Ziffern/Abkürzungen geschrieben). Timing: `artifacts/scene_plan_read.json`.
  `hyperframes-read/assets` ist eine Kopie von `hyperframes/assets` und nicht eingecheckt:
  vor dem Rendern `cp -r hyperframes/assets hyperframes-read/`.

## Entscheidung des Nutzers
Lokale Piper-/CSS10-Stimmen gefallen nicht (zu langweilig). Gewünscht: **junge, sehr sanfte,
sehr freundliche Frauenstimme von ElevenLabs**, die die **Folientexte vorliest**.

## Stimmen-Optionen
- **Gemini-TTS (bevorzugt, falls `GEMINI_API_KEY` gesetzt):** `generativelanguage.googleapis.com` ist ohne
  Freigabe erreichbar. Tool `tools/audio/gemini_tts.py` (liest `GOOGLE_API_KEY` oder `GEMINI_API_KEY`).
  Stil per Anweisung steuerbar („sanft, warm, freundlich, junge Frau“). Kandidaten-Stimmen zum Vergleichen:
  Leda, Aoede, Achernar, Sulafat, Vindemiatrix, Kore.
- **ElevenLabs:** braucht `ELEVENLABS_API_KEY` und Freigabe von `api.elevenlabs.io`.

## Nächste Schritte (neue Sitzung mit Gemini- oder ElevenLabs-Schlüssel)
1. Junge, sanfte, freundliche deutsche Frauenstimmen beim verfügbaren Dienst suchen, Hörproben als Artifact-Seite zeigen,
   Nutzer wählen lassen.
2. Folientexte je Folie mit der gewählten Stimme erzeugen (Text darf jetzt normal mit Zahlen sein,
   Vorlage: `artifacts/slide_reading.json` bzw. Folientexte aus `source.pptx`).
3. Foliendauer = Sprechzeit + ca. 1,5 s; `hyperframes-read/index.html` daraus neu erzeugen
   (gleiche Struktur wie jetzt), rendern mit `tools/video/hyperframes_compose.py`
   (operation `render_existing`), Ton per ffmpeg dazumischen.
4. Für den Nutzer: Video auf einer Artifact-Seite zum Ansehen + MP4 zum Herunterladen
   (der Nutzer kann Videos im Chat nicht abspielen).
