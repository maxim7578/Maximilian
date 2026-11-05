// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Required Notice: Copyright (c) 2026 nanaisu - NBT-AAD (https://github.com/Sq00ky/Supra-iDrive6-Android-Auto)
// The car's packet filter and the Android Auto port (header-only text helpers, host-tested in
// tests/test_pf_rules.cpp; main.cpp runs pfctl).
//
// The car's pf ruleset blocks TCP 5277, where the phone connects. Up to v1.8.x the daemon ran `pfctl -d`, which
// turns the whole filter off on every interface (CarPlay hotspot, Wi-Fi Direct, Ethernet) until the next reboot.
// Now (NBT_PF=rule, the default) it reads the live filter rules (`pfctl -sr`), puts one `pass in quick` rule per
// listening address for TCP 5277 in front of them and loads the result as the filter rules only (`pfctl -R -f`),
// so NAT, tables and options stay as the car set them. If that fails, or the phone twice takes the Wi-Fi details
// and never connects, the daemon falls back to `pfctl -d` and says so in the log.
// NBT_PF=off (or disable) is the old `pfctl -d`; NBT_PF=keep, like NBT_KEEP_PF=1, leaves the filter alone.
#ifndef NBT_PF_RULES_HPP
#define NBT_PF_RULES_HPP

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <string>
#include <vector>

namespace nbt {

enum PfMode { kPfAllowRule = 0, kPfDisable = 1, kPfKeep = 2 };

// nbtPf: NBT_PF (NULL if unset). keepFlag: envFlag("NBT_KEEP_PF") (1 = keep, the older setting wins).
inline PfMode pfModeFrom(const char* nbtPf, int keepFlag) {
    if (keepFlag == 1) return kPfKeep;
    if (!nbtPf || !*nbtPf) return kPfAllowRule;
    if (!strcmp(nbtPf, "off") || !strcmp(nbtPf, "disable") || !strcmp(nbtPf, "0")) return kPfDisable;
    if (!strcmp(nbtPf, "keep")) return kPfKeep;
    return kPfAllowRule;   // "rule" and anything unknown
}

inline const char* pfModeName(PfMode m) {
    return m == kPfDisable ? "off (pfctl -d)" : m == kPfKeep ? "keep (untouched)" : "rule (allow TCP 5277 only)";
}

// `pfctl -si` output: "Status: Enabled for ..." / "Status: Disabled ...".
inline bool pfStatusEnabled(const std::string& si) {
    return si.find("Status: Enabled") != std::string::npos;
}

inline std::string pfPassRules(const std::vector<std::string>& dstIps, uint16_t port) {
    std::string out;
    for (size_t i = 0; i < dstIps.size(); ++i) {
        char line[160];
        snprintf(line, sizeof(line), "pass in quick proto tcp from any to %s port %u keep state\n",
                 dstIps[i].c_str(), (unsigned)port);
        out += line;
    }
    return out;
}

// True if `line` mentions TCP port `port` as a whole number ("port = 5277" from pfctl -sr, "port 5277" from us).
inline bool pfLineHasPort(const std::string& line, uint16_t port) {
    char a[32], b[32];
    snprintf(a, sizeof(a), "port = %u", (unsigned)port);
    snprintf(b, sizeof(b), "port %u", (unsigned)port);
    const char* pats[2] = { a, b };
    for (int k = 0; k < 2; ++k) {
        size_t len = strlen(pats[k]);
        for (size_t p = line.find(pats[k]); p != std::string::npos; p = line.find(pats[k], p + 1)) {
            char next = p + len < line.size() ? line[p + len] : ' ';
            if (next < '0' || next > '9') return true;
        }
    }
    return false;
}

inline bool pfLineIsPassInQuickTcp(const std::string& line) {
    return line.compare(0, 13, "pass in quick") == 0 && line.find(" proto tcp ") != std::string::npos;
}

// True if `line` is a pass-in rule for TCP `port` to exactly `ip` on any interface, the shape of our own rule as
// pfctl prints it back ("pass in quick inet proto tcp from any to 172.16.224.1 port = 5277 flags S/SA keep state").
// A rule of the car's that only covers another interface ("on en0") or has 5277 as the source port does not count.
inline bool pfLinePassesTo(const std::string& line, const std::string& ip, uint16_t port) {
    if (!pfLineIsPassInQuickTcp(line) || line.find(" on ") != std::string::npos) return false;
    char a[96], b[96];
    snprintf(a, sizeof(a), " to %s port = %u", ip.c_str(), (unsigned)port);
    snprintf(b, sizeof(b), " to %s port %u", ip.c_str(), (unsigned)port);
    const char* pats[2] = { a, b };
    for (int k = 0; k < 2; ++k) {
        size_t len = strlen(pats[k]);
        for (size_t p = line.find(pats[k]); p != std::string::npos; p = line.find(pats[k], p + 1)) {
            char next = p + len < line.size() ? line[p + len] : ' ';
            if (next < '0' || next > '9') return true;
        }
    }
    return false;
}

inline std::vector<std::string> pfLines(const std::string& text) {
    std::vector<std::string> lines;
    size_t pos = 0;
    while (pos < text.size()) {
        size_t nl = text.find('\n', pos);
        if (nl == std::string::npos) nl = text.size();
        std::string l = text.substr(pos, nl - pos);
        if (!l.empty() && l[l.size() - 1] == '\r') l.erase(l.size() - 1);
        if (!l.empty()) lines.push_back(l);
        pos = nl + 1;
    }
    return lines;
}

// True if `line` is one of the rules in `passRules` as pfctl prints it back (same address and port).
inline bool pfLineIsOurs(const std::string& line, const std::string& passRules) {
    if (!pfLineIsPassInQuickTcp(line)) return false;
    std::vector<std::string> ours = pfLines(passRules);
    for (size_t k = 0; k < ours.size(); ++k) {
        size_t to = ours[k].find(" to ");
        size_t pt = ours[k].find(" port ");
        if (to == std::string::npos || pt == std::string::npos || pt <= to + 4) continue;
        std::string ip = ours[k].substr(to + 4, pt - (to + 4));
        unsigned port = (unsigned)atoi(ours[k].c_str() + pt + 6);
        if (pfLinePassesTo(line, ip, (uint16_t)port)) return true;
    }
    return false;
}

// The car's rules as `pfctl -sr` printed them, with our pass rules in front of the filter rules. pf wants
// normalization (scrub) before filtering, so leading scrub lines stay first. Our rules from an earlier run (as
// pfctl prints them back) are not repeated.
inline std::string pfMergeRules(const std::string& passRules, const std::string& current) {
    std::vector<std::string> lines = pfLines(current);
    std::string out;
    size_t i = 0;
    for (; i < lines.size() && lines[i].compare(0, 5, "scrub") == 0; ++i) {
        out += lines[i];
        out += '\n';
    }
    out += passRules;
    for (; i < lines.size(); ++i) {
        if (pfLineIsOurs(lines[i], passRules)) continue;
        out += lines[i];
        out += '\n';
    }
    return out;
}

// True if the loaded rules (`pfctl -sr`) pass TCP `port` to every address in `dstIps`.
inline bool pfRulesHavePass(const std::string& sr, const std::vector<std::string>& dstIps, uint16_t port) {
    std::vector<std::string> lines = pfLines(sr);
    for (size_t i = 0; i < dstIps.size(); ++i) {
        bool found = false;
        for (size_t k = 0; k < lines.size() && !found; ++k) found = pfLinePassesTo(lines[k], dstIps[i], port);
        if (!found) return false;
    }
    return !dstIps.empty();
}

} // namespace nbt

#endif
