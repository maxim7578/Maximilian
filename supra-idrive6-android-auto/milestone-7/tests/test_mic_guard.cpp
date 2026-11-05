// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Required Notice: Copyright (c) 2026 nanaisu - NBT-AAD (https://github.com/Sq00ky/Supra-iDrive6-Android-Auto)
// Host-Test für src/mic_guard.hpp: Das Automikrofon nur für Sitzungen, deren Telefon vorher über Bluetooth den
// WLAN-Handshake gemacht hat (oder per USB-Kabel verbunden ist).
#include "mic_guard.hpp"
#include <stdio.h>
using namespace nbt;

static int g_fehler = 0;
#define PRUEFE(name, cond) do { \
    if (cond) printf("[OK]     %s\n", name); \
    else { printf("[FEHLER] %s (Zeile %d: %s)\n", name, __LINE__, #cond); ++g_fehler; } } while (0)

int main() {
    printf("test_mic_guard: Mikrofon nur für über Bluetooth gekoppelte Sitzungen\n");
    const bool drahtlos = true;

    {
        MicGuard g;
        g.sessionStarted(kTransportTcp, drahtlos, true, 100);
        PRUEFE("WLAN-Sitzung ohne Bluetooth-Handshake bekommt kein Mikrofon", !g.micAllowed());
        PRUEFE("Grund wird genannt", g.reason() != NULL && g.reason()[0] != 0);
    }
    {
        MicGuard g;
        g.bluetoothHandshakeOk(100);
        g.sessionStarted(kTransportTcp, drahtlos, true, 110);
        PRUEFE("WLAN-Sitzung kurz nach dem Handshake bekommt das Mikrofon", g.micAllowed());
    }
    {
        MicGuard g;
        g.bluetoothHandshakeOk(100);
        g.sessionStarted(kTransportTcp, drahtlos, true, 100 + MicGuard::kWindowSec);
        PRUEFE("Genau am Ende des Zeitfensters noch erlaubt", g.micAllowed());
        g.sessionStarted(kTransportTcp, drahtlos, true, 101 + MicGuard::kWindowSec);
        PRUEFE("Nach dem Zeitfenster verweigert", !g.micAllowed());
    }
    {
        // Der Wireless-Thread wartet höchstens 90 s auf die TCP-Verbindung und schließt danach den Bluetooth-Link;
        // eine neue Sitzung braucht immer einen neuen Handshake. Das Fenster zählt daher ab dem Handshake.
        MicGuard g;
        g.bluetoothHandshakeOk(100);
        g.sessionStarted(kTransportTcp, drahtlos, true, 100 + 10 * MicGuard::kWindowSec);
        PRUEFE("Alter Handshake erlaubt keine spätere Sitzung", !g.micAllowed());
        g.bluetoothHandshakeOk(200);
        g.sessionStarted(kTransportTcp, drahtlos, true, 205);
        PRUEFE("Neuer Handshake zählt wieder", g.micAllowed());
    }
    {
        MicGuard g;
        PRUEFE("Fenster deckt die 90 s Wartezeit des Wireless-Threads ab", MicGuard::kWindowSec >= 90);
        PRUEFE("Vor der ersten Sitzung kein Mikrofon", !g.micAllowed());
    }
    {
        MicGuard g;
        g.sessionStarted(kTransportUsb, drahtlos, true, 100);
        PRUEFE("USB-Sitzung (Kabel) bekommt das Mikrofon", g.micAllowed());
    }
    {
        MicGuard g;
        g.sessionStarted(kTransportTcp, drahtlos, false, 100);
        PRUEFE("NBT_MIC_REQUIRE_BT=0 stellt das alte Verhalten her", g.micAllowed());
    }
    {
        MicGuard g;
        g.sessionStarted(kTransportTcp, false, true, 100);
        PRUEFE("NBT_WIRELESS=0 (ausgehender Scanner, kein Bluetooth) bleibt wie bisher erlaubt", g.micAllowed());
    }
    {
        MicGuard g;
        g.bluetoothHandshakeOk(100);
        g.sessionStarted(kTransportTcp, drahtlos, true, 110);
        g.sessionEnded();
        PRUEFE("Nach Sitzungsende kein Mikrofon mehr", !g.micAllowed());
    }
    {
        MicGuard g;
        g.bluetoothHandshakeOk(4294967290u);        // monoSecs läuft nach ~136 Jahren über; trotzdem kein Fehlalarm
        g.sessionStarted(kTransportTcp, drahtlos, true, 5);
        PRUEFE("Zeitüberlauf von uint32 wird richtig gerechnet", g.micAllowed());
    }

    if (g_fehler) { printf("test_mic_guard: %d Prüfung(en) fehlgeschlagen\n", g_fehler); return 1; }
    printf("test_mic_guard: alle Prüfungen bestanden\n");
    return 0;
}
