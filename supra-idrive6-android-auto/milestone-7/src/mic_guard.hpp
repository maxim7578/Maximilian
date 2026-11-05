// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Required Notice: Copyright (c) 2026 nanaisu - NBT-AAD (https://github.com/Sq00ky/Supra-iDrive6-Android-Auto)
// Who may open the car microphone (header-only, host-tested in tests/test_mic_guard.cpp).
//
// The TLS handshake does not authenticate the phone (aa_cryptor.cpp: SSL_VERIFY_NONE; the phone side of Android
// Auto has no certificate we could pin). Anything that reaches TCP 5277 can therefore run a session and send
// AVInputOpenRequest on channel 14, which used to start the car microphone and stream it to that host. A real
// wireless phone always does the Bluetooth handshake first (Wi-Fi details over the Android Auto RFCOMM link, which
// needs a paired phone), then joins the Wi-Fi and connects within the 90 s the wireless thread waits. So the
// microphone is only opened for a wireless session that started within kWindowSec of a successful Bluetooth
// handshake (or whose phone does the Bluetooth step while the session runs), or for a USB session (cable in the
// car). A host that only knows the Wi-Fi passphrase, or sits on the car's Ethernet, gets a session without the
// microphone, unless it connects while a paired phone is doing its Bluetooth step (it would then also have taken
// the only session slot from that phone).
//
// NBT_MIC_REQUIRE_BT=0 restores the old behaviour. NBT_WIRELESS=0 (the old outbound scanner, no Bluetooth step)
// keeps the microphone as before.
#ifndef NBT_MIC_GUARD_HPP
#define NBT_MIC_GUARD_HPP

#include <pthread.h>
#include <stdint.h>
#include <stddef.h>
#include "session_owner.hpp"

namespace nbt {

class MicGuard {
public:
    static const uint32_t kWindowSec = 120;   // the wireless thread waits up to 90 s for the TCP connect

    MicGuard() : hs_seen_(false), hs_time_(0), active_(false), base_(false), base_reason_(""), start_(0) {
        pthread_mutex_init(&mutex_, NULL);
    }
    ~MicGuard() { pthread_mutex_destroy(&mutex_); }

    // A paired phone is doing the Bluetooth step: it accepted the Wi-Fi start (WifiStartResponse), the handshake
    // returned true, or its Android Auto Bluetooth link is still open (called about once a second while it is).
    void bluetoothHandshakeOk(uint32_t now) {
        pthread_mutex_lock(&mutex_);
        hs_seen_ = true;
        hs_time_ = now;
        pthread_mutex_unlock(&mutex_);
    }

    void sessionStarted(Transport t, bool wirelessMode, bool requireBt, uint32_t now) {
        pthread_mutex_lock(&mutex_);
        active_ = true;
        start_ = now;
        base_ = true;
        if (t == kTransportUsb) base_reason_ = "USB session (phone on the cable)";
        else if (!requireBt) base_reason_ = "NBT_MIC_REQUIRE_BT=0";
        else if (!wirelessMode) base_reason_ = "NBT_WIRELESS=0 (outbound scanner, no Bluetooth step)";
        else { base_ = false; base_reason_ = ""; }
        pthread_mutex_unlock(&mutex_);
    }

    void sessionEnded() {
        pthread_mutex_lock(&mutex_);
        active_ = false;
        pthread_mutex_unlock(&mutex_);
    }

    // Asked when the phone opens the mic and for every captured chunk: a Bluetooth step that arrives after the
    // session started (phones that report success over Bluetooth only later) counts from then on.
    bool micAllowed() const {
        pthread_mutex_lock(&mutex_);
        bool a = allowedLocked();
        pthread_mutex_unlock(&mutex_);
        return a;
    }

    const char* reason() const {
        pthread_mutex_lock(&mutex_);
        const char* r;
        if (!active_) r = "no session";
        else if (base_) r = base_reason_;
        else if (allowedLocked()) r = "Bluetooth handshake of this phone";
        else if (hs_seen_) r = "no Bluetooth handshake in the 120 s before this session or during it";
        else r = "no Bluetooth handshake since the daemon started";
        pthread_mutex_unlock(&mutex_);
        return r;
    }

private:
    MicGuard(const MicGuard&);
    MicGuard& operator=(const MicGuard&);

    bool allowedLocked() const {
        if (!active_) return false;
        if (base_) return true;
        if (!hs_seen_) return false;
        // Wrap-safe: the last Bluetooth step at most kWindowSec before the session start, or after it.
        return (int32_t)(hs_time_ - start_) >= 0 || (uint32_t)(start_ - hs_time_) <= kWindowSec;
    }

    mutable pthread_mutex_t mutex_;
    bool hs_seen_;
    uint32_t hs_time_;
    bool active_;
    bool base_;
    const char* base_reason_;
    uint32_t start_;
};

} // namespace nbt

#endif
