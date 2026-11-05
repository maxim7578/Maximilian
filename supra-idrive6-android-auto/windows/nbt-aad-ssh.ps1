# NBT-AAD SSH-Werkzeug für Windows
# Verbindet sich über das ENET-Kabel per SSH mit der NBT-Evo-Headunit und erledigt die üblichen Schritte:
# Verbindung testen, Log holen (als Datei auf den Desktop), Status, Installieren/Aktualisieren vom USB-Stick,
# dauerhaftes Log auf dem Stick, iDrive neu starten.
#
# Start: Doppelklick auf "NBT-AAD SSH.bat" (oder: powershell -ExecutionPolicy Bypass -File nbt-aad-ssh.ps1)
# Voraussetzung: Windows 10/11 mit dem eingebauten OpenSSH-Client (Befehl "ssh").
# Bei jedem Schritt fragt ssh nach dem Passwort der Headunit.

param(
    [string]$HeadUnit = "169.254.199.99",   # ENET-Adresse der Headunit (TurboCode-Proxy: 127.0.0.1 und Port 6969)
    [int]$Port = 22,
    [string]$Stick = ""                      # z. B. umass01200; leer = beim Start erkennen
)

# Continue: ssh schreibt Hinweise auf stderr; mit "Stop" bricht PowerShell 5.1 dann ab.
$ErrorActionPreference = "Continue"
$SshOpts = @(
    "-p", "$Port",
    "-o", "HostKeyAlgorithms=+ssh-rsa",
    "-o", "PubkeyAcceptedAlgorithms=+ssh-rsa",
    "-o", "StrictHostKeyChecking=accept-new",
    "-o", "ConnectTimeout=10",
    "-m", "hmac-sha1"
)
$Desktop = [Environment]::GetFolderPath("Desktop")
$PluginDir = "/opt/hmi/ID5/data/ro/Plugins/NbtAad"
$PluginFiles = @("libNbtAad.so", "NbtAad.manifest", "NbtAad.xml", "NbtAad_ALL_Texts.zip", "NbtAad_ALL_Images.zip")

function Write-Titel([string]$t) {
    Write-Host ""
    Write-Host "=== $t ===" -ForegroundColor Cyan
}

function Test-Ssh {
    if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
        Write-Host "Der Windows-SSH-Client fehlt." -ForegroundColor Red
        Write-Host "Einstellungen > Apps > Optionale Features > Feature hinzufügen > 'OpenSSH-Client' installieren."
        Read-Host "Enter zum Beenden"
        exit 1
    }
}

# Führt einen Befehl auf dem Anmelde-Knoten aus (dort, wo ssh ankommt).
function Invoke-Login([string]$cmd) {
    & ssh @SshOpts "root@$HeadUnit" $cmd | Out-Host   # Ausgabe sofort zeigen; die Funktion liefert nur den Exit-Code
    return $LASTEXITCODE
}

# Führt einen Befehl auf hu-omap aus (dort liegen /opt, /mnt/umass..., /fs/sda0), wie "on -f /net/hu-omap/" in der Anleitung.
# Der Befehl darf keine einfachen Anführungszeichen enthalten.
function Invoke-Omap([string]$cmd) {
    if ($cmd.Contains("'")) { throw "interner Fehler: einfaches Anführungszeichen im Befehl" }
    & ssh @SshOpts "root@$HeadUnit" "on -f /net/hu-omap/ /bin/sh -c '$cmd'" | Out-Host
    return $LASTEXITCODE
}

function Get-OmapOutput([string]$cmd) {
    if ($cmd.Contains("'")) { throw "interner Fehler: einfaches Anführungszeichen im Befehl" }
    $out = & ssh @SshOpts "root@$HeadUnit" "on -f /net/hu-omap/ /bin/sh -c '$cmd'" 2>&1
    return ,@($out)
}

function Find-Stick {
    if ($script:Stick) { return $script:Stick }
    Write-Host "Suche den USB-Stick auf der Headunit ..."
    $lines = Get-OmapOutput "ls /mnt/"
    $found = @($lines | ForEach-Object { "$_".Trim() } | Where-Object { $_ -match '^umass[0-9A-Za-z]+$' })
    if ($found.Count -eq 1) {
        $script:Stick = $found[0]
        Write-Host "USB-Stick: /mnt/$($script:Stick)" -ForegroundColor Green
    } elseif ($found.Count -gt 1) {
        Write-Host "Mehrere Sticks gefunden: $($found -join ', ')"
        $script:Stick = Read-Host "Welchen nehmen (Name eingeben)"
    } else {
        Write-Host "Kein USB-Stick unter /mnt gefunden. Ausgabe von ls /mnt/:" -ForegroundColor Yellow
        $lines | ForEach-Object { Write-Host "  $_" }
        $script:Stick = Read-Host "Namen des Sticks eingeben (z. B. umass01200), leer = ohne Stick"
    }
    return $script:Stick
}

