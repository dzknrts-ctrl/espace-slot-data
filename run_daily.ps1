# エスパス4店 日次収集→分析→push（Windowsタスクスケジューラから毎朝実行）
# 家庭用IPで実ブラウザ(Playwright)収集するため、みんレポの反スクレイピング対策を突破できる。
# PCが起動していれば実行。休止していた日も collect.py の --days が未取得日を自動で埋める。
$ErrorActionPreference = "Continue"
$repo = $PSScriptRoot
$py   = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
$log  = Join-Path $repo "run_daily.log"
$env:PYTHONIOENCODING = "utf-8"

"==== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') 収集開始 ====" | Tee-Object -FilePath $log -Append

# 1) 収集（直近5日で未取得を補完）
& $py (Join-Path $repo "collect.py") --days 5 2>&1 | Tee-Object -FilePath $log -Append

# 1.5) 店X先読みを収集(取材/全台/機種/イベント)
& $py (Join-Path $repo "harvest_x.py") ((Get-Date).ToString("yyyy-MM-dd")) 2>&1 | Tee-Object -FilePath $log -Append

# 2) 分析レポート＆ダッシュボード更新
& $py (Join-Path $repo "analyze.py") 2>&1 | Tee-Object -FilePath $log -Append
& $py (Join-Path $repo "build_dashboard.py") 2>&1 | Tee-Object -FilePath $log -Append
$today = (Get-Date).ToString("yyyy-MM-dd")   # 当日の狙い島・狙い台
& $py (Join-Path $repo "shima.py") $today 2>&1 | Tee-Object -FilePath $log -Append
# 予測→答え合わせループ（今日を予測＋未採点の過去予測を採点＋日次レポート）
& $py (Join-Path $repo "track.py") daily $today 2>&1 | Tee-Object -FilePath $log -Append

# 3) 変更があれば commit & push
Set-Location $repo
$changed = git status --porcelain data reports predictions hints
if ($changed) {
    git add data reports predictions hints
    git commit -m "auto: $(Get-Date -Format 'yyyy-MM-dd') collect+analyze" | Tee-Object -FilePath $log -Append
    git push | Tee-Object -FilePath $log -Append
    "pushed." | Tee-Object -FilePath $log -Append
} else {
    "no changes." | Tee-Object -FilePath $log -Append
}
"==== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') 完了 ====" | Tee-Object -FilePath $log -Append
