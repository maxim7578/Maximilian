// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Required Notice: Copyright (c) 2026 nanaisu - NBT-AAD (https://github.com/Sq00ky/Supra-iDrive6-Android-Auto)
// Host-Tests für die Prüfungen empfangener Daten (rx_guard.hpp und ihre Verwendung):
//   1. Klartext-Frames nur auf Kanal 0, nur vor dem TLS-Handshake und nur für Handshake-Nachrichten.
//   3. Überlaufsichere Längenprüfung in den Protobuf-Parsern (Session, WPP über Bluetooth).
//   4. Reassemblierung pro Kanal und insgesamt begrenzt.
// Jeder Fall läuft in einem eigenen Kindprozess mit Zeitlimit, damit ein Absturz oder eine Endlosschleife
// als FEHLGESCHLAGEN zählt statt den ganzen Test mitzureißen.
#include "aa_session.hpp"
#include "rx_guard.hpp"
#include "wireless_setup.hpp"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>
#include <poll.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <vector>
using namespace nbt;

#define PRUEFE(cond) do { if (!(cond)) { fprintf(stderr, "  Bedingung verletzt: %s (Zeile %d)\n", #cond, __LINE__); _exit(1); } } while (0)

static int g_fehler = 0;

static void fall(const char* name, void (*fn)(), unsigned limitSek = 3) {
    fflush(stdout);
    pid_t pid = fork();
    if (pid == 0) {
        alarm(limitSek);
        fn();
        _exit(0);
    }
    int st = 0;
    waitpid(pid, &st, 0);
    if (WIFEXITED(st) && WEXITSTATUS(st) == 0) {
        printf("[OK]     %s\n", name);
    } else {
        ++g_fehler;
        if (WIFSIGNALED(st))
            printf("[FEHLER] %s (Signal %d%s)\n", name, WTERMSIG(st),
                   WTERMSIG(st) == SIGALRM ? ": Zeitlimit, vermutlich Endlosschleife" : "");
        else
            printf("[FEHLER] %s\n", name);
    }
}

static std::vector<uint8_t> bytes(const char* hex) {
    std::vector<uint8_t> v;
    for (const char* p = hex; *p; ) {
        while (*p == ' ') ++p;
        if (!*p) break;
        unsigned b = 0;
        sscanf(p, "%2x", &b);
        v.push_back((uint8_t)b);
        p += 2;
    }
    return v;
}

// ---------- 1. Klartext-Regel ----------

static void klartextNurHandshakeAufKanal0() {
    // Vor dem Handshake: VersionRequest/-Response, SSL-Handshake, AuthComplete, Ping auf Kanal 0.
    const uint16_t erlaubt[] = { 1, 2, 3, 4, 11, 12 };
    for (size_t i = 0; i < sizeof(erlaubt) / sizeof(erlaubt[0]); ++i)
        PRUEFE(plaintextAllowed(0, erlaubt[i], false));
    // ServiceDiscovery, ByeBye, Fokusanfragen usw. nie im Klartext.
    const uint16_t verboten[] = { 0, 5, 6, 7, 0x0F, 0x10, 0x12, 0x8001 };
    for (size_t i = 0; i < sizeof(verboten) / sizeof(verboten[0]); ++i)
        PRUEFE(!plaintextAllowed(0, verboten[i], false));
}

static void klartextAufAnderenKanaelenVerboten() {
    for (unsigned ch = 1; ch < 256; ++ch) {
        PRUEFE(!plaintextChannelAllowed((uint8_t)ch));
        PRUEFE(!plaintextAllowed((uint8_t)ch, 2, false));
        PRUEFE(!plaintextAllowed((uint8_t)ch, 11, true));
    }
    PRUEFE(plaintextChannelAllowed(0));
}

static void klartextNachHandshakeNurPing() {
    // aasdk schickt Pings auch in der laufenden Sitzung unverschlüsselt; alles andere muss verschlüsselt sein.
    for (unsigned id = 0; id < 0x20; ++id)
        PRUEFE(plaintextAllowed(0, (uint16_t)id, true) == (id == 11 || id == 12));
    PRUEFE(!plaintextAllowed(0, 0x8001, true));
}

// ---------- 3. Überlaufsichere Längen ----------

static void laengePasstGrenzfaelle() {
    PRUEFE(fieldFits(0, 0, 0));
    PRUEFE(fieldFits(2, 3, 5));
    PRUEFE(!fieldFits(2, 4, 5));
    PRUEFE(!fieldFits(6, 0, 5));                    // Position schon hinter dem Ende
    PRUEFE(!fieldFits(2, ~(uint64_t)0, 5));         // 2^64-1: pos + len läuft über
    PRUEFE(!fieldFits(8, 0xFFFFFFFAull, 16));       // 32-Bit-Rücksprung aus pbFirstVarint
}

