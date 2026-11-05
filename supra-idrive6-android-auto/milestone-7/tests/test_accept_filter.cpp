// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Required Notice: Copyright (c) 2026 nanaisu - NBT-AAD (https://github.com/Sq00ky/Supra-iDrive6-Android-Auto)
// Host-Test für nbt::aaPeerAllowed (alt_wifi.hpp): Wer darf sich auf TCP 5277 verbinden?
// Früher galt ohne lesbare WLAN-Adresse "gleiches /24 wie die Ankunftsadresse". Lauschte der Server dann auf allen
// Interfaces, kam jeder Rechner am Ethernet/OBD-Kabel durch.
#include "alt_wifi.hpp"
#include <stdio.h>
#include <string>
#include <vector>
using namespace nbt;

static int g_fehler = 0;
#define PRUEFE(name, cond) do { \
    if (cond) printf("[OK]     %s\n", name); \
    else { printf("[FEHLER] %s (Zeile %d: %s)\n", name, __LINE__, #cond); ++g_fehler; } } while (0)

static const unsigned kTelefonAp  = 0xAC10E064u;   // 172.16.224.100 (CarPlay-Hotspot)
static const unsigned kTelefonWfd = 0xAC10DE64u;   // 172.16.222.100 (Wi-Fi Direct)
static const unsigned kEthernet   = 0xA030C701u;   // 160.48.199.1 (Fahrzeugnetz / OBD-Ethernet)
static const unsigned kEthernetHu = 0xA030C764u;   // 160.48.199.100 (Adresse der Headunit dort)

int main() {
    printf("test_accept_filter: Annahmefilter für TCP 5277\n");
    const unsigned netze[2] = { 0xAC10E001u, 0xAC10DE01u };   // gelesene uap0 / wfd0

    PRUEFE("Telefon im CarPlay-Netz wird angenommen", aaPeerAllowed(kTelefonAp, netze, 2));
    PRUEFE("Telefon im Wi-Fi-Direct-Netz wird angenommen", aaPeerAllowed(kTelefonWfd, netze, 2));
    PRUEFE("Rechner am Fahrzeug-Ethernet wird abgewiesen", !aaPeerAllowed(kEthernet, netze, 2));

    // Kein Interface lesbar: früher entschied die Ankunftsadresse (hier das Ethernet der Headunit) -> angenommen.
    PRUEFE("Ohne lesbare WLAN-Adresse: Ethernet-Rechner trotzdem abgewiesen", !aaPeerAllowed(kEthernet, netze, 0));
    PRUEFE("Ohne lesbare WLAN-Adresse: Telefon im Standard-CarPlay-Netz angenommen", aaPeerAllowed(kTelefonAp, netze, 0));
    PRUEFE("Ohne lesbare WLAN-Adresse: Telefon im Standard-Wi-Fi-Direct-Netz angenommen",
           aaPeerAllowed(kTelefonWfd, netze, 0));
    PRUEFE("Loopback ist nie ein Telefon", !aaPeerAllowed(0x7F000001u, netze, 2) && !aaPeerAllowed(0x7F000001u, netze, 0));
    PRUEFE("Gleiches Netz wie die Headunit am Ethernet reicht nicht mehr",
           !aaPeerAllowed(kEthernet, netze, 0) && kEthernet != kEthernetHu);

    // Ein Auto, das seine Interfaces anders nummeriert, liefert die Netze über die gelesenen Adressen.
    const unsigned anders[1] = { 0x0A4D0001u };   // 10.77.0.1
    PRUEFE("Anders nummeriertes WLAN-Netz wird über die gelesene Adresse angenommen",
           aaPeerAllowed(0x0A4D0017u, anders, 1));
    PRUEFE("Mit gelesenen Adressen gelten die Standardnetze nicht zusätzlich", !aaPeerAllowed(kTelefonAp, anders, 1));

    // Netzliste aus den gelesenen bzw. eingestellten Adressen (uap0/wfd0 oder NBT_AP_IF/NBT_WFD_IF, NBT_AP_IP/NBT_WFD_IP).
    {
        std::vector<std::string> adr;
        adr.push_back("172.16.224.1");
        adr.push_back("");                  // Interface ohne Adresse
        adr.push_back("10.77.0.1");         // NBT_AP_IP in einem anderen Netz
        adr.push_back("172.16.224.7");      // gleiches /24 wie die erste: nicht doppelt
        adr.push_back("kaputt");
        unsigned n[4] = { 0, 0, 0, 0 };
        int cnt = aaNetsFromAddrs(adr, n, 4);
        PRUEFE("Netzliste: gültige Adressen, ohne Doppelte und Unlesbares", cnt == 2);
        PRUEFE("Netzliste: eingestelltes Netz wird angenommen", aaPeerAllowed(0x0A4D0017u, n, (size_t)cnt));
        PRUEFE("Netzliste: CarPlay-Netz wird angenommen", aaPeerAllowed(kTelefonAp, n, (size_t)cnt));
        PRUEFE("Netzliste: Ethernet bleibt draußen", !aaPeerAllowed(kEthernet, n, (size_t)cnt));
        std::vector<std::string> viele(10, "");
        for (int i = 0; i < 10; ++i) { char b2[32]; snprintf(b2, sizeof(b2), "10.0.%d.1", i); viele[i] = b2; }
        PRUEFE("Netzliste: höchstens so viele wie Platz ist", aaNetsFromAddrs(viele, n, 4) == 4);
    }

    if (g_fehler) { printf("test_accept_filter: %d Prüfung(en) fehlgeschlagen\n", g_fehler); return 1; }
    printf("test_accept_filter: alle Prüfungen bestanden\n");
    return 0;
}
