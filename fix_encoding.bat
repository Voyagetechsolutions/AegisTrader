@echo off
REM Fix Windows console encoding for Python Unicode output
chcp 65001 >nul
python run_complete_system.py
