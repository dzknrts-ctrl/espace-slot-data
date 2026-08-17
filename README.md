# エスパス上野 スロット日次収集（Phase 1）

みんレポからエスパス日拓上野 新館・本館の**台番号別データ（G/BB/RB/差枚）**を毎日1回自動取得し、`data/日付_館.csv` に蓄積します。GitHub Actions で完全自動（人力ゼロ）。

## 仕組み
- 毎朝 **07:10 JST** に前日分を収集（`.github/workflows/daily.yml`）。手動実行（日付指定）も可。
- 各投稿ページで**日付・館名を実際に確認**してから取り込み（前年データ混入を防止）。
- 1リクエストごとに2.5秒待機・UA明示・単発アクセス（サイト負荷に配慮）。
- 出力: `data/2026-08-15_shinkan.csv` … `date,hall,model,daban,G,BB,RB,samai`

## セットアップ（初回のみ・あなたの作業）
1. GitHub にログイン → 新しい**プライベート**リポジトリを作成（例: `espace-slot-data`）。
2. このフォルダ（`juggler-collector` の中身）をそのリポジトリに置いて push。
   ```bash
   cd juggler-collector
   git init
   git add .
   git commit -m "init: daily collector"
   git branch -M main
   git remote add origin https://github.com/<あなた>/espace-slot-data.git
   git push -u origin main
   ```
3. リポジトリの **Settings → Actions → General → Workflow permissions** を
   **Read and write permissions** に設定（data/ の自動コミットに必要）。
4. **Actions** タブ → `daily-collect` → **Run workflow**（date空欄）で手動テスト実行。
   - 成功すると `data/` に前日分の CSV が2つ（新館・本館）追加され自動コミットされます。
   - ログに `probe … / wrote N rows` が出ます。0行や未検出なら連絡ください（セレクタ調整します）。

## 手元での試し実行（任意・Pythonがある環境）
```bash
pip install requests beautifulsoup4
python collect.py --date 8/15 --juggler-only   # 指定日・ジャグラーのみ
python collect.py                               # 前日・全スロット
```

## 注意 / 規約
- 収集対象は自動取得を禁じていないみんレポのみ。**個人・非公開利用**を前提に、低頻度・単発でアクセスします。
- データは参考情報。設定・勝敗を保証するものではありません。
- 規約は変わり得るため、定期的に再確認してください。

## 次フェーズ（予定）
- **Phase 2**: 日付タイプ別（曜日・末尾・0/7/ゾロ目）の本命シマ学習 → 任意の日の狙い台。
- **Phase 3**: 当日リアルタイム判定（日中に複数回取得する別スケジュール）。
