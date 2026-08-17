#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
みんレポ 日次スロットデータ収集 — エスパス日拓上野 新館・本館
GitHub Actions で毎朝1回実行し、前日(既定)の per-台番号 データを data/ に保存する。

方針:
  - タグページから候補 postid を取り、各投稿ページで「日付・館名」を実際に確認してから採用
    （タグのページ送りや関連枠に前年データが混じるため、必ず現物検証する）
  - 1リクエストごとに待機し、単発・低頻度・UA明示でアクセス（サイト負荷配慮）
使い方:
  python collect.py                # 前日(JST)を収集
  python collect.py --date 8/15    # 指定日(当年)を収集
  python collect.py --juggler-only # ジャグラー系のみ
"""
import argparse, csv, os, re, sys, time, urllib.parse
from datetime import datetime, timedelta, timezone
import requests
from bs4 import BeautifulSoup

BASE = "https://min-repo.com"
HALLS = {
    "shinkan": {"name": "エスパス日拓上野新館", "tag": "エスパス日拓上野新館"},
    "honkan":  {"name": "エスパス日拓上野本館", "tag": "エスパス日拓上野本館"},
}
JST = timezone(timedelta(hours=9))
UA = "Mozilla/5.0 (compatible; personal-slot-analysis/1.0; +non-commercial private use)"
DELAY = 2.5  # 秒
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
    """投稿ページの <title>/<h1> から (month,day, hall_name) を得る。"""
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.get_text(" ", strip=True) if soup.title else "")
    h1 = soup.find(["h1", "h2"])
    text = title + " " + (h1.get_text(" ", strip=True) if h1 else "")
    md = re.search(r"(\d{1,2})/(\d{1,2})", text)
    hall = None
    for k, v in HALLS.items():
        if v["name"] in text:
            hall = k; break
    if not md:
        return None
    return (int(md.group(1)), int(md.group(2)), hall)

def candidate_ids(hall):
    """タグページから最新側の候補 postid を降順で返す（前年の低IDは除外）。"""
    tag = urllib.parse.quote(HALLS[hall]["tag"])
    html = get(f"{BASE}/tag/{tag}/")
    ids = set()
    for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        m = re.match(r"^https?://min-repo\.com/(\d{7})/?$", a["href"])
        if m:
            ids.add(int(m.group(1)))
    if not ids:
        return []
    mx = max(ids)
    # 現行年の直近~70日ぶりの範囲のみ（前年 ~百万台 の混入を除外）
    return sorted([i for i in ids if i >= mx - 150000], reverse=True)

def resolve_post(hall, target_md):
    """指定 (month,day) と館に一致する投稿ページを特定して (id, html) を返す。"""
    for pid in candidate_ids(hall)[:8]:
        html = get(f"{BASE}/{pid}/")
        info = page_date_hall(html)
        if not info:
            continue
        m, d, h = info
        log(f"  probe {pid}: {m}/{d} hall={h}")
        if (m, d) == target_md and h == hall:
            return pid, html
    return None, None

def list_models(pid):
    """?kishu=all から機種名リストを取得。"""
    html = get(f"{BASE}/{pid}/?kishu=all")
    models = []
    for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        m = re.search(r"[?&]kishu=([^&]+)", a["href"])
        if not m:
            continue
        name = urllib.parse.unquote(m.group(1))
        if name and name != "all" and name not in models:
            models.append(name)
    return models

def parse_machines(html):
    """per-台番号 テーブルを解析。ヘッダ名からカラム位置を判定。"""
    soup = BeautifulSoup(html, "html.parser")
    rows_out = []
    for table in soup.find_all("table"):
        heads = [th.get_text(strip=True) for th in table.find_all("th")]
        if not heads:
            first = table.find("tr")
            heads = [c.get_text(strip=True) for c in first.find_all(["td", "th"])] if first else []
        if not any("台番" in h for h in heads) or not any(h == "BB" or "BB" in h for h in heads):
            continue
        def idx(*names):
            for i, h in enumerate(heads):
                if any(n in h for n in names):
                    return i
            return None
        i_no, i_g, i_bb, i_rb, i_sa = idx("台番"), idx("G数", "G"), idx("BB"), idx("RB"), idx("差枚")
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
            rows_out.append({"daban": no, "G": num(i_g), "BB": num(i_bb),
                             "RB": num(i_rb), "samai": num(i_sa)})
        if rows_out:
            break
    return rows_out

def collect_hall(hall, target_md, year, juggler_only):
    log(f"[{hall}] resolve {target_md[0]}/{target_md[1]} ...")
    pid, html = resolve_post(hall, target_md)
    if not pid:
        log(f"[{hall}] 投稿が見つかりませんでした（要確認）")
        return None
    models = list_models(pid)
    if juggler_only:
        models = [m for m in models if JUGGLER_RE.search(m)]
    log(f"[{hall}] id={pid} 機種数={len(models)}")
    date_str = f"{year:04d}-{target_md[0]:02d}-{target_md[1]:02d}"
    out_rows = []
    for model in models:
        mhtml = get(f"{BASE}/{pid}/?kishu={urllib.parse.quote(model)}")
        for r in parse_machines(mhtml):
            if not r["G"]:
                continue
            out_rows.append({"date": date_str, "hall": hall, "model": model, **r})
    if not out_rows:
        log(f"[{hall}] 行が取れませんでした（パーサ要確認）")
        return None
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, f"{date_str}_{hall}.csv")
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "hall", "model", "daban", "G", "BB", "RB", "samai"])
        w.writeheader(); w.writerows(out_rows)
    log(f"[{hall}] wrote {len(out_rows)} rows -> {os.path.relpath(path)}")
    return path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="M/D（当年）。省略時は前日(JST)")
    ap.add_argument("--juggler-only", action="store_true")
    ap.add_argument("--force", action="store_true", help="既存ファイルがあっても再取得")
    a = ap.parse_args()
    now = datetime.now(JST)
    if a.date:
        m, d = map(int, a.date.split("/")); year = now.year
    else:
        y = now - timedelta(days=1); m, d, year = y.month, y.day, y.year
    target = (m, d)
    log(f"target = {year}-{m:02d}-{d:02d} (JST now {now:%Y-%m-%d %H:%M})")
    ok = True
    for hall in HALLS:
        path = os.path.join(DATA_DIR, f"{year:04d}-{m:02d}-{d:02d}_{hall}.csv")
        if os.path.exists(path) and not a.force:
            log(f"[{hall}] already exists, skip"); continue
        try:
            if not collect_hall(hall, target, year, a.juggler_only):
                ok = False
        except Exception as e:
            log(f"[{hall}] ERROR: {e}"); ok = False
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
