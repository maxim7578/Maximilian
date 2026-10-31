import json
import stat

from bmw_cardata.usage import DAILY_LIMIT, Usage, load_usage, record_call, save_usage, usage_path

TAG = 24 * 60 * 60


def test_neue_zählung_ist_leer_und_hat_das_volle_kontingent():
    assert Usage().remaining(now=1000.0) == DAILY_LIMIT == 50


def test_abrufe_der_letzten_24_stunden_werden_gezählt():
    zaehlung = Usage().record(100.0).record(200.0)
    assert zaehlung.remaining(now=300.0) == 48
    assert zaehlung.recent(now=300.0) == (100.0, 200.0)


def test_ältere_abrufe_fallen_aus_dem_fenster_und_werden_verworfen():
    zaehlung = Usage().record(0.0).record(TAG + 10.0)
    assert zaehlung.calls == (TAG + 10.0,)
    assert zaehlung.remaining(now=TAG + 20.0) == 49


def test_zählung_ist_unveränderlich():
    original = Usage()
    original.record(5.0)
    assert original.calls == ()


def test_nächster_freier_abruf_erst_wenn_das_limit_erreicht_ist():
    voll = Usage(tuple(float(t) for t in range(100, 100 + DAILY_LIMIT)))
    assert voll.remaining(now=200.0) == 0
    assert voll.next_free_at(now=200.0) == 100.0 + TAG
    assert Usage((1.0,)).next_free_at(now=2.0) is None


def test_zählung_liegt_neben_der_anmeldedatei(tmp_path):
    assert usage_path(tmp_path / "state.json") == tmp_path / "abrufe.json"


def test_zählung_wird_gespeichert_und_geladen(tmp_path):
    pfad = tmp_path / "unter" / "abrufe.json"
    save_usage(pfad, Usage((1.0, 2.0)))
    assert load_usage(pfad) == Usage((1.0, 2.0))
    assert stat.S_IMODE(pfad.stat().st_mode) == 0o600


def test_fehlende_oder_beschädigte_zählung_beginnt_von_vorn(tmp_path):
    pfad = tmp_path / "abrufe.json"
    assert load_usage(pfad) == Usage()
    for inhalt in ["kein json", json.dumps({"abrufe": ["x"]}), json.dumps([1])]:
        pfad.write_text(inhalt)
        assert load_usage(pfad) == Usage()


def test_abruf_erfassen_schreibt_sofort_in_die_datei(tmp_path):
    pfad = tmp_path / "abrufe.json"
    record_call(pfad, now=10.0)
    record_call(pfad, now=20.0)
    assert load_usage(pfad).calls == (10.0, 20.0)
