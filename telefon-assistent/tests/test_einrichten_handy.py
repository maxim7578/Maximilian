"""einrichten-handy.sh: Chat-ID nur nach Bestätigung übernehmen, nie einfach die letzte."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SKRIPT = Path(__file__).parent.parent / "einrichten-handy.sh"


def nachricht(chat_id, vorname, benutzer=None, art="private", titel=None):
    von = {"id": chat_id, "first_name": vorname}
    if benutzer:
        von["username"] = benutzer
    chat = {"id": chat_id, "type": art}
    if titel:
        chat["title"] = titel
    return {"update_id": 1, "message": {"chat": chat, "from": von, "text": "/start"}}


def bash(befehl, eingabe="", stdin=""):
    """Lädt nur die Funktionen des Skripts (ohne die Einrichtung zu starten).

    Die Antworten auf die Fragen kommen aus der Datei `eingabe` statt von der Tastatur.
    """
    env = {**os.environ, "PATH": f"{Path(sys.executable).parent}:{os.environ['PATH']}",
           "EINRICHTEN_NUR_LADEN": "1"}
    return subprocess.run(["bash", "-c", f'source "{SKRIPT}"; exec 3< "$1"; {befehl}', "bash",
                           eingabe or os.devnull], input=stdin, env=env, check=False,
                          capture_output=True, text=True, timeout=30)


def absender(updates):
    ergebnis = bash("absender_lesen", stdin=json.dumps({"ok": True, "result": updates}))
    assert ergebnis.returncode == 0, ergebnis.stderr
    return ergebnis.stdout.splitlines()


def test_absender_mit_name_und_benutzername():
    zeilen = absender([nachricht(111, "Max", "maxi"), nachricht(111, "Max", "maxi")])
    assert zeilen == ["111\tMax (@maxi)"]


def test_mehrere_absender_werden_alle_gezeigt():
    zeilen = absender([nachricht(111, "Max"), nachricht(222, "Fremd\tTab\nZeile"),
                       nachricht(-333, "Erna", art="group", titel="Familie")])
    assert zeilen == ["111\tMax", "222\tFremd Tab Zeile", "-333\tErna, Gruppe „Familie“"]


def test_kaputte_antwort_ergibt_nichts():
    assert bash("absender_lesen", stdin="kein json").stdout == ""


def waehlen(tmp_path, zeilen, antworten):
    datei = tmp_path / "antworten"
    datei.write_text("".join(f"{a}\n" for a in antworten), encoding="utf-8")
    ergebnis = bash('chat_id_waehlen "$(cat)"; echo "ERGEBNIS=$CHAT_ID"', eingabe=str(datei),
                    stdin="\n".join(zeilen))
    assert ergebnis.returncode == 0, ergebnis.stderr
    return ergebnis.stdout


@pytest.mark.parametrize("antwort, erwartet", [("j", "111"), ("J", "111"), ("n", "")])
def test_ein_absender_muss_bestaetigt_werden(tmp_path, antwort, erwartet):
    ausgabe = waehlen(tmp_path, ["111\tMax (@maxi)"], [antwort])
    assert "Max (@maxi)" in ausgabe and "111" in ausgabe
    assert ausgabe.strip().endswith(f"ERGEBNIS={erwartet}")


def test_bestaetigung_fragt_bei_unsinn_nochmal(tmp_path):
    ausgabe = waehlen(tmp_path, ["111\tMax"], ["vielleicht", "j"])
    assert ausgabe.strip().endswith("ERGEBNIS=111")


@pytest.mark.parametrize("antwort, erwartet", [("2", "222"), ("1", "111"), ("0", "")])
def test_mehrere_absender_auswahl_oder_abbruch(tmp_path, antwort, erwartet):
    ausgabe = waehlen(tmp_path, ["111\tMax", "222\tErna"], [antwort])
    assert "Max" in ausgabe and "Erna" in ausgabe
    assert ausgabe.strip().endswith(f"ERGEBNIS={erwartet}")


def test_auswahl_ausserhalb_der_liste_fragt_nochmal(tmp_path):
    ausgabe = waehlen(tmp_path, ["111\tMax", "222\tErna"], ["7", "2"])
    assert ausgabe.strip().endswith("ERGEBNIS=222")
