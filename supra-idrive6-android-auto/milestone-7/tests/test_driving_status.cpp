// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Required Notice: Copyright (c) 2026 nanaisu - NBT-AAD (https://github.com/Sq00ky/Supra-iDrive6-Android-Auto)
// Host-Test für src/driving_status.hpp: Standard ist "fährt" (Fahrbeschränkungen von Android Auto an),
// Sprachbedienung bleibt erlaubt; NBT_DRIVING_STATUS überschreibt.
#include "driving_status.hpp"
#include <stdio.h>
#include <stdlib.h>
using namespace nbt;

static int g_fehler = 0;
#define PRUEFE(name, cond) do { \
    if (cond) printf("[OK]     %s\n", name); \
    else { printf("[FEHLER] %s (Zeile %d: %s)\n", name, __LINE__, #cond); ++g_fehler; } } while (0)

int main() {
    printf("test_driving_status: Fahrstatus an das Telefon\n");

    unsetenv("NBT_DRIVING_STATUS");
    const unsigned s = drivingStatus();
    PRUEFE("Standard ist nicht mehr uneingeschränkt", s != kDriveUnrestricted);
    PRUEFE("Standard sperrt Video", (s & kDriveNoVideo) != 0);
    PRUEFE("Standard sperrt die Tastatur", (s & kDriveNoKeyboard) != 0);
    PRUEFE("Standard sperrt Einstellungen", (s & kDriveNoConfig) != 0);
    PRUEFE("Standard kürzt Nachrichten", (s & kDriveLimitMessageLen) != 0);
    PRUEFE("Standard lässt Sprachbedienung zu (Assistant beim Fahren)", (s & kDriveNoVoice) == 0);

    setenv("NBT_DRIVING_STATUS", "0", 1);
    PRUEFE("NBT_DRIVING_STATUS=0 stellt uneingeschränkt her (altes Verhalten)", drivingStatus() == 0);
    setenv("NBT_DRIVING_STATUS", "31", 1);
    PRUEFE("NBT_DRIVING_STATUS=31 sperrt alles", drivingStatus() == 31);
    setenv("NBT_DRIVING_STATUS", "200", 1);
    PRUEFE("Zu großer Wert wird auf 31 begrenzt", drivingStatus() == 31);
    setenv("NBT_DRIVING_STATUS", "quatsch", 1);
    PRUEFE("Unlesbarer Wert behält den Standard", drivingStatus() == s);
    setenv("NBT_DRIVING_STATUS", "", 1);
    PRUEFE("Leerer Wert behält den Standard", drivingStatus() == s);

    if (g_fehler) { printf("test_driving_status: %d Prüfung(en) fehlgeschlagen\n", g_fehler); return 1; }
    printf("test_driving_status: alle Prüfungen bestanden\n");
    return 0;
}
