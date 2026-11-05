// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Required Notice: Copyright (c) 2026 nanaisu - NBT-AAD (https://github.com/Sq00ky/Supra-iDrive6-Android-Auto)
// Checks for data received from the phone (TCP/USB session and the Bluetooth WPP link). Header-only so the host
// tests (tests/test_rx_guard.cpp) and the daemon use the same code. Written for GCC 4.4 (gnu++0x), no <atomic>.
#ifndef NBT_RX_GUARD_HPP
#define NBT_RX_GUARD_HPP

#include <stdint.h>
#include <stddef.h>
#include <vector>

namespace nbt {

// ---------- Plaintext frames ----------
// Frames without the encryption flag (0x08) are only allowed on the control channel 0, and there only for
// messages the protocol sends in the clear: VersionRequest/Response (1/2), SSL handshake records (3) and
// AuthComplete (4) before this session's TLS handshake has finished, PingRequest/Response (11/12) at any time
// (aasdk sends pings PLAIN, and we answer them in the clear too). Anything else in plaintext (ServiceDiscovery,
// ByeBye, focus requests, and every message on channels 1..255: sensors, mic, video, audio) is dropped, so a
// host that reaches port 5277 cannot drive the session without doing TLS first. (TLS itself does not check
// the phone's certificate: see aa_cryptor.cpp.)
inline bool plaintextChannelAllowed(uint8_t channel) {
    return channel == 0;
}

inline bool plaintextAllowed(uint8_t channel, uint16_t msgId, bool tlsDone) {
    if (!plaintextChannelAllowed(channel)) return false;
    if (msgId == 11 || msgId == 12) return true;
    return !tlsDone && msgId >= 1 && msgId <= 4;
}

// ---------- Length checks without overflow ----------
// True if `len` bytes starting at `pos` lie inside a buffer of `n` bytes. Written as len <= n - pos, never
// pos + len <= n: with a 32-bit size_t (ARMv7) or a 64-bit varint length the sum wraps and a huge length passed.
inline bool fieldFits(size_t pos, uint64_t len, size_t n) {
    return pos <= n && len <= (uint64_t)(n - pos);
}

// Reads one protobuf varint (at most 10 bytes). False if the buffer ends first or the varint is too long.
inline bool pbReadVarint(const std::vector<uint8_t>& d, size_t& i, uint64_t& v) {
    v = 0;
    for (int sh = 0; sh < 64; sh += 7) {
        if (i >= d.size()) return false;
        uint8_t b = d[i++];
        v |= (uint64_t)(b & 0x7F) << sh;
        if (!(b & 0x80)) return true;
    }
    return false;
}

const uint32_t kPbNotFound = 0xFFFFFFFFu;

// First varint field `field` of the protobuf message starting at `off` (after the 2-byte message id).
// Returns kPbNotFound if it is absent or the message is malformed (truncated, oversized length).
inline uint32_t pbFirstVarint(const std::vector<uint8_t>& d, size_t off, uint32_t field) {
    size_t i = off;
    while (i < d.size()) {
        uint64_t tag;
        if (!pbReadVarint(d, i, tag)) break;
        uint64_t f = tag >> 3;
        unsigned w = (unsigned)(tag & 7);
        if (w == 0) {
            uint64_t v;
            if (!pbReadVarint(d, i, v)) break;
            if (f == field) return (uint32_t)v;
        } else if (w == 2) {
            uint64_t len;
            if (!pbReadVarint(d, i, len) || !fieldFits(i, len, d.size())) break;
            i += (size_t)len;
        } else if (w == 1) {
            if (!fieldFits(i, 8, d.size())) break;
            i += 8;
        } else if (w == 5) {
            if (!fieldFits(i, 4, d.size())) break;
            i += 4;
        } else {
            break;
        }
    }
    return kPbNotFound;
}

// ---------- Reassembly of fragmented messages ----------
// Per channel as before (one H.264 key frame fits easily), plus a cap over all channels: the per-channel cap
// alone allowed 256 channels x 8 MiB = 2 GiB of FIRST/MIDDLE fragments that never get a LAST.
const size_t kReassemblyChannelMax = 8u * 1024u * 1024u;
const size_t kReassemblyTotalMax   = 16u * 1024u * 1024u;

// chanBytes: bytes already queued on this channel; totalBytes: queued on all channels (including this one).
inline bool reassemblyFits(size_t chanBytes, size_t totalBytes, size_t add) {
    if (chanBytes > kReassemblyChannelMax || add > kReassemblyChannelMax - chanBytes) return false;
    if (totalBytes > kReassemblyTotalMax || add > kReassemblyTotalMax - totalBytes) return false;
    return true;
}

} // namespace nbt

#endif
