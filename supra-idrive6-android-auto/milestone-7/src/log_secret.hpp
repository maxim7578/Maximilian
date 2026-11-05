// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Required Notice: Copyright (c) 2026 nanaisu - NBT-AAD (https://github.com/Sq00ky/Supra-iDrive6-Android-Auto)
// Secrets in the log (header-only, host-tested in tests/test_log_secret.cpp).
//
// The Wi-Fi Direct passphrase used to be printed in clear text so it could be typed on a phone by hand. The log goes
// to a USB stick or /dev/shmem, and with the passphrase anyone holding the log can join the car's Wi-Fi and reach
// TCP 5277. It is now hidden unless NBT_LOG_WFD_PASS=1 asks for it (for that manual DIRECT test).
#ifndef NBT_LOG_SECRET_HPP
#define NBT_LOG_SECRET_HPP

#include <stdio.h>
#include <string>
#include "nbt_env.hpp"

namespace nbt {

inline bool logWfdPassphrase() {
    return envFlag("NBT_LOG_WFD_PASS") == 1;
}

inline std::string secretForLog(const std::string& secret, bool reveal) {
    if (reveal) return "'" + secret + "'";
    char buf[96];
    snprintf(buf, sizeof(buf), "<hidden, %u chars; NBT_LOG_WFD_PASS=1 shows it>", (unsigned)secret.size());
    return buf;
}

} // namespace nbt

#endif
