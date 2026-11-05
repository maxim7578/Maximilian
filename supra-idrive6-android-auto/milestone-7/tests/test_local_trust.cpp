// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Required Notice: Copyright (c) 2026 nanaisu - NBT-AAD (https://github.com/Sq00ky/Supra-iDrive6-Android-Auto)
// Host-Test für src/local_trust.hpp:
//  - Touch-PDUs (UDP 30567) nie aus dem Android-Auto-WLAN annehmen oder als Touch-Controller lernen.
//  - Die iDrive-App beendet bei "Force Stop" nur einen Prozess, der wirklich nbt-aad ist.
#include "local_trust.hpp"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
using namespace nbt;

static int g_fehler = 0;
#define PRUEFE(name, cond) do { \
    if (cond) printf("[OK]     %s\n", name); \
    else { printf("[FEHLER] %s (Zeile %d: %s)\n", name, __LINE__, #cond); ++g_fehler; } } while (0)

static void schreibeExefile(const char* root, int pid, const char* inhalt) {
    char p[256];
    snprintf(p, sizeof(p), "%s/%d", root, pid);
    mkdir(p, 0700);
    snprintf(p, sizeof(p), "%s/%d/exefile", root, pid);
    FILE* f = fopen(p, "w");
    if (f) { fputs(inhalt, f); fclose(f); }
}

int main() {
    printf("test_local_trust: Touch-Absender und Prozessprüfung\n");

    // ---- Touch-Absender ----
    const unsigned keine[1] = { 0 };
    PRUEFE("Touch-Controller im Fahrzeugnetz wird angenommen", touchSenderAllowed(0xA030C773u, keine, 0));   // 160.48.199.115
    PRUEFE("Gestenkamera im Fahrzeugnetz wird angenommen", touchSenderAllowed(0xA030C710u, keine, 0));      // 160.48.199.16
    PRUEFE("Absender aus dem CarPlay-WLAN wird abgewiesen", !touchSenderAllowed(0xAC10E064u, keine, 0));     // 172.16.224.100
    PRUEFE("Absender aus dem Wi-Fi-Direct-Netz wird abgewiesen", !touchSenderAllowed(0xAC10DE65u, keine, 0)); // 172.16.222.101
    const unsigned gelesen[1] = { 0x0A4D0001u };   // uap0 anders nummeriert: 10.77.0.1
    PRUEFE("Absender aus einem gelesenen WLAN-Netz wird abgewiesen", !touchSenderAllowed(0x0A4D0017u, gelesen, 1));
    PRUEFE("Standard-WLAN-Netze gelten auch mit gelesenen Netzen", !touchSenderAllowed(0xAC10E064u, gelesen, 1));
    PRUEFE("Lokaler Absender (Loopback) bleibt erlaubt", touchSenderAllowed(0x7F000001u, gelesen, 1));

    // ---- Prozessprüfung vor kill ----
    PRUEFE("Pfad des Daemons erkannt", exePathIsNbtAad("/opt/aa/nbt-aad"));
    PRUEFE("Pfad mit Zeilenumbruch erkannt", exePathIsNbtAad("/opt/aa/nbt-aad\n"));
    PRUEFE("HmiMain3D wird nicht erkannt", !exePathIsNbtAad("/opt/hmi/bin/HmiMain3D"));
    PRUEFE("Ähnlicher Name wird nicht erkannt", !exePathIsNbtAad("/opt/aa/xnbt-aad") && !exePathIsNbtAad("/opt/aa/nbt-aad-old"));
    PRUEFE("Leerer Pfad wird nicht erkannt", !exePathIsNbtAad("") && !exePathIsNbtAad(NULL));

    char root[] = "/tmp/nbt_proc_testXXXXXX";
    if (!mkdtemp(root)) { printf("[FEHLER] mkdtemp\n"); return 1; }
    schreibeExefile(root, 4242, "/opt/aa/nbt-aad\n");
    schreibeExefile(root, 77, "/opt/hmi/bin/HmiMain3D\n");
    PRUEFE("PID des Daemons darf beendet werden", pidIsNbtAad(root, 4242));
    PRUEFE("Fremde PID aus der Zustandsdatei wird nicht beendet", !pidIsNbtAad(root, 77));
    PRUEFE("Nicht vorhandene PID wird nicht beendet", !pidIsNbtAad(root, 9999));
    PRUEFE("PID 0 oder negativ wird nicht beendet", !pidIsNbtAad(root, 0) && !pidIsNbtAad(root, -1));
    // Auf QNX hat nicht jeder Prozess ein lesbares exefile: dann bleibt Force Stop wie bisher möglich.
    PRUEFE("Nachweislich anderes Programm wird erkannt", pidIsOtherProgram(root, 77));
    PRUEFE("Daemon ist kein anderes Programm", !pidIsOtherProgram(root, 4242));
    PRUEFE("Unlesbares exefile gilt nicht als anderes Programm", !pidIsOtherProgram(root, 9999));

    char cmd[300];
    snprintf(cmd, sizeof(cmd), "rm -rf %s", root);
    if (system(cmd) != 0) printf("Hinweis: %s nicht gelöscht\n", root);

    if (g_fehler) { printf("test_local_trust: %d Prüfung(en) fehlgeschlagen\n", g_fehler); return 1; }
    printf("test_local_trust: alle Prüfungen bestanden\n");
    return 0;
}