function Confirm-Schritt([string]$was) {
    $a = Read-Host "$was  Wirklich ausführen? (j/n)"
    return ($a -eq "j" -or $a -eq "J" -or $a -eq "ja")
}

function Menu-Verbindung {
    Write-Titel "Verbindung testen"
    Invoke-Login "uname -a; echo; echo Knoten:; ls /net/" | Out-Null
    Invoke-Omap "echo; echo hu-omap:; uname -a; echo; echo USB:; ls /mnt/" | Out-Null
}

function Menu-Log {
    Write-Titel "Log holen"
    $s = Find-Stick
    $stamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
    $datei = Join-Path $Desktop "nbt-aad-log_$stamp.txt"
    $quellen = @()
    if ($s) { $quellen += "/mnt/$s/nbt-aad.log", "/mnt/$s/nbt-aad-app.log" }
    $quellen += "/dev/shmem/nbt-aad.log", "/dev/shmem/nbt-aad-app.log"
    $cmd = ""
    foreach ($q in $quellen) {
        $cmd += "if [ -f $q ]; then echo; echo ===== $q =====; tail -n 3000 $q; fi; "
    }
    $cmd += "echo; echo ===== Status =====; ls -l /opt/aa/ $PluginDir/ 2>&1; cat /dev/shmem/nbt-aad-state 2>&1; pidin -f an 2>/dev/null | grep -i nbt-aad"
    $out = Get-OmapOutput $cmd
    $out | Out-File -FilePath $datei -Encoding utf8
    $n = $out.Count
    Write-Host "Gespeichert: $datei ($n Zeilen)" -ForegroundColor Green
    Write-Host "Diese Datei kannst du Claude anhängen."
    Write-Host ""
    Write-Host "Wichtigste Zeilen:" -ForegroundColor Cyan
    $out | Where-Object { "$_" -match 'Wireless\]|TcpServer|BluetoothManager|\[PF\]|\[Mic\]|ERROR|FAILED|refus|session ended|connected over' } |
        Select-Object -Last 40 | ForEach-Object { Write-Host "  $_" }
}

function Menu-Status {
    Write-Titel "Status"
    Invoke-Omap "echo Daemon:; ls -l /opt/aa/ 2>&1; echo; echo Plugin:; ls -l $PluginDir/ 2>&1; echo; echo Zustand:; cat /dev/shmem/nbt-aad-state 2>&1; echo; echo Prozess:; pidin -f an 2>/dev/null | grep -i nbt-aad; echo; echo Einstellungen:; cat /opt/aa/nbt-aad.env 2>&1" | Out-Null
}

# Systempartition beschreibbar machen (auf dem Anmelde-Knoten, wie in der Anleitung des Projekts).
function Set-Beschreibbar {
    Write-Host "Systempartition beschreibbar machen ..."
    $rc = Invoke-Login "mount -o remount rw /net/hu-omap/fs/sda0"
    if ($rc -ne 0) { Write-Host "mount meldet $rc" -ForegroundColor Yellow }
}

