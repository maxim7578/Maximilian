"""Tests der Sicherheitsschicht: nur Lesebefehle duerfen durch."""

import pytest

from bmw_hu_info.safety import (
    UnsichererBefehlError,
    ist_lesebefehl,
    pruefe_befehl,
)


class TestErlaubteLesebefehle:
    def test_laesst_einfachen_lesebefehl_durch(self):
        assert pruefe_befehl("uname -a") == "uname -a"

    def test_laesst_cat_durch(self):
        assert ist_lesebefehl("cat /proc/cpuinfo")

    def test_laesst_pipe_mit_grep_durch(self):
        assert ist_lesebefehl("dmesg | grep -i error")

    def test_laesst_journalctl_durch(self):
        assert ist_lesebefehl("journalctl -p err -n 200 --no-pager")

    def test_pipe_in_anfuehrungszeichen_wird_nicht_als_trenner_gewertet(self):
        # Regression: '|' innerhalb von Anfuehrungszeichen ist Teil des
        # Arguments, kein Pipe-Trenner.
        assert ist_lesebefehl("dmesg | grep -i -E 'error|fail|warn'")

    def test_verweigert_unbalancierte_anfuehrungszeichen(self):
        with pytest.raises(UnsichererBefehlError):
            pruefe_befehl("grep 'offen")


class TestVerweigerteSchreibbefehle:
    def test_verweigert_rm(self):
        assert not ist_lesebefehl("rm -rf /")

    def test_verweigert_umleitung(self):
        with pytest.raises(UnsichererBefehlError):
            pruefe_befehl("echo kaputt > /etc/wichtig")

    def test_verweigert_befehlskettung_mit_semikolon(self):
        with pytest.raises(UnsichererBefehlError):
            pruefe_befehl("uname -a; rm -rf /")

    def test_verweigert_und_verkettung(self):
        with pytest.raises(UnsichererBefehlError):
            pruefe_befehl("cat x && reboot")

    def test_verweigert_kommandosubstitution(self):
        with pytest.raises(UnsichererBefehlError):
            pruefe_befehl("cat $(reboot)")

    def test_verweigert_sed_in_place(self):
        with pytest.raises(UnsichererBefehlError):
            pruefe_befehl("sed -i s/a/b/ datei")

    def test_verweigert_find_exec(self):
        with pytest.raises(UnsichererBefehlError):
            pruefe_befehl("find / -name x -exec rm {} ;")

    def test_verweigert_platzhalter(self):
        with pytest.raises(UnsichererBefehlError):
            pruefe_befehl("cat <PFAD_ZUR_VIN_DATEI>")

    def test_verweigert_unbekanntes_programm(self):
        assert not ist_lesebefehl("flash_tool --write")

    def test_verweigert_leeren_befehl(self):
        with pytest.raises(UnsichererBefehlError):
            pruefe_befehl("   ")
