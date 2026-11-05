// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Required Notice: Copyright (c) 2026 nanaisu - NBT-AAD (https://github.com/Sq00ky/Supra-iDrive6-Android-Auto)
// Host-Test für src/log_secret.hpp: Die Wi-Fi-Direct-Passphrase steht nur auf ausdrücklichen Wunsch im Log.
#include "log_secret.hpp"
#include <stdio.h>
#include <stdlib.h>
#include <string>
using namespace nbt;

static int g_fehler = 0;
#define PRUEFE(name, cond) do { \
    if (cond) printf("[OK]     %s\n", name); \
    else { printf("[FEHLER] %s (Zeile %d: %s)\n", name, __LINE__, #cond); ++g_fehler; } } while (0)

int main() {
    printf("test_log_secret: Passphrase im Log\n");
    const std::string pass = "geheim12345";

    std::string verdeckt = secretForLog(pass, false);
    PRUEFE("Standard: Passphrase steht nicht im Logtext", verdeckt.find(pass) == std::string::npos);
    PRUEFE("Standard: Länge wird genannt", verdeckt.find("11 chars") != std::string::npos);
    PRUEFE("Standard: Hinweis, wie man sie sichtbar macht", verdeckt.find("NBT_LOG_WFD_PASS=1") != std::string::npos);
    PRUEFE("Auf Wunsch: Passphrase in Anführungszeichen", secretForLog(pass, true) == "'geheim12345'");

    unsetenv("NBT_LOG_WFD_PASS");
    PRUEFE("Ohne Einstellung bleibt sie verborgen", !logWfdPassphrase());
    setenv("NBT_LOG_WFD_PASS", "1", 1);
    PRUEFE("NBT_LOG_WFD_PASS=1 zeigt sie", logWfdPassphrase());
    setenv("NBT_LOG_WFD_PASS", "0", 1);
    PRUEFE("NBT_LOG_WFD_PASS=0 verbirgt sie", !logWfdPassphrase());

    if (g_fehler) { printf("test_log_secret: %d Prüfung(en) fehlgeschlagen\n", g_fehler); return 1; }
    printf("test_log_secret: alle Prüfungen bestanden\n");
    return 0;
}
