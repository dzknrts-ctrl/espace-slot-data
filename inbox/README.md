# inbox/ — 店舗メルマガ（先読み情報）

各店のP-WORLDメルマガをGmailから収集して置く場所。`email_harvester.gs`（Google Apps Script）が
`inbox/YYYY-MM-DD_<hall>.txt` の形式で自動保存する。収集パイプラインがここを読み、イベント日・
強調機種・取材などの先読み情報を狙い（狙い島・狙い台）に反映する。

- 送信元は全店共通 `members@p-world.co.jp`、店の判別は件名の店名で行う。
- 手動で入れる場合も、同じファイル名・「date:/hall:/subject:/--- body ---」形式で置けば解析対象になる。
- hall キー: shinkan / honkan / island_akiba / espace_akiba
