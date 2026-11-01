"""Startskript fuer die gebuendelte Windows-.exe (PyInstaller-Einstieg).

Nutzt einen absoluten Import, damit die App auch als eigenstaendiges
Skript (ausserhalb von `python -m bmw_hu_info`) startet.
"""

from bmw_hu_info.gui import main

if __name__ == "__main__":
    raise SystemExit(main())
