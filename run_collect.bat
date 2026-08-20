@echo off
rem === みんレポ 日次収集ランナー（自宅PC用・タスクスケジューラ対応） ===
rem このバッチと同じフォルダの collect.py を実行し、結果を run.log に追記する。
cd /d "%~dp0"
echo ==== %date% %time% start ==== >> run.log
python collect.py >> run.log 2>&1
echo ==== %date% %time% end (exit=%errorlevel%) ==== >> run.log