static void pbFirstVarintFindetFeld() {
    // 80 01 | 08 05 (f1=5) | 12 02 41 42 (f2="AB") | 18 07 (f3=7)
    std::vector<uint8_t> d = bytes("80 01 08 05 12 02 41 42 18 07");
    PRUEFE(pbFirstVarint(d, 2, 1) == 5);
    PRUEFE(pbFirstVarint(d, 2, 3) == 7);
    PRUEFE(pbFirstVarint(d, 2, 9) == kPbNotFound);
}

static void pbFirstVarintUebergrosseLaenge() {
    // Fund aus dem Review: Feld 1, Wiretype 2, Länge 0xFFFFFFFA. Auf 32-Bit-ARM sprang i zurück -> Endlosschleife.
    std::vector<uint8_t> d = bytes("80 01 0A FA FF FF FF 0F 08 05");
    PRUEFE(pbFirstVarint(d, 2, 1) == kPbNotFound);
    // Länge 2^64-1 (10-Byte-Varint) und abgeschnittene Felder.
    d = bytes("80 01 0A FF FF FF FF FF FF FF FF FF 01 08 05");
    PRUEFE(pbFirstVarint(d, 2, 1) == kPbNotFound);
    d = bytes("80 01 0A 05 41");                        // Länge 5, nur 1 Byte da
    PRUEFE(pbFirstVarint(d, 2, 1) == kPbNotFound);
    d = bytes("80 01 09 01 02");                        // fixed64, nur 2 Byte da
    PRUEFE(pbFirstVarint(d, 2, 2) == kPbNotFound);
    d = bytes("80 01 08");                              // Wert fehlt
    PRUEFE(pbFirstVarint(d, 2, 1) == kPbNotFound);
    d = bytes("80");                                    // Offset hinter dem Ende
    PRUEFE(pbFirstVarint(d, 2, 1) == kPbNotFound);
}

static void wppFindVarintFieldUebergrosseLaenge() {
    // Feld 1, Wiretype 2, Länge 2^64-1, danach f2=7: pos + len lief über und pos sprang zurück.
    std::vector<uint8_t> d = bytes("0A FF FF FF FF FF FF FF FF FF 01 10 07");
    uint64_t v = 0;
    PRUEFE(!wpp::findVarintField(&d[0], d.size(), 2, v));
    // Länge 2^64-11: pos (11) + len ergibt genau 0, der Parser beginnt wieder von vorn -> Endlosschleife.
    d = bytes("0A F5 FF FF FF FF FF FF FF FF 01 10 07");
    PRUEFE(!wpp::findVarintField(&d[0], d.size(), 2, v));
    // Gültige Nachricht wird weiter gelesen.
    d = bytes("0A 02 41 42 10 07");
    PRUEFE(wpp::findVarintField(&d[0], d.size(), 2, v) && v == 7);
}

static void wppDumpProtoUebergrosseLaenge() {
    // Derselbe Frame wie vom Review gemeldet: dumpProto las über das Pufferende hinaus (SIGSEGV).
    std::vector<uint8_t> d = bytes("0A FF FF FF FF FF FF FF FF FF 01");
    if (!freopen("/dev/null", "w", stdout)) _exit(2);
    wpp::dumpProto(&d[0], d.size());
}

// ---------- 4. Reassemblierung ----------

static void reassemblierungProKanalBegrenzt() {
    PRUEFE(reassemblyFits(0, 0, kReassemblyChannelMax));
    PRUEFE(!reassemblyFits(0, 0, kReassemblyChannelMax + 1));
    PRUEFE(!reassemblyFits(kReassemblyChannelMax - 10, kReassemblyChannelMax - 10, 11));
}

static void reassemblierungInsgesamtBegrenzt() {
    PRUEFE(kReassemblyTotalMax >= kReassemblyChannelMax);
    // Viele Kanäle mit je knapp 8 MiB: früher bis 256 x 8 MiB = 2 GiB.
    PRUEFE(reassemblyFits(0, kReassemblyTotalMax - 100, 100));
    PRUEFE(!reassemblyFits(0, kReassemblyTotalMax - 100, 101));
    PRUEFE(!reassemblyFits(0, kReassemblyTotalMax, 1));
    PRUEFE(!reassemblyFits(0, (size_t)-1, 1));      // kein Überlauf in der Summe
}

