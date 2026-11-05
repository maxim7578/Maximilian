// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Required Notice: Copyright (c) 2026 nanaisu - NBT-AAD (https://github.com/Sq00ky/Supra-iDrive6-Android-Auto)
// The DRIVING_STATUS sensor value sent to the phone (header-only, host-tested in tests/test_driving_status.cpp).
//
// Android Auto restricts what the driver can do while the car moves (no keyboard, short lists and messages, no
// settings, no video) only when the head unit reports it. NBT-AAD has no vehicle speed, and up to now it always
// reported 0 (unrestricted), so those restrictions were off while driving too. The default is now "moving": every
// restriction except voice input, which stays allowed because the Assistant is the way to use the phone while
// driving. NBT_DRIVING_STATUS=<0..31> overrides it (0 = unrestricted, the old behaviour; 31 = all restrictions).
// Bits as in Android Auto's DrivingStatus (aasdk DrivingStatusEnum).
#ifndef NBT_DRIVING_STATUS_HPP
#define NBT_DRIVING_STATUS_HPP

#include "nbt_env.hpp"

namespace nbt {

const unsigned kDriveUnrestricted    = 0;
const unsigned kDriveNoVideo         = 1;
const unsigned kDriveNoKeyboard      = 2;
const unsigned kDriveNoVoice         = 4;
const unsigned kDriveNoConfig        = 8;
const unsigned kDriveLimitMessageLen = 16;
const unsigned kDriveMoving = kDriveNoVideo | kDriveNoKeyboard | kDriveNoConfig | kDriveLimitMessageLen;   // 27

inline unsigned drivingStatus() {
    return (unsigned)envRange("NBT_DRIVING_STATUS", (long)kDriveMoving, 0, 31);
}

} // namespace nbt

#endif
