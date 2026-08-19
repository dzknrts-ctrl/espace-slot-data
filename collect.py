#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
みんレポ 日次スロットデータ収集 — エスパス上野 新館/本館・秋葉原2店（全台・取りこぼしゼロ版）

要点:
  - データは「末尾別 ?kishu=0..9」の10ページで全台を取得（機種ナビに依存せず完全網羅）
  - 機種名は機種ページ ?kishu=<機種> から付与（付かない台は「不明」だがデータは完全）
  - 本物のブラウザUA＋自動リトライ＋空応答検知で、ブロック/空ページを回避
  - 直近N日をバックフィル（未取得日だけ埋める）。0件でもジョブは失敗させない
使い方:
  python collect.py                 # 直近5日で未取得の日を全台収集
  python collect.py --days 10
  python collect.py --date 8/18
  python collect.py --juggler-only
  python collect.py --force
"""
import argparse, csv, os, re, sys, time, urllib.parse
from datetime import datetime, timedelta, timezone
import requests
from bs4 import BeautifulSoup

BASE = "https://min-repo.com"
HALLS = {
    "shinkan":      {"name": "エスパス日拓上野新館",     "tag": "エスパス日拓上野新館"},
    "honkan":       {"name": "エスパス日拓上野本館",     "tag": "エスパス日拓上野本館"},
    "island_akiba": {"name": "アイランド秋葉原店",       "tag": "アイランド秋葉原店"},
    "espace_akiba": {"name": "エスパス日拓秋葉原駅前店", "tag": "エスパス日拓秋葉原駅前店"},
}
JST = timezone(timedelta(hours=9))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
DELAY = 2.0
BACKFILL_DAYS = 5
PROBE = 14
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
JUGGLER_RE = re.compile(r"ジャグラー")

sess = requests.Session()
sess.headers.update({"User-Agent": UA, "Accept-Language": "ja,en;q=0.8"})

def log(*a): print(*a, flush=True)

def get(url, tries=4, need=None):
    """取得。非200/空応答/needマーカー欠落はリトライ。失敗時は空文字を返す。"""
    last = ""
    for t in range(tries):
        try:
            time.sleep(DELAY if t == 0 else DELAY * (t + 1) + 2)
            r = sess.get(url, timeout=45)
            txt = r.text or ""
            if r.status_code == 200 and len(txt) > 1500 and (need is None or need in txt):
                return txt
            last = f"status={r.status_code} len={len(txt)}"
        except Exception as e:
            last = str(e)
    log(f"    ! 取得失敗 {url} ({last})")
    return ""

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
    html = get(f"{BASE}/tag/{urllib.parse.quote(HALLS[hall]['tag'])}/", need="min-repo.com")
    ids = set()
    for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        m = re.match(r"^https?://min-repo\.com/(\d{7})/?$", a["href"])
        if m:
            ids.add(int(m.group(1)))
    if not ids:
        return []
    mx = max(ids)
    return sorted([i for i in ids if i >= mx - 150000], reverse=True)

def build_date_map(hall):
    dm = {}
    for pid in candidate_ids(hall)[:PROBE]:
        info = page_date_hall(get(f"{BASE}/{pid}/", need="勝率"))
        if not info:
            continue
        m, d, h = info
        if h == hall and (m, d) not in dm:
            dm[(m, d)] = pid
    return dm

def list_models(html):
    """機種ページの kishu= リンク（末尾0-9・ゾロ目z・allは除外）。機種名の付与に使う。"""
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
    m = re.search(r"勝率\D{0,8}(\d+)\s*/\s*(\d+)", BeautifulSoup(html, "html.parser").get_text(" "))
    return int(m.group(2)) if m else None

def _idx(heads, *names):
    for i, h in enumerate(heads):
        if any(n in h for n in names):
            return i
    return None

def _num(cells, i):
    if i is None or i >= len(cells):
        return ""
    v = cells[i]
    return v if re.fullmatch(r"-?\d+", v) else ""

def parse_machines(html):
    """ページ内の「台番」を持つ全テーブルを走査し、台番→データ(dict)で統合して返す。"""
    soup = BeautifulSoup(html, "html.parser")
    out = {}
    for table in soup.find_all("table"):
        heads = [th.get_text(strip=True) for th in table.find_all("th")]
        if not heads:
            first = table.find("tr")
            heads = [c.get_text(strip=True) for c in first.find_all(["td", "th"])] if first else []
        if not any("台番" in h for h in heads):
            continue
        i_no, i_g, i_bb, i_rb, i_sa = (_idx(heads, "台番"), _idx(heads, "G数", "G"),
                                       _idx(heads, "BB"), _idx(heads, "RB"), _idx(heads, "差枚"))
        for tr in table.find_all("tr"):
            cells = [c.get_text(strip=True).replace(",", "") for c in tr.find_all("td")]
            if not cells or i_no is None or i_no >= len(cells):
                continue
            no = cells[i_no]
            if not re.fullmatch(r"\d+", no):
                continue
            row = {"G": _num(cells, i_g), "BB": _num(cells, i_bb),
                   "RB": _num(cells, i_rb), "samai": _num(cells, i_sa)}
            old = out.get(no)
            if old is None:
                out[no] = row
            else:
                for k in ("G", "BB", "RB", "samai"):
                    if not old[k] and row[k]:
                        old[k] = row[k]
    return out

def collect_one(hall, y, m, d, pid, juggler_only):
    date_str = f"{y:04d}-{m:02d}-{d:02d}"
    html0 = get(f"{BASE}/{pid}/", need="勝率")
    if not html0:
        log(f"[{hall}] {date_str} 記事取得失敗→スキップ（次回再挑戦）"); return None
    total = win_total(html0)

    # 1) 末尾0-9 で全台データ（機種名なし・完全網羅）
    data = {}
    for dg in "0123456789":
        h = get(f"{BASE}/{pid}/?kishu={dg}", need="台番")
        for no, row in parse_machines(h).items():
            if row["G"]:
                data[no] = row

    # 2) 機種ページで 台番→機種名 を付与
    models = list_models(html0)
    if juggler_only:
        models = [x for x in models if JUGGLER_RE.search(x)]
    model_of = {}
    for model in models:
        h = get(f"{BASE}/{pid}/?kishu={urllib.parse.quote(model)}", need="台番")
        for no in parse_machines(h):
            model_of[no] = model
    if juggler_only:
        data = {k: v for k, v in data.items() if k in model_of}

    if not data:
        log(f"[{hall}] {date_str} 0台→スキップ"); return None

    rows = [{"date": date_str, "hall": hall, "model": model_of.get(no, "不明"),
             "daban": no, "G": v["G"], "BB": v["BB"], "RB": v["RB"], "samai": v["samai"]}
            for no, v in sorted(data.items(), key=lambda kv: int(kv[0]))]

    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, f"{date_str}_{hall}.csv")
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "hall", "model", "daban", "G", "BB", "RB", "samai"])
        w.writeheader(); w.writerows(rows)
    labeled = sum(1 for r in rows if r["model"] != "不明")
    cov = f"{len(rows)}/{total}" if total else str(len(rows))
    log(f"[{hall}] wrote {len(rows)} rows (全台 {cov} / 機種判明 {labeled}) -> {os.path.relpath(path)}")
    if total and len(rows) < total * 0.95:
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
        targets = [((now - timedelta(days=i)).year, (now - timedelta(days=i)).month,
                    (now - timedelta(days=i)).day) for i in range(1, a.days + 1)]
    log("targets: " + ", ".join(f"{y}-{m:02d}-{d:02d}" for y, m, d in targets))

    wrote_any = False
    for hall in HALLS:
        need = [(y, m, d) for (y, m, d) in targets
                if a.force or not os.path.exists(os.path.join(DATA_DIR, f"{y:04d}-{m:02d}-{d:02d}_{hall}.csv"))]
        if not need:
            log(f"[{hall}] 直近{a.days}日はすべて取得済み、スキップ"); continue
        log(f"[{hall}] 未取得 {len(need)} 日 → タグ検証中 ...")
        try:
            dmap = build_date_map(hall)
        except Exception as e:
            log(f"[{hall}] タグ取得エラー: {e}"); continue
        if not dmap:
            log(f"[{hall}] 日付マップが空（サイト応答不良の可能性・次回再挑戦）"); continue
        for (y, m, d) in sorted(need):
            pid = dmap.get((m, d))
            if not pid:
                log(f"[{hall}] {y}-{m:02d}-{d:02d} 投稿未検出（未掲載かも／次回再挑戦）"); continue
            try:
                if collect_one(hall, y, m, d, pid, a.juggler_only):
                    wrote_any = True
            except Exception as e:
                log(f"[{hall}] {y}-{m:02d}-{d:02d} ERROR: {e}")
    # 1件でも取れていれば成功扱い（部分成功で赤にしない）
    sys.exit(0 if wrote_any else 1)

if __name__ == "__main__":
    main()