// ---------- Integration: AASession über einen Socket ----------

static void schreibe(int fd, const std::vector<uint8_t>& v) {
    size_t off = 0;
    while (off < v.size()) {
        ssize_t n = write(fd, &v[off], v.size() - off);
        if (n <= 0) _exit(3);
        off += (size_t)n;
    }
}

// Liest einen Frame mit Kopf (ch, flags, len16) innerhalb von ms Millisekunden.
static bool leseFrame(int fd, int ms, std::vector<uint8_t>& frame) {
    frame.clear();
    size_t want = 4;
    while (frame.size() < want) {
        struct pollfd p = { fd, POLLIN, 0 };
        if (poll(&p, 1, ms) <= 0) return false;
        uint8_t buf[4096];
        size_t need = want - frame.size();
        ssize_t n = read(fd, buf, need < sizeof(buf) ? need : sizeof(buf));
        if (n <= 0) return false;
        frame.insert(frame.end(), buf, buf + n);
        if (want == 4 && frame.size() == 4) want = 4 + ((size_t)frame[2] << 8 | frame[3]);
    }
    return true;
}

static std::vector<uint8_t> klartextFrame(uint8_t ch, const char* payloadHex) {
    std::vector<uint8_t> pl = bytes(payloadHex);
    std::vector<uint8_t> f;
    f.push_back(ch);
    f.push_back(0x03);                                  // BULK, Bit 0x08 (verschlüsselt) nicht gesetzt
    f.push_back((uint8_t)(pl.size() >> 8));
    f.push_back((uint8_t)pl.size());
    f.insert(f.end(), pl.begin(), pl.end());
    return f;
}

static volatile int g_beendet = 0;
static void beiEnde(void*) { __sync_fetch_and_add(&g_beendet, 1); }

static void sitzungIgnoriertKlartextByeBye() {
    signal(SIGPIPE, SIG_IGN);
    AASession s;
    s.setDisconnectCallback(&beiEnde, NULL);
    int sv[2];
    PRUEFE(socketpair(AF_UNIX, SOCK_STREAM, 0, sv) == 0);
    PRUEFE(s.start(sv[0]));
    std::vector<uint8_t> f;
    PRUEFE(leseFrame(sv[1], 2000, f) && f[0] == 0 && f[4] == 0 && f[5] == 1);   // VersionRequest
    // Angreifer ohne TLS schickt ByeByeRequest im Klartext: früher beendete das die Sitzung sofort.
    schreibe(sv[1], klartextFrame(0, "00 0F 08 01"));
    // Danach eine Klartext-VersionResponse: Die Sitzung verarbeitet Frames der Reihe nach. Kommt der ClientHello,
    // ist das ByeBye vorher schon behandelt (und verworfen) worden; mit dem alten Code war die Sitzung da schon zu.
    schreibe(sv[1], klartextFrame(0, "00 02 00 01 00 07 00 00"));
    PRUEFE(leseFrame(sv[1], 3000, f) && f[0] == 0 && f[4] == 0x00 && f[5] == 0x03);
    PRUEFE(g_beendet == 0);
    PRUEFE(s.isActive());
    s.stop();
    close(sv[1]);
}

static void sitzungIgnoriertKlartextAufKanal1() {
    signal(SIGPIPE, SIG_IGN);
    AASession s;
    s.setDisconnectCallback(&beiEnde, NULL);
    int sv[2];
    PRUEFE(socketpair(AF_UNIX, SOCK_STREAM, 0, sv) == 0);
    PRUEFE(s.start(sv[0]));
    std::vector<uint8_t> f;
    PRUEFE(leseFrame(sv[1], 2000, f));
    // Der Review-Frame (SensorStartRequest mit Länge 0xFFFFFFFA) und ein LAST-Fragment ohne FIRST.
    schreibe(sv[1], klartextFrame(1, "80 01 0A FA FF FF FF 0F"));
    std::vector<uint8_t> frag = klartextFrame(6, "00 00 01 02 03");
    frag[1] = 0x02;
    schreibe(sv[1], frag);
    // Klartext-VersionResponse wird weiterhin angenommen: Antwort ist der TLS-ClientHello (Kanal 0, Msg 3).
    schreibe(sv[1], klartextFrame(0, "00 02 00 01 00 07 00 00"));
    PRUEFE(leseFrame(sv[1], 3000, f));
    PRUEFE(f[0] == 0 && f[4] == 0x00 && f[5] == 0x03);
    PRUEFE(g_beendet == 0 && s.isActive());
    s.stop();
    close(sv[1]);
}

