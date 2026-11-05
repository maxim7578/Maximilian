// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Required Notice: Copyright (c) 2026 nanaisu - NBT-AAD (https://github.com/Sq00ky/Supra-iDrive6-Android-Auto)
// Trust checks for the head unit's own side (header-only, host-tested in tests/test_local_trust.cpp).
//
// touchSenderAllowed(): the touch controller (160.48.199.115:30501 on the cars seen) and the gesture camera send
// UDP to port 30567 on the vehicle network. The forwarder used to take the first sender of a touch PDU as the
// controller, save it in /var/opt/aa/touch-peer and pass its touches to the phone. A host on the Android Auto
// Wi-Fi could therefore tap on the phone while Android Auto was on screen, and take the controller's place for good.
// Touch PDUs from the Android Auto Wi-Fi networks are now dropped and never learned.
//
// pidIsNbtAad(): the iDrive app's Force Stop sends SIGTERM / SIGKILL to the pid in /dev/shmem/nbt-aad-state. It
// now first checks that this pid really runs nbt-aad (/proc/<pid>/exefile), so a pid written there by something else
// is not killed.
#ifndef NBT_LOCAL_TRUST_HPP
#define NBT_LOCAL_TRUST_HPP

#include <stdio.h>
#include <string.h>
#include <stddef.h>

namespace nbt {

// peerHostOrder: the sender (host order). nets: /24s read from uap0 / wfd0 (host order), in addition to the
// default CarPlay AP 172.16.224.0/24 and Wi-Fi Direct 172.16.222.0/24 networks.
inline bool touchSenderAllowed(unsigned peerHostOrder, const unsigned* nets, size_t count) {
    static const unsigned kAaDefaults[2] = { 0xAC10E000u, 0xAC10DE00u };
    const unsigned p = peerHostOrder & 0xffffff00u;
    for (size_t i = 0; i < 2; ++i) if (p == kAaDefaults[i]) return false;
    for (size_t i = 0; i < count; ++i) if (p == (nets[i] & 0xffffff00u)) return false;
    return true;
}

// True if an executable path (as /proc/<pid>/exefile reports it, trailing newline allowed) is nbt-aad.
inline bool exePathIsNbtAad(const char* path) {
    if (!path) return false;
    static const char kTail[] = "/nbt-aad";
    size_t n = strlen(path);
    while (n > 0 && (path[n - 1] == '\n' || path[n - 1] == '\r' || path[n - 1] == ' ')) --n;
    const size_t t = sizeof(kTail) - 1;
    return n >= t && strncmp(path + n - t, kTail, t) == 0;
}

// Reads <procRoot>/<pid>/exefile. procRoot: "/proc" on the head unit (a temporary directory in the host test).
inline bool readExePath(const char* procRoot, int pid, char* buf, size_t len) {
    if (pid <= 0 || len == 0) return false;
    char p[128];
    snprintf(p, sizeof(p), "%s/%d/exefile", procRoot, pid);
    FILE* f = fopen(p, "r");
    if (!f) return false;
    size_t n = fread(buf, 1, len - 1, f);
    fclose(f);
    buf[n] = 0;
    return n > 0;
}

// True only if the pid is shown to run nbt-aad.
inline bool pidIsNbtAad(const char* procRoot, int pid) {
    char buf[256];
    return readExePath(procRoot, pid, buf, sizeof(buf)) && exePathIsNbtAad(buf);
}

// True only if the pid is shown to run something else. Not every QNX process has a readable exefile (mmr_launch.cpp
// falls back to procfs_debuginfo for that), so an unreadable one is not taken as proof: Force Stop still works then.
inline bool pidIsOtherProgram(const char* procRoot, int pid) {
    char buf[256];
    return readExePath(procRoot, pid, buf, sizeof(buf)) && !exePathIsNbtAad(buf);
}

} // namespace nbt

#endif
