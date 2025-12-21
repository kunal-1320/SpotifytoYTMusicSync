@echo off
REM Spotify to YouTube Music Sync - Windows Startup Script
REM Place this file in shell:startup to auto-run on login

REM Change to your project directory
cd /d %~dp0

REM Wait 30 seconds for network to be ready
timeout /t 30 /nobreak > nul

REM Run the sync script
python sync_playlists.py

REM Uncomment the line below to keep window open and see results
REM pause