// Ein Fragment im Klartext: flags 0x01 FIRST (mit 4-Byte-Gesamtlänge), 0x00 MIDDLE, 0x02 LAST.
static std::vector<uint8_t> klartextFragment(uint8_t ch, uint8_t typ, const char* payloadHex, uint32_t gesamt = 0) {
    std::vector<uint8_t> pl = bytes(payloadHex);
    std::vector<uint8_t> f;
    f.push_back(ch);
    f.push_back(typ);
    f.push_back((uint8_t)(pl.size() >> 8));
    f.push_back((uint8_t)pl.size());
    if (typ == 0x01) {
        f.push_back((uint8_t)(gesamt >> 24)); f.push_back((uint8_t)(gesamt >> 16));
        f.push_back((uint8_t)(gesamt >> 8));  f.push_back((uint8_t)gesamt);
    }
    f.insert(f.end(), pl.begin(), pl.end());
    return f;
}

static void sitzungFragmenteOhneFirstVerworfen() {
    signal(SIGPIPE, SIG_IGN);
    AASession s;
    s.setDisconnectCallback(&beiEnde, NULL);
    int sv[2];
    PRUEFE(socketpair(AF_UNIX, SOCK_STREAM, 0, sv) == 0);
    PRUEFE(s.start(sv[0]));
    std::vector<uint8_t> f;
    PRUEFE(leseFrame(sv[1], 2000, f));
    // MIDDLE + LAST ohne FIRST ergeben zusammen eine VersionResponse. Früher wurde sie zugestellt (ClientHello kam).
    schreibe(sv[1], klartextFragment(0, 0x00, "00 02 00 01"));
    schreibe(sv[1], klartextFragment(0, 0x02, "00 07 00 00"));
    PRUEFE(!leseFrame(sv[1], 500, f));
    // Dieselbe Nachricht korrekt geteilt (FIRST + LAST) wird angenommen.
    schreibe(sv[1], klartextFragment(0, 0x01, "00 02 00 01", 8));
    schreibe(sv[1], klartextFragment(0, 0x02, "00 07 00 00"));
    PRUEFE(leseFrame(sv[1], 3000, f) && f[0] == 0 && f[4] == 0x00 && f[5] == 0x03);
    PRUEFE(g_beendet == 0 && s.isActive());
    s.stop();
    close(sv[1]);
}

int main() {
    printf("test_rx_guard: Prüfungen empfangener Daten\n");
    fall("Klartext nur für Handshake-Nachrichten auf Kanal 0", klartextNurHandshakeAufKanal0);
    fall("Klartext auf allen anderen Kanälen verboten", klartextAufAnderenKanaelenVerboten);
    fall("Klartext nach dem TLS-Handshake nur noch für Ping", klartextNachHandshakeNurPing);
    fall("Längenprüfung ohne Überlauf (Grenzfälle)", laengePasstGrenzfaelle);
    fall("pbFirstVarint findet Felder hinter Längenfeldern", pbFirstVarintFindetFeld);
    fall("pbFirstVarint bricht bei übergroßer oder abgeschnittener Länge ab", pbFirstVarintUebergrosseLaenge);
    fall("WPP findVarintField: übergroße Länge endet ohne Endlosschleife", wppFindVarintFieldUebergrosseLaenge);
    fall("WPP dumpProto: Länge 2^64-1 liest nicht über den Puffer hinaus", wppDumpProtoUebergrosseLaenge);
    fall("Reassemblierung pro Kanal auf 8 MiB begrenzt", reassemblierungProKanalBegrenzt);
    fall("Reassemblierung über alle Kanäle begrenzt", reassemblierungInsgesamtBegrenzt);
    fall("Sitzung: Klartext-ByeBye ohne TLS beendet die Sitzung nicht", sitzungIgnoriertKlartextByeBye, 5);
    fall("Sitzung: Klartext auf Kanal 1/6 verworfen, Klartext-VersionResponse weiter angenommen",
         sitzungIgnoriertKlartextAufKanal1, 6);
    fall("Sitzung: MIDDLE/LAST ohne FIRST verworfen, FIRST+LAST zugestellt", sitzungFragmenteOhneFirstVerworfen, 6);
    if (g_fehler) {
        printf("test_rx_guard: %d Fall/Fälle fehlgeschlagen\n", g_fehler);
        return 1;
    }
    printf("test_rx_guard: alle Fälle bestanden\n");
    return 0;
}
