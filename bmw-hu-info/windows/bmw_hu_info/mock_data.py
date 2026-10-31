"""Beispielantworten einer simulierten BMW-Headunit.

Dient nur zum Testen ohne Fahrzeug. Die Werte sind erfunden, aber im
Format an echte NBTEVO-/MGU-Ausgaben angelehnt.
"""

from __future__ import annotations

# Zuordnung: exakter Befehl -> (stdout, exit_code)
ANTWORTEN: dict[str, tuple[str, int]] = {
    "hostname": ("bmw-nbtevo\n", 0),
    "uname -a": (
        "Linux bmw-nbtevo 3.10.49 #1 SMP PREEMPT Tue Jan 1 00:00:00 UTC 2019 "
        "armv7l GNU/Linux\n",
        0,
    ),
    "cat /etc/os-release": (
        'NAME="BMW HeadUnit Linux"\nVERSION="ENTRY_EVO_2019-11"\n'
        'ID=bmw-hu\nPRETTY_NAME="BMW HU NBTevo (Simulation)"\n',
        0,
    ),
    "uptime": (
        " 11:42:07 up 1:23, load average: 0.21, 0.18, 0.15\n",
        0,
    ),
    "date": ("Fri Oct 31 11:42:07 UTC 2025\n", 0),
    "cat /proc/cpuinfo": (
        "processor\t: 0\nmodel name\t: ARMv7 Processor rev 0 (v7l)\n"
        "BogoMIPS\t: 1988.28\nprocessor\t: 1\nmodel name\t: ARMv7 Processor "
        "rev 0 (v7l)\nHardware\t: Jacinto6 (BMW NBTevo)\n",
        0,
    ),
    "cat /proc/meminfo": (
        "MemTotal:        1026048 kB\nMemFree:          312884 kB\n"
        "MemAvailable:     640220 kB\nBuffers:           20480 kB\n",
        0,
    ),
    "df -h": (
        "Filesystem      Size  Used Avail Use% Mounted on\n"
        "/dev/root       1.8G  1.1G  620M  64% /\n"
        "tmpfs           256M   12M  244M   5% /tmp\n"
        "/dev/mmcblk0p9   12G  7.4G  4.0G  65% /opt/bmw/data\n",
        0,
    ),
    "free -m": (
        "              total        used        free      shared\n"
        "Mem:           1002         673         305          11\n"
        "Swap:             0           0           0\n",
        0,
    ),
    "mount": (
        "/dev/root on / type ext4 (ro,relatime)\n"
        "tmpfs on /tmp type tmpfs (rw,nosuid,nodev)\n"
        "/dev/mmcblk0p9 on /opt/bmw/data type ext4 (rw,relatime)\n",
        0,
    ),
    "ip addr": (
        "1: lo: <LOOPBACK,UP> mtu 65536\n    inet 127.0.0.1/8 scope host lo\n"
        "2: eth0: <BROADCAST,MULTICAST,UP> mtu 1500\n"
        "    inet 160.48.199.99/24 scope global eth0\n",
        0,
    ),
    "ip route": (
        "default via 160.48.199.1 dev eth0\n"
        "160.48.199.0/24 dev eth0 proto kernel scope link src 160.48.199.99\n",
        0,
    ),
    "ifconfig -a": (
        "eth0  Link encap:Ethernet  HWaddr 00:1A:2B:3C:4D:5E\n"
        "      inet addr:160.48.199.99  Mask:255.255.255.0\n",
        0,
    ),
    "dmesg": (
        "[    0.000000] Booting Linux on physical CPU 0x0\n"
        "[    1.234567] bmw-hmi: display controller initialised\n"
        "[    2.345678] can0: BMW K-CAN up at 100000 bit/s\n"
        "[    9.876543] usb 1-1: new high-speed USB device number 2\n",
        0,
    ),
    "dmesg | grep -i -E 'error|fail|warn'": (
        "[    3.111222] mmc1: error -110 whilst initialising SD card\n"
        "[    4.222333] WARNING: CPU: 1 PID: 88 at drivers/gpu/hmi.c:204\n",
        0,
    ),
    "journalctl -p err -n 200 --no-pager": (
        "Oct 31 11:40:02 bmw-nbtevo hmi[412]: failed to load skin 'night'\n"
        "Oct 31 11:41:15 bmw-nbtevo connd[511]: BT a2dp stream reset\n",
        0,
    ),
    "grep -rIsoE 'WB[A-HJ-NPR-Z0-9]{15}' /etc /opt /var /mnt /data /persistency": (
        "/etc/bmw/vehicle.cfg:WBA8E9C50GK123456\n",
        0,
    ),
    "find /etc /opt /var /mnt /data /persistency -maxdepth 6 -type f -iname '*vin*'": (
        "/etc/bmw/vin.cfg\n/opt/bmw/data/vehicle_vin.dat\n",
        0,
    ),
    "find /etc /opt /var /mnt /data /persistency -maxdepth 6 -type f -iname '*version*'": (
        "/etc/bmw/sw_version.cfg\n/opt/bmw/hu_version.txt\n",
        0,
    ),
    "find /etc /opt /var /mnt /data /persistency -maxdepth 6 -type f -iname '*swfl*'": (
        "/etc/bmw/swfl_istep.cfg\n",
        0,
    ),
    "find /etc /opt /var /mnt /data /persistency -maxdepth 6 -type f -iname '*istep*'": (
        "/etc/bmw/swfl_istep.cfg\n/persistency/istep.info\n",
        0,
    ),
}

# Fallback, wenn der Befehl erlaubt, aber nicht vorbereitet ist.
UNBEKANNT = ("", 0)


def antwort_fuer(command: str) -> tuple[str, int]:
    """Liefert (stdout, exit_code) fuer einen Befehl."""
    return ANTWORTEN.get(command.strip(), UNBEKANNT)
