#!/usr/bin/env python3
"""Erzeugt echte Übungsvideos mit Trainerin und Trainer aus den Coach-Fotos.

Ablauf pro Übung und Person:
  1. Startbild: Gemini-Bildmodell setzt die Person aus dem Foto in die
     Startposition der Übung (gleiches Gesicht, gleiche Kleidung, Seitenansicht).
  2. Video: Veo animiert das Startbild zur Übungsbewegung (statische Kamera).
  3. Das MP4 wird nach apps/bauchwerk/videos/ geladen und in videos.json eingetragen.

Voraussetzung: Umgebungsvariable GEMINI_API_KEY (oder GOOGLE_API_KEY) mit
aktivierter Abrechnung im Google-Projekt (Veo ist nicht im Gratis-Kontingent).

Aufruf:
  python3 apps/bauchwerk/tools/generate_videos.py --dry-run          # nur Plan zeigen
  python3 apps/bauchwerk/tools/generate_videos.py crunch plank climber
  python3 apps/bauchwerk/tools/generate_videos.py crunch --person frau
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://generativelanguage.googleapis.com/v1beta"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "videos"
PHOTOS = {"frau": ROOT / "coach-frau.webp", "mann": ROOT / "coach-mann.webp"}
WHO = {
    "frau": "the same athletic woman from the photo (same face, same dark ponytail, black cropped tank top, black joggers, black smartwatch)",
    "mann": "the same muscular man from the photo (same face, same short dark hair and beard, black tank top, black joggers, black smartwatch)",
}
SCENE = "in the same modern gym, on a light blue exercise mat, full body visible, camera at hip height, strict side view"
NEGATIVE = "camera movement, zoom, cuts, extra people, extra limbs, distorted hands, text, logos, watermark, bad exercise form"

# Startposition (Bild) und Bewegung (Video) je Übung
EXERCISES = {
    "crunch": {
        "start": "lying on the back, knees bent, feet flat on the mat, hands lightly behind the head, elbows open",
        "move": "performs slow controlled crunches: exhales and curls the shoulder blades off the mat, chin stays a fist away from the chest, "
                "holds briefly, lowers slowly back down. Lower back stays on the mat. Repeats the same movement smoothly for the whole clip.",
    },
    "plank": {
        "start": "in a forearm plank: elbows under the shoulders, forearms on the mat, body in one straight line from head to heels",
        "move": "holds a perfect forearm plank without moving the hips, breathing calmly, slight natural muscle tension visible. "
                "Body stays in one straight line for the whole clip.",
    },
    "climber": {
        "start": "in a high plank: hands under the shoulders, arms straight, body in one straight line",
        "move": "performs mountain climbers at a steady pace: drives one knee toward the chest, returns it and switches legs, "
                "hips stay low and shoulders stay over the hands. Repeats smoothly for the whole clip.",
    },
}


def key():
    k = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not k:
        sys.exit("GEMINI_API_KEY fehlt. Bitte in den Umgebungseinstellungen hinterlegen und eine neue Session starten.")
    return k


def call(method, url, body=None, raw=False, timeout=120):
    req = urllib.request.Request(url, method=method, headers={"x-goog-api-key": key(), "Content-Type": "application/json"},
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"API-Fehler {e.code} bei {url.split('?')[0]}: {e.read().decode(errors='replace')[:600]}")
    return data if raw else json.loads(data)


def pick_models():
    names = []
    url = f"{API}/models?pageSize=200"
    while url:
        res = call("GET", url)
        names += [m["name"].split("/", 1)[1] for m in res.get("models", [])]
        tok = res.get("nextPageToken")
        url = f"{API}/models?pageSize=200&pageToken={tok}" if tok else None
    veo = next((n for pref in ("veo-3.1-fast", "veo-3.1", "veo-3.0-fast", "veo-3") for n in names if n.startswith(pref)), None)
    img = next((n for n in names if "flash-image" in n), None)
    if not veo or not img:
        sys.exit(f"Kein passendes Modell gefunden (Veo: {veo}, Bild: {img}). Verfügbar: {', '.join(names)}")
    return img, veo


def start_frame(img_model, person, ex):
    photo = base64.b64encode(PHOTOS[person].read_bytes()).decode()
    prompt = (f"Photorealistic photo of {WHO[person]} {SCENE}. The person is {EXERCISES[ex]['start']}. "
              "Keep identity, body type, skin tone and outfit exactly as in the reference photo. Natural gym lighting.")
    res = call("POST", f"{API}/models/{img_model}:generateContent", {
        "contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": "image/webp", "data": photo}}]}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "16:9"}},
    })
    for part in res["candidates"][0]["content"]["parts"]:
        data = part.get("inlineData") or part.get("inline_data")
        if data:
            return data["data"], data.get("mimeType") or data.get("mime_type", "image/png")
    sys.exit(f"Bildmodell hat kein Bild geliefert für {ex}/{person}.")


def animate(veo_model, frame_b64, mime, person, ex):
    prompt = (f"{WHO[person].capitalize()} {SCENE}. The person {EXERCISES[ex]['move']} "
              "Static locked-off camera, realistic human motion, correct exercise technique, no sound needed.")
    op = call("POST", f"{API}/models/{veo_model}:predictLongRunning", {
        "instances": [{"prompt": prompt, "image": {"bytesBase64Encoded": frame_b64, "mimeType": mime}}],
        "parameters": {"aspectRatio": "16:9", "negativePrompt": NEGATIVE, "personGeneration": "allow_adult"},
    })
    name = op["name"]
    for _ in range(90):
        time.sleep(10)
        op = call("GET", f"{API}/{name}")
        if op.get("done"):
            break
    else:
        sys.exit(f"Zeitüberschreitung bei {ex}/{person}.")
    if "error" in op:
        sys.exit(f"Veo-Fehler bei {ex}/{person}: {op['error']}")
    samples = op["response"]["generateVideoResponse"].get("generatedSamples") or []
    if not samples:
        sys.exit(f"Veo hat kein Video geliefert bei {ex}/{person} (evtl. Sicherheitsfilter): {json.dumps(op['response'])[:400]}")
    return call("GET", samples[0]["video"]["uri"], raw=True, timeout=300)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("exercises", nargs="*", default=list(EXERCISES), help="Übungs-IDs (Standard: alle mit Prompt)")
    ap.add_argument("--person", choices=["frau", "mann", "beide"], default="beide")
    ap.add_argument("--dry-run", action="store_true", help="Nur anzeigen, was erzeugt würde")
    args = ap.parse_args()
    unknown = [e for e in args.exercises if e not in EXERCISES]
    if unknown:
        sys.exit(f"Kein Prompt für: {', '.join(unknown)}. Vorhanden: {', '.join(EXERCISES)}")
    people = ["frau", "mann"] if args.person == "beide" else [args.person]
    jobs = [(e, p) for e in args.exercises for p in people]
    print(f"{len(jobs)} Clips geplant: " + ", ".join(f"{e}/{p}" for e, p in jobs))
    if args.dry_run:
        return
    img_model, veo_model = pick_models()
    print(f"Bildmodell: {img_model} · Videomodell: {veo_model}")
    OUT.mkdir(exist_ok=True)
    manifest_path = OUT / "videos.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    for ex, person in jobs:
        print(f"→ {ex}/{person}: Startbild …", flush=True)
        frame, mime = start_frame(img_model, person, ex)
        (OUT / f"{ex}-{person}-start.{'png' if 'png' in mime else 'jpg'}").write_bytes(base64.b64decode(frame))
        print(f"→ {ex}/{person}: Video (dauert einige Minuten) …", flush=True)
        mp4 = animate(veo_model, frame, mime, person, ex)
        (OUT / f"{ex}-{person}.mp4").write_bytes(mp4)
        manifest.setdefault(ex, {})[person] = f"videos/{ex}-{person}.mp4"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
        print(f"✓ {ex}/{person}: {len(mp4) // 1024} KB gespeichert")
    print("Fertig. Clips liegen in", OUT)


if __name__ == "__main__":
    main()
