@echo off
rem Startet das NBT-AAD SSH-Werkzeug (PowerShell) ohne Aenderung der Ausfuehrungsrichtlinie.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0nbt-aad-ssh.ps1" %*
pause
