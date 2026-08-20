@echo off
rem === 日次ランナー（タスクスケジューラ/手動用）===
rem run_daily.ps1 を実行して 収集→分析→push まで行う。
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_daily.ps1"