function Menu-Installieren {
    Write-Titel "Installieren / Aktualisieren vom USB-Stick"
    $s = Find-Stick
    if (-not $s) { Write-Host "Ohne Stick geht das nicht." -ForegroundColor Red; return }
    $m = "/mnt/$s"
    Write-Host "Erwartet auf dem Stick: $m/nbt-aad und $m/release/ mit $($PluginFiles -join ', ')"
    $check = "ls -l $m/nbt-aad"
    foreach ($f in $PluginFiles) { $check += " $m/release/$f" }
    $rc = Invoke-Omap $check
    if ($rc -ne 0) {
        Write-Host "Auf dem Stick fehlt etwas (siehe oben). Abbruch, nichts verändert." -ForegroundColor Red
        return
    }
    if (-not (Confirm-Schritt "Kopiert nbt-aad nach /opt/aa und die iDrive-App nach $PluginDir (alte Dateien werden als .old aufgehoben).")) { return }
    Set-Beschreibbar
    # Laut Projekt nie über eine laufende Datei kopieren: erst umbenennen, dann kopieren.
    $cmd = "mkdir -p /fs/sda0/opt/aa && " +
           "if [ -f /opt/aa/nbt-aad ]; then mv /opt/aa/nbt-aad /opt/aa/nbt-aad.old; fi && " +
           "cp $m/nbt-aad /opt/aa/nbt-aad && chmod 755 /opt/aa/nbt-aad && " +
           "mkdir -p $PluginDir && " +
           "if [ -f $PluginDir/libNbtAad.so ]; then mv $PluginDir/libNbtAad.so $PluginDir/libNbtAad.so.old; fi"
    foreach ($f in $PluginFiles) { $cmd += " && cp $m/release/$f $PluginDir/$f" }
    $cmd += " && sync && echo && echo KURZTEST: && /opt/aa/nbt-aad --license | head -3 && echo && ls -l /opt/aa/ $PluginDir/"
    $rc = Invoke-Omap $cmd
    if ($rc -eq 0) {
        Write-Host "Installiert. Danach iDrive neu starten (Menüpunkt 6)." -ForegroundColor Green
    } else {
        Write-Host "Fehler beim Installieren (Code $rc). Bitte die Ausgabe oben an Claude schicken." -ForegroundColor Red
    }
}

function Menu-DauerLog {
    Write-Titel "Dauerhaftes Log auf dem USB-Stick"
    $s = Find-Stick
    if (-not $s) { Write-Host "Ohne Stick geht das nicht." -ForegroundColor Red; return }
    Write-Host "Schreibt NBT_LOG_FILE=/mnt/$s/nbt-aad.log in /opt/aa/nbt-aad.env."
    Write-Host "Dann landet jedes Log auf dem Stick, auch ohne den Haken 'Log to USB'."
    if (-not (Confirm-Schritt "Einstellungsdatei schreiben.")) { return }
    Set-Beschreibbar
    $cmd = "touch /opt/aa/nbt-aad.env && grep -v ^NBT_LOG_FILE= /opt/aa/nbt-aad.env > /dev/shmem/nbt-aad.env.neu; " +
           "echo NBT_LOG_FILE=/mnt/$s/nbt-aad.log >> /dev/shmem/nbt-aad.env.neu && " +
           "cp /dev/shmem/nbt-aad.env.neu /opt/aa/nbt-aad.env && rm /dev/shmem/nbt-aad.env.neu && sync && cat /opt/aa/nbt-aad.env"
    $rc = Invoke-Omap $cmd
    if ($rc -eq 0) { Write-Host "Gilt ab dem nächsten Start von Android Auto." -ForegroundColor Green }
}

function Menu-Neustart {
    Write-Titel "iDrive neu starten"
    if (-not (Confirm-Schritt "Der Bildschirm geht kurz aus, die Verbindung kann abbrechen.")) { return }
    Invoke-Omap "sync; OnOffDSICommander appreset" | Out-Null
    Write-Host "Befehl gesendet. Falls kein Menüpunkt erscheint: Ein-/Aus-Knopf der Headunit ca. 30 s halten."
}

Test-Ssh
Write-Host "NBT-AAD SSH-Werkzeug  -  Headunit $HeadUnit, Port $Port" -ForegroundColor Cyan
Write-Host "ssh fragt bei jedem Schritt nach dem Passwort der Headunit."
while ($true) {
    Write-Host ""
    Write-Host "1  Verbindung testen"
    Write-Host "2  Log holen (Datei auf dem Desktop)"
    Write-Host "3  Status anzeigen"
    Write-Host "4  Installieren / Aktualisieren vom USB-Stick"
    Write-Host "5  Dauerhaftes Log auf dem USB-Stick einschalten"
    Write-Host "6  iDrive neu starten"
    Write-Host "0  Beenden"
    $w = Read-Host "Auswahl"
    try {
        switch ($w) {
            "1" { Menu-Verbindung }
            "2" { Menu-Log }
            "3" { Menu-Status }
            "4" { Menu-Installieren }
            "5" { Menu-DauerLog }
            "6" { Menu-Neustart }
            "0" { exit 0 }
            default { Write-Host "Bitte 0 bis 6 eingeben." }
        }
    } catch {
        Write-Host "Fehler: $($_.Exception.Message)" -ForegroundColor Red
    }
}
