#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
みんレポ 日次スロットデータ収集 — エスパス日拓上野 新館・本館（取りこぼしゼロ版）

GitHub Actions で毎朝実行。既定では「直近5日分」を対象にし、まだ取得していない日だけ
収集する（バックフィル）。定時実行が遅延・スキップされても、次回以降が穴を自動で埋める。

方針:
  - タグ最新側の投稿を実際に開いて「日付・館名」を確認してから採用（前年データ混入を防ぐ）
  - 1リクエストごとに待機、単発・低頻度・UA明示（サイト負荷配慮）
使い方:
  python collect.py                 # 直近5日で未取得の日を埋める（全スロット）
  python collect.py --days 10       # 直近10日を対象
  python collect.py --date 8/15     # 指定日(当年)だけ
  python collect.py --juggler-only  # ジャグラー系のみ
  python collect.py --force         # 既存でも再取得
"""
import argparse, csv, os, re, sys, time, urllib.parse
from datetime import datetime, timedelta, timezone
import requests
from bs4 import BeautifulSoup

BASE = "https://min-repo.com"
HALLS = {
    "shinkan":      {"name": "エスパス日拓上野新館",       "tag": "エスパス日拓上野新館"},
    "honkan":       {"name": "エスパス日拓上野本館",       "tag": "エスパス日拓上野本館"},
    "island_akiba": {"name": "アイランド秋葉原店",         "tag": "アイランド秋葉原店"},
    "espace_akiba": {"name": "エスパス日拓秋葉原駅前店",   "tag": "エスパス日拓秋葉原駅前店"},
}
JST = timezone(timedelta(hours=9))
UA = "Mozilla/5.0 (compatible; personal-slot-analysis/1.0; +non-commercial private use)"
DELAY = 2.5           # 秒
BACKFILL_DAYS = 5     # 既定の遡り日数
PROBE = 16            # タグ先頭から検証する投稿数
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
JUGGLER_RE = re.compile(r"ジャグラー")

sess = requests.Session()
sess.headers.update({"User-Agent": UA, "Accept-Language": "ja,en;q=0.8"})

def log(*a): print(*a, flush=True)

def get(url):
    time.sleep(DELAY)
    r = sess.get(url, timeout=30)
    r.raise_for_status()
    return r.text

def page_date_hall(html):
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    h1 = soup.find(["h1", "h2"])
    text = title + " " + (h1.get_text(" ", strip=True) if h1 else "")
    md = re.search(r"(\d{1,2})/(\d{1,2})", text)
    hall = None
    for k, v in HALLS.items():
        if v["name"] in text:
            hall = k; break
    return (int(md.group(1)), int(md.group(2)), hall) if md else None

def candidate_ids(hall):
    tag = urllib.parse.quote(HALLS[hall]["tag"])
    html = get(f"{BASE}/tag/{tag}/")
    ids = set()
    for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        m = re.match(r"^https?://min-repo\.com/(\d{7})/?$", a["href"])
        if m:
            ids.add(int(m.group(1)))
    if not ids:
        return []
    mx = max(ids)  # 現行年の直近側のみ（前年 ~百万台IDを除外）
    return sorted([i for i in ids if i >= mx - 150000], reverse=True)

def build_date_map(hall):
    """タグ先頭の投稿を現物確認して {(month,day): postid} を作る（当該館のみ）。"""
    dm = {}
    for pid in candidate_ids(hall)[:PROBE]:
        try:
            info = page_date_hall(get(f"{BASE}/{pid}/"))
        except Exception as e:
            log(f"  probe {pid} err {e}"); continue
        if not info:
            continue
        m, d, h = info
        log(f"  probe {pid}: {m}/{d} hall={h}")
        if h == hall and (m, d) not in dm:
            dm[(m, d)] = pid
    return dm

def list_models(html):
    """記事ページのHTMLから機種の kishu= リンクを抽出。
    末尾別(?kishu=0..9)・ゾロ目(?kishu=z)・全体(?kishu=all)は機種ではないので除外する。"""
    models = []
    for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        m = re.search(r"[?&]kishu=([^&]+)", a["href"])
        if not m:
            continue
        name = urllib.parse.unquote(m.group(1))
        if name in ("all", "z") or re.fullmatch(r"[0-9]", name):
            continue
        if name and name not in models:
            models.append(name)
    return models

def win_total(html):
    """ヘッダの「勝率 x/y」の y（=その日の全台数の目安）を取り出す。"""
    txt = BeautifulSoup(html, "html.parser").get_text(" ")
    m = re.search(r"勝率\D{0,8}(\d+)\s*/\s*(\d+)", txt)
    return int(m.group(2)) if m else None

def parse_machines(html):
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.find_all("table"):
        heads = [th.get_text(strip=True) for th in table.find_all("th")]
        if not heads:
            first = table.find("tr")
            heads = [c.get_text(strip=True) for c in first.find_all(["td", "th"])] if first else []
        if not any("台番" in h for h in heads):
            continue  # 台番号のある表＝per-台番号テーブル（BB列の有無は問わない＝AT機も拾う）
        def idx(*names):
            for i, h in enumerate(heads):
                if any(n in h for n in names):
                    return i
            return None
        i_no, i_g, i_bb, i_rb, i_sa = idx("台番"), idx("G数", "G"), idx("BB"), idx("RB"), idx("差枚")
        rows = []
        for tr in table.find_all("tr"):
            cells = [c.get_text(strip=True).replace(",", "") for c in tr.find_all("td")]
            if not cells or i_no is None or i_no >= len(cells):
                continue
            no = cells[i_no]
            if not re.fullmatch(r"\d+", no):
                continue
            def num(i):
                if i is None or i >= len(cells):
                    return ""
                v = cells[i]
                return v if re.fullmatch(r"-?\d+", v) else ""
            rows.append({"daban": no, "G": num(i_g), "BB": num(i_bb),
                         "RB": num(i_rb), "samai": num(i_sa)})
        if rows:
            return rows
    return []

def collect_one(hall, y, m, d, pid, juggler_only):
    date_str = f"{y:04d}-{m:02d}-{d:02d}"
    html0 = get(f"{BASE}/{pid}/")            # 記事トップ＝全機種ナビが載るページ
    models = list_models(html0)
    total = win_total(html0)                  # 全台数の目安（勝率の分母）
    if juggler_only:
        models = [x for x in models if JUGGLER_RE.search(x)]
    log(f"[{hall}] {date_str} id={pid} models={len(models)} 全台数(勝率分母)={total}")
    rows, seen = [], set()
    for model in models:
        mh = get(f"{BASE}/{pid}/?kishu={urllib.parse.quote(model)}")
        parsed = parse_machines(mh)
        if not parsed:
            log(f"    ⚠ {model}: テーブル未検出（要確認）")
        for r in parsed:
            if r["G"] and r["daban"] not in seen:
                seen.add(r["daban"])
                rows.append({"date": date_str, "hall": hall, "model": model, **r})
    if not rows:
        log(f"[{hall}] {date_str} 0 rows（パーサ要確認）"); return False
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, f"{date_str}_{hall}.csv")
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "hall", "model", "daban", "G", "BB", "RB", "samai"])
        w.writeheader(); w.writerows(rows)
    cov = f"{len(rows)}/{total}" if total else str(len(rows))
    log(f"[{hall}] wrote {len(rows)} rows (全台 {cov}) -> {os.path.relpath(path)}")
    if total and not juggler_only and len(rows) < total * 0.95:
        log(f"    ⚠ 取得{len(rows)} < 全台{total}：未取得あり（要調整）")
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="M/D（当年）。指定時はその日だけ")
    ap.add_argument("--days", type=int, default=BACKFILL_DAYS, help="遡って埋める日数（既定5）")
    ap.add_argument("--juggler-only", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    now = datetime.now(JST)

    if a.date:
        m, d = map(int, a.date.split("/"))
        targets = [(now.year, m, d)]
    else:
        targets = [((now - timedelta(days=i)).year,
                    (now - timedelta(days=i)).month,
                    (now - timedelta(days=i)).day) for i in range(1, a.days + 1)]
    log("targets: " + ", ".join(f"{y}-{m:02d}-{d:02d}" for y, m, d in targets))

    ok = True
    for hall in HALLS:
        need = [(y, m, d) for (y, m, d) in targets
                if a.force or not os.path.exists(os.path.join(DATA_DIR, f"{y:04d}-{m:02d}-{d:02d}_{hall}.csv"))]
        if not need:
            log(f"[{hall}] 直近{a.days}日はすべて取得済み、スキップ"); continue
        log(f"[{hall}] 未取得 {len(need)} 日 → タグ検証中 ...")
        try:
            dmap = build_date_map(hall)
        except Exception as e:
            log(f"[{hall}] タグ取得エラー: {e}"); ok = False; continue
        for (y, m, d) in sorted(need):
            pid = dmap.get((m, d))
            if not pid:
                log(f"[{hall}] {y}-{m:02d}-{d:02d} 投稿未検出（未掲載かも／次回再挑戦）")
                continue  # ここでは失敗扱いにしない（翌日以降に自動で埋める）
            try:
                if not collect_one(hall, y, m, d, pid, a.juggler_only):
                    ok = False
            except Exception as e:
                log(f"[{hall}] {y}-{m:02d}-{d:02d} ERROR: {e}"); ok = False
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
