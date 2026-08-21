/**
 * エスパス/アイランド各店のP-WORLDメルマガをGmailから収集し、
 * GitHubリポジトリ espace-slot-data の inbox/ に保存する。
 * 収集パイプライン(collect/analyze)がinbox/を読み、狙いに反映する。
 *
 * ■ 初回設定（1回だけ）
 *  1) このコードをGoogle Apps Script(script.google.com)に新規プロジェクトとして貼り付け
 *  2) プロジェクトの設定 → スクリプト プロパティ に以下を追加:
 *       GITHUB_TOKEN = <リポジトリへのcontents:write権限を持つfine-grained PAT>
 *       GITHUB_REPO  = dzknrts-ctrl/espace-slot-data   （既定値と同じなら省略可）
 *  3) harvest を1回手動実行して認可を許可 → inbox/ にファイルが増えることを確認
 *  4) トリガー → harvest を「時間主導・1日おき(毎朝8時など)」で登録
 *
 * ※ P-WORLD配信は差出人が全店共通(members@p-world.co.jp)なので、店の判別は件名で行う。
 */
var REPO = PropertiesService.getScriptProperties().getProperty('GITHUB_REPO') || 'dzknrts-ctrl/espace-slot-data';
var TOKEN = PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');

// 件名に含まれる文字列 → 店キー
var HALL_BY_SUBJECT = [
  ['エスパス日拓上野新館',     'shinkan'],
  ['エスパス日拓上野本館',     'honkan'],
  ['アイランド秋葉原',         'island_akiba'],
  ['エスパス日拓秋葉原駅前',   'espace_akiba']
];

function hallOf(subject) {
  for (var i = 0; i < HALL_BY_SUBJECT.length; i++) {
    if (subject.indexOf(HALL_BY_SUBJECT[i][0]) >= 0) return HALL_BY_SUBJECT[i][1];
  }
  return null;
}

function fmtDate(d) {
  return Utilities.formatDate(d, 'Asia/Tokyo', 'yyyy-MM-dd');
}

function harvest() {
  if (!TOKEN) { throw new Error('GITHUB_TOKEN 未設定（スクリプト プロパティに追加してください）'); }
  // 直近7日のP-WORLD配信を対象（初回は newer_than:30d などに広げてもよい）
  var threads = GmailApp.search('from:members@p-world.co.jp newer_than:7d');
  var n = 0;
  for (var t = 0; t < threads.length; t++) {
    var msgs = threads[t].getMessages();
    for (var m = 0; m < msgs.length; m++) {
      var msg = msgs[m];
      var subject = msg.getSubject() || '';
      var hall = hallOf(subject);
      if (!hall) continue;
      var date = fmtDate(msg.getDate());
      var body = msg.getPlainBody() || '';
      // HTML本文からリンクも拾う（P-WORLD店舗ページ等の先読み情報用）
      var html = msg.getBody() || '';
      var links = (html.match(/https?:\/\/[^"'\s<>]+/g) || []).filter(function (u) {
        return u.indexOf('p-world.co.jp') >= 0 || u.indexOf('unsubscribe') < 0;
      });
      var content = [
        'date: ' + date,
        'hall: ' + hall,
        'subject: ' + subject,
        'received: ' + msg.getDate(),
        '--- links ---',
        links.slice(0, 20).join('\n'),
        '--- body ---',
        body
      ].join('\n');
      var path = 'inbox/' + date + '_' + hall + '.txt';
      if (putFile(path, content, 'mail: ' + date + ' ' + hall)) n++;
    }
  }
  Logger.log('harvested ' + n + ' file(s)');
}

/** GitHub Contents API でファイルを作成/更新。既存なら内容が同じ場合スキップ。 */
function putFile(path, content, message) {
  var api = 'https://api.github.com/repos/' + REPO + '/contents/' + path;
  var headers = { Authorization: 'Bearer ' + TOKEN, Accept: 'application/vnd.github+json' };
  // 既存sha取得
  var sha = null;
  var getRes = UrlFetchApp.fetch(api, { method: 'get', headers: headers, muteHttpExceptions: true });
  if (getRes.getResponseCode() === 200) {
    var cur = JSON.parse(getRes.getContentText());
    sha = cur.sha;
    // 既存と同一内容ならスキップ
    var curContent = Utilities.newBlob(Utilities.base64Decode(cur.content.replace(/\n/g, ''))).getDataAsString();
    if (curContent === content) return false;
  }
  var payload = {
    message: message,
    content: Utilities.base64Encode(Utilities.newBlob(content).getBytes()),
    committer: { name: 'mail-harvester', email: 'actions@users.noreply.github.com' }
  };
  if (sha) payload.sha = sha;
  var res = UrlFetchApp.fetch(api, {
    method: 'put', headers: headers, contentType: 'application/json',
    payload: JSON.stringify(payload), muteHttpExceptions: true
  });
  if (res.getResponseCode() >= 300) {
    Logger.log('PUT失敗 ' + path + ' : ' + res.getResponseCode() + ' ' + res.getContentText());
    return false;
  }
  return true;
}
