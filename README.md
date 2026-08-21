# エスパス4店 スロット出玉 収集＆分析

エスパス日拓上野（新館・本館）＋アイランド秋葉原＋エスパス日拓秋葉原駅前 の**全台データ（台番別 差枚/G/BB/RB/合成/出率）**を毎日みんレポから取得して `data/` に蓄積し、`analyze.py` で狙い台の絞り込みに使うレポートを生成する。

## 対象4店

| key | 店名 | 全台数目安 |
|---|---|---|
| `shinkan` | エスパス日拓上野新館 | 約377 |
| `honkan` | エスパス日拓上野本館 | 約375 |
| `island_akiba` | アイランド秋葉原店 | 約395 |
| `espace_akiba` | エスパス日拓秋葉原駅前店 | 約522 |

## 収集方式（重要）

みんレポは **2026-08頃に反スクレイピング対策**を導入した：
1. **JSロールCookie `_d2`** … 記事/データページは初回、本文の代わりに `_d2` を発行して自分をリロードするだけの小さなシェルを返す。`_d2` は毎回変わり、正しくないと台番データを返さない。→ 単純な `requests` では突破不可。
2. **累積レート制限** … 重いデータページを短時間に多数取得すると空応答を返し、IP単位でクールダウン。

そのため収集は **実ブラウザ（Playwright / Chromium）** で行う。ブラウザがJSを実行して `_d2` を自動処理し、人間ペースで巡回することでレート制限も回避する。1記事あたり base + 末尾別0〜9 の**12ページ**で全台を取得（勝率の分母＝全台数と一致するのを実測確認済み）。

- 日付→記事IDは**タグ一覧ページのタイトル `M/D(曜)` から直接マッピング**（記事を1件ずつ開かない）。
- 台番→機種は `data/models_<hall>.json`（`--build-models` で最新記事から生成）を流用。無い台は機種空欄でもデータは完全。

### 日次自動化＝GitHub Actions（クラウド・PC不要）
**主エンジンは GitHub Actions**（`.github/workflows/daily.yml`）。毎日 02:00 UTC(=11:00 JST) に Playwright で収集→分析→ダッシュボード更新→自動commit する。2026-08-21にクラウドIPでの収集成功を実測確認済み（データセンターIPはブロックされなかった）。PCの電源状態に関係なく動く。
`run_daily.ps1`（タスクスケジューラ用）は同処理をローカルで回すための任意のバックアップ。

## ファイル
- `collect.py` … 収集本体（Playwright）
- `analyze.py` / `shima.py` … 機種別サマリ・台番クセ・日付タイプ / 島単位(全ツッパ/看板島/狙い島)分析
- `track.py` … 予測→答え合わせループ（狙いを記録→翌日採点→的中率/エッジ→`daily_report.md`）
- `harvest_x.py` … 店X(取材/全台/機種/イベント)をPlaywrightで収集→`hints/`（APIキー不要）
- `hints_vision.py` … 示唆画像/メール画像をClaude画像認識で構造化（要 `ANTHROPIC_API_KEY`）
- `email_harvester.gs` … Gmailの店メルマガ→`inbox/`（Google Apps Script）
- `concentration.py` … 島型/単体型の店別・曜日別傾向
- `run_daily.ps1` … ローカルで一括実行（任意のバックアップ）
- `data/` … `YYYY-MM-DD_<hall>.csv`（台番別）, `..._kishu.csv`（機種別集計）, `models_<hall>.json`
- `reports/` … `daily_report.md`(狙い＋答え合わせ), `track_record.csv`(累積成績), `dashboard.html`, 各種CSV
- `hints/` … 先読み示唆（X/画像/メール由来。`<date>_<hall>.json`）／`predictions/` … 日々の狙い記録

## 先読み層（示唆）
出玉データに加え、店の先読み情報を `hints/` に集約して狙いに反映する。
- **X(Twitter)**: `harvest_x.py` が店アカウントをPlaywrightで読取り→取材/全台/機種/イベントを抽出（本館 @ueno_honkan0821 / 新館 @espace_ueno_iyo。秋葉原handleは追記可）。
- **示唆画像/メール画像**: `hints_vision.py`（Claude画像認識）で文字化。婉曲な機種示唆はここで拾う。
- **メール**: `email_harvester.gs` でGmail→`inbox/`。
- 反映: `track.py daily` が `hints/<today>_<hall>.json` を読み、日次レポートに「📢示唆(取材/全台/強調機種)」として反映。効く示唆だけをデータで検証(誕生日/公約は過去実績で裏取り済み=店により有無が異なる)。

## データ形式 `data/YYYY-MM-DD_<hall>.csv`
```
date,hall,model,daban,G,BB,RB,samai,deri,gousei,bb_bunbo,rb_bunbo
```
`samai`=差枚, `deri`=出率%, `gousei`=合成確率の分母(1/x の x), `bb_bunbo`/`rb_bunbo`=BB率/RB率の分母。

## セットアップ（初回のみ）
```powershell
# Python 3.12 と依存
pip install playwright
python -m playwright install chromium
```

## 使い方
```powershell
python collect.py                 # 直近5日で未取得を収集（全4店）
python collect.py --days 20       # 直近20日をバックフィル
python collect.py --date 8/20     # 指定日だけ
python collect.py --hall shinkan  # 店舗限定
python collect.py --build-models  # 台番→機種マップを最新記事から生成/更新
python analyze.py                 # レポート生成（reports/）
```

## 毎日の自動化（タスクスケジューラ）
`run_daily.ps1` を毎朝実行するタスクを登録すると、収集→分析→push まで自動。PCが休止していた日も `--days 5` が未取得日を次回自動で補完する。

## 注意 / 規約
個人・非公開利用前提。低頻度・人間ペースでアクセスする。データは独自調査値であり実数とは異なり得る参考情報。設定・勝敗を保証しない。規約は変わり得るため定期的に再確認する。
