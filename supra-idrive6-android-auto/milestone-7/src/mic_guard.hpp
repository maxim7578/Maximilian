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
// handshake, or for a USB session (cable in the car). A host that only knows the Wi-Fi passphrase, or sits on the
// car's Ethernet, gets a session without the microphone.
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

    MicGuard() : hs_seen_(false), hs_time_(0), allowed_(false), reason_("no session") {
        pthread_mutex_init(&mutex_, NULL);
    }
    ~MicGuard() { pthread_mutex_destroy(&mutex_); }

    // The phone accepted the Wi-Fi details over Bluetooth (runWirelessHandshake() returned true).
    void bluetoothHandshakeOk(uint32_t now) {
        pthread_mutex_lock(&mutex_);
        hs_seen_ = true;
        hs_time_ = now;
        pthread_mutex_unlock(&mutex_);
    }

    // Decides once per session; micAllowed() answers for the rest of it.
    void sessionStarted(Transport t, bool wirelessMode, bool requireBt, uint32_t now) {
        pthread_mutex_lock(&mutex_);
        if (t == kTransportUsb) {
            allowed_ = true;  reason_ = "USB session (phone on the cable)";
        } else if (!requireBt) {
            allowed_ = true;  reason_ = "NBT_MIC_REQUIRE_BT=0";
        } else if (!wirelessMode) {
            allowed_ = true;  reason_ = "NBT_WIRELESS=0 (outbound scanner, no Bluetooth step)";
        } else if (hs_seen_ && (uint32_t)(now - hs_time_) <= kWindowSec) {
            allowed_ = true;  reason_ = "Bluetooth handshake just before this session";
        } else {
            allowed_ = false;
            reason_ = hs_seen_ ? "no Bluetooth handshake in the 120 s before this session"
                               : "no Bluetooth handshake since the daemon started";
        }
        pthread_mutex_unlock(&mutex_);
    }

    void sessionEnded() {
        pthread_mutex_lock(&mutex_);
        allowed_ = false;
        reason_ = "no session";
        pthread_mutex_unlock(&mutex_);
    }

    bool micAllowed() const {
        pthread_mutex_lock(&mutex_);
        bool a = allowed_;
        pthread_mutex_unlock(&mutex_);
        return a;
    }

    const char* reason() const {
        pthread_mutex_lock(&mutex_);
        const char* r = reason_;
        pthread_mutex_unlock(&mutex_);
        return r;
    }

private:
    MicGuard(const MicGuard&);
    MicGuard& operator=(const MicGuard&);

    mutable pthread_mutex_t mutex_;
    bool hs_seen_;
    uint32_t hs_time_;
    bool allowed_;
    const char* reason_;
};

} // namespace nbt

#endif
