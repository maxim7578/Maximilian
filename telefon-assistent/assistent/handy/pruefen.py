"""Prüft die Verbindung zur FRITZ!Box und findet ihre Adresse.

Aufruf (im Ordner telefon-assistent): python -m assistent.handy.pruefen
"""

import asyncio
import os
import socket
from pathlib import Path

from .__main__ import env_laden
from .sip import Telefon, _zufall


def lokale_ip() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 53))
        return s.getsockname()[0]


def web_erreichbar(ip: str) -> bool:
    try:
        with socket.create_connection((ip, 80), timeout=2):
            return True
    except OSError:
        return False


def sip_antwort(ip: str, port: int = 5060) -> str:
    """Schickt eine SIP-OPTIONS-Anfrage und gibt die erste Antwortzeile zurück ("" = keine Antwort)."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(3)
        s.connect((ip, port))
        eigene_ip, eigener_port = s.getsockname()
        anfrage = (
            f"OPTIONS sip:{ip} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {eigene_ip}:{eigener_port};branch=z9hG4bK{_zufall(12)};rport\r\n"
            f"Max-Forwards: 70\r\nFrom: <sip:pruefung@{eigene_ip}>;tag={_zufall(8)}\r\n"
            f"To: <sip:{ip}>\r\nCall-ID: {_zufall(16)}\r\nCSeq: 1 OPTIONS\r\n"
            f"Contact: <sip:pruefung@{eigene_ip}:{eigener_port}>\r\nContent-Length: 0\r\n\r\n"
        )
        try:
            s.send(anfrage.encode())
            return s.recv(4096).decode(errors="replace").split("\r\n")[0]
        except OSError:
            return ""


async def anmelden_testen(ip: str, port: int, benutzer: str, kennwort: str) -> str:
    telefon = Telefon(ip, benutzer, kennwort, server_port=port, lokaler_port=0)
    await telefon.starten()
    for _ in range(100):
        if telefon.angemeldet or telefon.letzter_fehler:
            break
        await asyncio.sleep(0.1)
    ergebnis = "✅ angemeldet" if telefon.angemeldet else f"❌ {telefon.letzter_fehler or 'keine Antwort'}"
    await telefon.stoppen()
    return ergebnis


def main() -> None:
    env_laden(Path.cwd() / ".env")
    eingetragen = os.getenv("FRITZBOX_ADRESSE", "192.168.178.1")
    adresse, _, port = eingetragen.partition(":")
    port = int(port or 5060)
    benutzer = os.getenv("FRITZBOX_BENUTZER", "")
    kennwort = os.getenv("FRITZBOX_KENNWORT", "")

    ich = lokale_ip()
    print(f"Dieses Handy hat die Adresse: {ich}")
    print(f"Eingetragene FRITZ!Box:        {eingetragen}")
    print(f"Benutzername IP-Telefon:       {benutzer or '(leer!)'}")
    print(f"Kennwort IP-Telefon:           {'(gesetzt, ' + str(len(kennwort)) + ' Zeichen)' if kennwort else '(leer!)'}\n")

    kandidaten = [adresse]
    for ip in (".".join(ich.split(".")[:3] + ["1"]), "192.168.178.1", "192.168.188.1", "192.168.0.1", "192.168.1.1"):
        if ip not in kandidaten:
            kandidaten.append(ip)

    gefunden = ""
    for ip in kandidaten:
        web = web_erreichbar(ip)
        sip = sip_antwort(ip, port)
        print(f"{ip:16} Webseite: {'ja ' if web else 'nein'}  Telefonie (SIP): {sip or 'keine Antwort'}")
        if sip and not gefunden:
            gefunden = ip

    print()
    if not gefunden:
        print("❌ Keine Telefonanlage antwortet. Ist das Handy im WLAN der FRITZ!Box (nicht Gastzugang)?")
        print("   Ist in der FRITZ!Box die Telefonie eingerichtet?")
        return
    if gefunden != adresse:
        print(f"➡️  Die FRITZ!Box antwortet unter {gefunden}, eingetragen ist aber {adresse}.")
        print("   Korrigieren mit diesem Befehl:")
        print(f"   sed -i 's/^FRITZBOX_ADRESSE=.*/FRITZBOX_ADRESSE={gefunden}/' .env\n")
    print(f"Anmeldung als IP-Telefon an {gefunden} wird getestet …")
    ergebnis = asyncio.run(anmelden_testen(gefunden, port, benutzer, kennwort))
    print(ergebnis)
    if "abgelehnt" in ergebnis:
        print("➡️  Benutzername oder Kennwort passen nicht zu den Anmeldedaten des IP-Telefons in der FRITZ!Box.")


if __name__ == "__main__":
    main()
