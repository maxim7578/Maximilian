"""Startskript des Containers: Besitz korrigieren, dann ohne root-Rechte weitermachen.

Läuft echt (mit setpriv), wenn der Test als root läuft und es UID 1000 gibt; Docker wird nicht gebraucht.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SKRIPT = Path(__file__).parent.parent / "container-start.sh"

pytestmark = pytest.mark.skipif(
    not hasattr(os, "geteuid")
    or os.geteuid() != 0
    or shutil.which("setpriv") is None
    or subprocess.run(["getent", "passwd", "1000"], capture_output=True, check=False).returncode != 0,
    reason="braucht root, setpriv und einen Benutzer mit UID 1000",
)


def starten(tmp_path, *befehl, daten=None, asterisk=None, als=None):
    env = {
        "PATH": os.environ["PATH"],
        "DATEN_ORDNER": str(daten or tmp_path / "gibt-es-nicht"),
        "ASTERISK_ORDNER": str(asterisk or tmp_path / "gibt-es-auch-nicht"),
    }
    vorne = ["setpriv", f"--reuid={als}", f"--regid={als}", "--clear-groups"] if als else []
    return subprocess.run([*vorne, "sh", str(SKRIPT), *befehl], env=env, capture_output=True, text=True, check=False,
                          timeout=30)


def test_kommando_laeuft_nicht_als_root(tmp_path):
    ergebnis = starten(tmp_path, "sh", "-c", 'echo "$(id -u):$(id -g) $HOME"')
    assert ergebnis.returncode == 0, ergebnis.stderr
    assert ergebnis.stdout.strip() == "1000:1000 /home/assistent"


def test_root_eigene_daten_werden_uebergeben(tmp_path):
    """Bestehende Installationen: ./daten gehört bisher root."""
    daten = tmp_path / "daten"
    (daten / "piper").mkdir(parents=True)
    (daten / "kontakte.json").write_text("{}", encoding="utf-8")
    ergebnis = starten(tmp_path, "true", daten=daten)
    assert ergebnis.returncode == 0, ergebnis.stderr
    for pfad in (daten, daten / "piper", daten / "kontakte.json"):
        assert (pfad.stat().st_uid, pfad.stat().st_gid) == (1000, 1000), pfad


def test_asterisk_ordner_wird_angelegt_und_uebergeben(tmp_path):
    asterisk = tmp_path / "asterisk"
    (asterisk / "vorlagen").mkdir(parents=True)
    alt = asterisk / "etc"
    alt.mkdir()
    (alt / "pjsip.conf").write_text("alt", encoding="utf-8")
    ergebnis = starten(tmp_path, "true", asterisk=asterisk)
    assert ergebnis.returncode == 0, ergebnis.stderr
    for pfad in (alt, alt / "pjsip.conf"):
        assert (pfad.stat().st_uid, pfad.stat().st_gid) == (1000, 1000), pfad
    assert (asterisk / "vorlagen").stat().st_uid == 0, "Vorlagen bleiben unverändert"

    neu = tmp_path / "neu"
    neu.mkdir()
    assert starten(tmp_path, "true", asterisk=neu).returncode == 0
    assert (neu / "etc").is_dir() and (neu / "etc").stat().st_uid == 1000


def test_besitz_wird_nur_bei_bedarf_geaendert(tmp_path):
    daten = tmp_path / "daten"
    daten.mkdir()
    datei = daten / "kontakte.json"
    datei.write_text("{}", encoding="utf-8")
    for pfad in (daten, datei):
        os.chown(pfad, 1000, 1000)
    vorher = datei.stat().st_ctime_ns
    assert starten(tmp_path, "true", daten=daten).returncode == 0
    assert datei.stat().st_ctime_ns == vorher


def test_ohne_root_wird_das_kommando_direkt_gestartet(tmp_path):
    ergebnis = starten(tmp_path, "id", "-u", als=1000)
    assert ergebnis.returncode == 0, ergebnis.stderr
    assert ergebnis.stdout.strip() == "1000"


def test_fehler_im_kommando_wird_weitergegeben(tmp_path):
    assert starten(tmp_path, "sh", "-c", "exit 3").returncode == 3
