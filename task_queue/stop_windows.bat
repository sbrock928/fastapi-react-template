@echo off
REM Stop script for Vibez task queue on Windows

echo Stopping Vibez Task Queue...

REM Stop all Celery processes
taskkill /FI "WINDOWTITLE eq Vibez Celery Beat*" /F
taskkill /FI "WINDOWTITLE eq Vibez Reports Worker*" /F
taskkill /FI "WINDOWTITLE eq Vibez Notifications Worker*" /F
taskkill /FI "WINDOWTITLE eq Vibez Default Worker*" /F
taskkill /FI "WINDOWTITLE eq Vibez Flower Monitoring*" /F

echo Vibez Task Queue stopped successfully!
