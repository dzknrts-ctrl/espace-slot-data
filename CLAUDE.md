# スロット出玉 収集＆狙い台システム — 引き継ぎ（最新の実態）

このリポジトリ1つで完結。**どのPC・どのClaudeセッションからでも、ここを読めば現状と操作が全部わかる**ようにしてある。
（注：`HANDOFF.md` は初期の古い内容＝「4店/GitHub Actions不可/requests+bs4」で**現状と食い違う**。本CLAUDE.mdが正。）

## 目的
みんレポ(min-repo.com)から対象ホールの**全台出玉データを毎日収集**し、統計＋イベント日から**その日の狙い台/狙い島**を絞る。的中保証でなく確率的優位の補助。ユーザーは非エンジニアなので、操作は簡潔・自動を優先。

## 対象6店舗（collect.py の HALLS キー）
| key | 店名 | みんレポtag | 台数 | 備考 |
|---|---|---|---|---|
| `shinkan` | エスパス日拓上野新館 | エスパス日拓上野新館 | 377 | 統計が効く。ジャグラー強 |
| `honkan` | エスパス日拓上野本館 | エスパス日拓上野本館 | 375 | マイジャグ主力。月末は効果薄 |
| `island_akiba` | アイランド秋葉原店 | アイランド秋葉原店 | 395 | 看板機種放出型。先読み重要 |
| `espace_akiba` | エスパス日拓秋葉原駅前店 | エスパス日拓秋葉原駅前店 | 522 | 同上。ToLOVE/マギレコ等 |
| `bigdipper` | BIGディッパー門前仲町店 | **ビックディッパー門前仲町店**(ビッ**ク**) | 185 | 2026-07追加。誕生祭11/22 |
| `stardust` | 門前仲町スターダスト | **門前仲町スターダスト**(順序注意) | 159 | 2026-07追加。8のつく日が激熱 |

## パイプライン（クラウドで自動＝PC不要）
- **GitHub Actions `.github/workflows/daily.yml`** が毎日自動実行（PCオフでも動く）。cron(UTC): 08:00/08:30/13:00/20:00 JSTの4回で当日分を収集→分析→ダッシュボード更新→自動commit。
- 反ボット対策：**Playwright(headless Chromium)** でみんレポの `_d2` JSクッキー挑戦を突破（旧requests方式は廃止）。
- 収集URL構造：記事`/{pid}/`、全台=末尾別`/{pid}/?kishu=0..9`、機種名=`/{pid}/?kishu=<機種名>`。全台数=記事の「勝率 x/**y**」のy。
- ダッシュボード：GitHub Pages → https://dzknrts-ctrl.github.io/espace-slot-data/ （スマホ可・ログイン不要）。

## 主要スクリプト（`python <file>` / 環境=Windows, Python 3.12, playwright済）
- `collect.py [--days N|--date M/D] [--hall KEY] [--build-models]` — 収集本体。**--build-modelsは新店で重い/ハング注意**（機種マップは`build_kanban_map.py`推奨）。
- `track.py daily YYYY-MM-DD` — 予測→答え合わせ→当日狙いレポート。
- `pick_today.py YYYY-MM-DD` / `shima.py` — 狙い台/狙い島選定。
- `events.py` — イベントカレンダー（下記）。`analyze.py` `build_dashboard.py` — 集計/ダッシュボード生成。
- `monthly_kishu.py YYYY-MM` + `build_monthly_html.py` — 月間機種別差枚ランキング「データ帳」HTML(reports/monthly.html)。
- `analyze_day8.py <hall> <末尾>` — Nのつく日イベント傾向分析。`day_pattern.py <hall>` — 曜日/末尾/特定日パターン。
- `harvest_x.py`（**現在Xの仕様変更でログアウト閲覧不可＝0件。要ログインセッション**）、`hints_vision.py`（示唆画像OCR、**ANTHROPIC_API_KEY必要**）。

## 検証済みイベント日（events.py）
- 月末=強（本館のみnormal）。espace_akiba: 6のつく日/特定日(1,11,22,25)。island_akiba: 20日。shinkan: 4/7のつく日。honkan: 7のつく日。
- **stardust: 8のつく日=強**（61日検証: 総差枚+19.2万 vs 平常+8.7万）。
- **bigdipper: 誕生祭11/22=強**（22日+21万/11日+19万）＋7のつく日=旧イベ(効果薄)。土日型。

## バックテストのエッジ（狙いの信頼度）
上野2店＝統計が機能（新館seat+266/island+154、本館+207/+182）。秋葉原＝先読み主体（駅前は統計エッジ低い）。**平均差枚>勝率で優先。非ジャグラー/非ハナハナのニッチAタイプは減点。**

## 既知のハマり所
- **スクラッチパッドが作業中にwipeされることがある** → `git checkout -- $(git ls-files --deleted)` で復元。長時間収集は途中でこまめにcommit。
- data/*.csv はCRLF正規化で差分が出る（`.gitattributes`で eol=lf 指定済み、無害）。
- track_record.csv 等はBOM付き→ `encoding="utf-8-sig"` で読む。
- push前に `git pull --rebase origin main`（クラウドの自動commitと衝突するため）。

## 別PC/スマホからの操作
- **見るだけ**：上記ダッシュボードURL（ログイン不要）。
- **指示する**：claude.ai/code かデスクトップアプリで**同じアカウント(dzknrts@gmail.com)にログイン**し、このリポジトリ`dzknrts-ctrl/espace-slot-data`を開く。本CLAUDE.mdを自動で読むので文脈は即引き継がれる。
