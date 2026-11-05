// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Required Notice: Copyright (c) 2026 nanaisu - NBT-AAD (https://github.com/Sq00ky/Supra-iDrive6-Android-Auto)
// Host-Test für src/pf_rules.hpp: Erlaubnis-Regel für Port 5277 statt `pfctl -d` (ganzer Paketfilter aus).
#include "pf_rules.hpp"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <string>
#include <vector>
using namespace nbt;

static int g_fehler = 0;
#define PRUEFE(name, cond) do { \
    if (cond) printf("[OK]     %s\n", name); \
    else { printf("[FEHLER] %s (Zeile %d: %s)\n", name, __LINE__, #cond); ++g_fehler; } } while (0)

static bool enthaelt(const std::string& s, const char* t) { return s.find(t) != std::string::npos; }

static std::vector<std::string> ziele() {
    std::vector<std::string> v;
    v.push_back("172.16.224.1");
    v.push_back("172.16.222.1");
    return v;
}

int main() {
    printf("test_pf_rules: Paketfilter-Regel für Android Auto\n");

    // ---- Modus aus den Einstellungen ----
    PRUEFE("Standard ist die Erlaubnis-Regel", pfModeFrom(NULL, -1) == kPfAllowRule);
    PRUEFE("NBT_PF=off schaltet den Filter ab wie früher", pfModeFrom("off", -1) == kPfDisable);
    PRUEFE("NBT_PF=disable schaltet den Filter ab", pfModeFrom("disable", -1) == kPfDisable);
    PRUEFE("NBT_PF=keep lässt den Filter in Ruhe", pfModeFrom("keep", -1) == kPfKeep);
    PRUEFE("NBT_KEEP_PF=1 gewinnt (alte Einstellung)", pfModeFrom("rule", 1) == kPfKeep);
    PRUEFE("NBT_PF=rule ist die Erlaubnis-Regel", pfModeFrom("rule", -1) == kPfAllowRule);
    PRUEFE("Unbekannter Wert behält den Standard", pfModeFrom("quatsch", -1) == kPfAllowRule);

    // ---- Status ----
    PRUEFE("Status Enabled erkannt",
           pfStatusEnabled("Status: Enabled for 0 days 00:12:01           Debug: Urgent\n\nState Table\n"));
    PRUEFE("Status Disabled erkannt", !pfStatusEnabled("Status: Disabled for 0 days 00:00:03\n"));
    PRUEFE("Leere Ausgabe gilt nicht als aktiv", !pfStatusEnabled(""));

    // ---- Regeln bauen ----
    std::string pass = pfPassRules(ziele(), 5277);
    PRUEFE("Regel lässt TCP 5277 zur AP-Adresse herein",
           enthaelt(pass, "pass in quick proto tcp from any to 172.16.224.1 port 5277 keep state"));
    PRUEFE("Regel lässt TCP 5277 zur Wi-Fi-Direct-Adresse herein",
           enthaelt(pass, "pass in quick proto tcp from any to 172.16.222.1 port 5277 keep state"));
    PRUEFE("Regel öffnet keinen anderen Port", !enthaelt(pass, "port 5278") && !enthaelt(pass, "from any to any"));
    PRUEFE("Jede Regelzeile endet mit Zeilenumbruch", !pass.empty() && pass[pass.size() - 1] == '\n');

    // ---- Zusammenführen mit den Regeln des Autos ----
    const char* auto_regeln =
        "block drop in log all\n"
        "pass in quick on lo0 all\n"
        "pass out all keep state\n";
    std::string neu = pfMergeRules(pass, auto_regeln);
    PRUEFE("Eigene Regeln stehen vor den Regeln des Autos", neu.find("pass in quick proto tcp") < neu.find("block drop in"));
    PRUEFE("Regeln des Autos bleiben vollständig erhalten",
           enthaelt(neu, "block drop in log all\n") && enthaelt(neu, "pass in quick on lo0 all\n") &&
           enthaelt(neu, "pass out all keep state\n"));
    // pfctl -sr zeigt unsere Regel in normalisierter Form; beim erneuten Anwenden darf sie nicht doppelt landen.
    std::string sr_mit_unserer =
        "pass in quick inet proto tcp from any to 172.16.224.1 port = 5277 flags S/SA keep state\n"
        "pass in quick inet proto tcp from any to 172.16.222.1 port = 5277 flags S/SA keep state\n"
        "block drop in log all\n";
    std::string zweimal = pfMergeRules(pass, sr_mit_unserer);
    size_t n = 0;
    for (size_t p = zweimal.find("172.16.224.1"); p != std::string::npos; p = zweimal.find("172.16.224.1", p + 1)) ++n;
    PRUEFE("Erneutes Anwenden verdoppelt die Regel nicht", n == 1);
    PRUEFE("Erneutes Anwenden behält die Regeln des Autos", enthaelt(zweimal, "block drop in log all\n"));
    PRUEFE("Letzte Zeile ohne Umbruch wird übernommen",
           enthaelt(pfMergeRules(pass, "block drop in all"), "block drop in all\n"));

    // pf verlangt die Reihenfolge Normalisierung (scrub) vor Filterregeln, sonst lehnt pfctl die Datei ab.
    std::string mit_scrub = pfMergeRules(pass, "scrub in all fragment reassemble\nblock drop in all\n");
    PRUEFE("scrub-Regeln bleiben vor den eigenen Regeln",
           mit_scrub.find("scrub in all") < mit_scrub.find("pass in quick proto tcp") &&
           mit_scrub.find("pass in quick proto tcp") < mit_scrub.find("block drop in all"));

    // ---- Prüfen, ob die Regel geladen ist ----
    PRUEFE("Geladene Regel wird in pfctl -sr erkannt", pfRulesHavePass(sr_mit_unserer, ziele(), 5277));
    PRUEFE("Fehlende Regel wird erkannt", !pfRulesHavePass(auto_regeln, ziele(), 5277));
    PRUEFE("Nur eine von zwei Adressen geladen reicht nicht",
           !pfRulesHavePass("pass in quick inet proto tcp from any to 172.16.224.1 port = 5277 keep state\n", ziele(), 5277));
    PRUEFE("Anderer Port zählt nicht",
           !pfRulesHavePass("pass in quick inet proto tcp from any to 172.16.224.1 port = 5278 keep state\n"
                            "pass in quick inet proto tcp from any to 172.16.222.1 port = 5278 keep state\n",
                            ziele(), 5277));
    PRUEFE("Block-Regel mit derselben Adresse zählt nicht",
           !pfRulesHavePass("block in quick inet proto tcp from any to 172.16.224.1 port = 5277\n"
                            "block in quick inet proto tcp from any to 172.16.222.1 port = 5277\n", ziele(), 5277));
    PRUEFE("Adresse als Präfix einer anderen zählt nicht",
           !pfRulesHavePass("pass in quick inet proto tcp from any to 172.16.224.10 port = 5277 keep state\n"
                            "pass in quick inet proto tcp from any to 172.16.222.10 port = 5277 keep state\n",
                            ziele(), 5277));

    if (g_fehler) { printf("test_pf_rules: %d Prüfung(en) fehlgeschlagen\n", g_fehler); return 1; }
    printf("test_pf_rules: alle Prüfungen bestanden\n");
    return 0;
}
