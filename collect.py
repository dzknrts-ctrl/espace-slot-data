#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
みんレポ 日次スロットデータ収集（Playwright版 / 反スクレイピング対策対応）
  対象: エスパス上野 新館・本館 / アイランド秋葉原 / エスパス秋葉原駅前

背景:
  みんレポは2026-08頃にJSロールCookie(_d2)＋累積レート制限の反スクレイピング対策を
  導入。単純なHTTP(requests)では突破できず空応答/シェルしか得られない。そこで実ブラウザ
  (Playwright/Chromium)でJSを実行させ、人間ペースで巡回して確実に全台データを取得する。

取得方式(1記事=12ページ, ~40秒, 取りこぼしゼロを実測確認):
  - タグ一覧ページから「日付→記事ID」を直接マッピング(記事を1件ずつ開かない)
  - 記事ベースページで 勝率N(総台数) と 機種別集計 と バラエティ(1台機種の台番→機種) を取得
  - 末尾別 ?kishu=0..9 の10ページで全台の台番別データを取得
  - 台番→機種 は data/models_<hall>.json を作っておけば流用(--build-modelsで生成/更新)

出力:
  data/YYYY-MM-DD_<hall>.csv        … 台番別: date,hall,model,daban,G,BB,RB,samai,deri,gousei,bb_bunbo,rb_bunbo
  data/YYYY-MM-DD_<hall>_kishu.csv  … 機種別集計: date,hall,model,avg_samai,avg_G,win,total_dai,deri
  data/models_<hall>.json           … 台番→機種(キャッシュ, 任意)

使い方:
  python collect.py                     # 直近5日で未取得の日を全台収集(全4店)
  python collect.py --days 20           # 直近20日
  python collect.py --date 8/20         # 指定日だけ
  python collect.py --hall shinkan      # 店舗を限定
  python collect.py --build-models      # 台番→機種マップを最新記事から生成/更新
  python collect.py --force             # 既存CSVも上書き
"""
import argparse, csv, os, re, sys, time, json, urllib.parse
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

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
PACE = 2.2          # ページ遷移間の待機(秒)。負荷とレート制限回避のバランス
BACKFILL_DAYS = 5
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def log(*a): print(*a, flush=True)

# ---- ブラウザ側で実行するJS ----
JS_DATE2PID = r"""() => {
  const out=[];
  for(const a of document.querySelectorAll('a[href]')){
    const m=a.href.match(/min-repo\.com\/(\d{7})\/?$/); if(!m) continue;
    const t=(a.innerText||'').trim(); const md=t.match(/(\d{1,2})\/(\d{1,2})/);
    out.push([m[1], md?md[0]:null]);
  }
  return out;
}"""

JS_TOTAL = r"""() => { const m=document.body.innerText.match(/勝率\s*(\d+)\s*\/\s*(\d+)/); return m?parseInt(m[2]):null; }"""

JS_HALLNAME = r"""() => document.title || ''"""

# 末尾別ページ: 台番別の全機能列を取得
JS_MACHINES = r"""() => {
  const num=s=>{ if(s==null) return ''; s=(''+s).replace(/[,%\s]/g,''); return /^-?\d+(\.\d+)?$/.test(s)?s:''; };
  const divb=s=>{ const m=(''+s).match(/1\s*\/\s*([\d,]+)/); return m?m[1].replace(/,/g,''):''; };
  const rows=[];
  for(const tb of document.querySelectorAll('table')){
    const hr=tb.querySelector('tr'); if(!hr) continue;
    const heads=[...hr.querySelectorAll('th,td')].map(x=>x.innerText.trim());
    const iNo=heads.findIndex(h=>h.includes('台番')); if(iNo<0) continue;
    const idx=(...ns)=>{for(let i=0;i<heads.length;i++){if(ns.some(n=>heads[i].includes(n)))return i;}return -1;};
    const iSa=idx('差枚'), iG=idx('G数'), iDe=idx('出率'),
          iBB=heads.findIndex(h=>h==='BB'), iRB=heads.findIndex(h=>h==='RB'),
          iGo=idx('合成'), iBr=idx('BB率'), iRr=idx('RB率');
    for(const tr of tb.querySelectorAll('tr')){
      const c=[...tr.querySelectorAll('td')].map(x=>x.innerText.trim());
      if(!c[iNo]||!/^\d+$/.test(c[iNo])) continue;
      rows.push({daban:c[iNo], samai:num(c[iSa]), G:num(c[iG]), deri:num(c[iDe]),
                 BB:num(c[iBB]), RB:num(c[iRB]), gousei:divb(c[iGo]), bb:divb(c[iBr]), rb:divb(c[iRr])});
    }
  }
  const map={}; for(const r of rows){ if(!(r.daban in map)||(!map[r.daban].G&&r.G)) map[r.daban]=r; }
  return Object.values(map);
}"""

# 記事ベースページ: 機種別集計(model,平均差枚,平均G,勝率,出率)
JS_KISHU_AGG = r"""() => {
  const num=s=>{ if(s==null) return ''; s=(''+s).replace(/[,%\s]/g,''); return /^-?\d+(\.\d+)?$/.test(s)?s:''; };
  const out=[];
  for(const tb of document.querySelectorAll('table')){
    const hr=tb.querySelector('tr'); if(!hr) continue;
    const heads=[...hr.querySelectorAll('th,td')].map(x=>x.innerText.trim());
    const iM=heads.findIndex(h=>h.includes('機種'));
    const iSa=heads.findIndex(h=>h.includes('平均差枚'));
    const iG=heads.findIndex(h=>h.includes('平均G'));
    const iW=heads.findIndex(h=>h.includes('勝率'));
    const iDe=heads.findIndex(h=>h.includes('出率'));
    if(iM<0||iSa<0) continue;              // 機種別集計テーブルのみ
    for(const tr of tb.querySelectorAll('tr')){
      const c=[...tr.querySelectorAll('td')].map(x=>x.innerText.trim());
      if(c.length<2||!c[iM]||c[iM].includes('機種')) continue;
      const win=iW>=0?(c[iW]||''):''; const md=win.match(/(\d+)\s*\/\s*(\d+)/);
      out.push({model:c[iM], avg_samai:num(c[iSa]), avg_G:iG>=0?num(c[iG]):'',
                win:win, total_dai:md?md[2]:'', deri:iDe>=0?num(c[iDe]):''});
    }
  }
  return out;
}"""

# バラエティ等: 台番→機種(1台設置機種)
JS_DABAN2MODEL = r"""() => {
  const res={};
  for(const tb of document.querySelectorAll('table')){
    const hr=tb.querySelector('tr'); if(!hr) continue;
    const h=[...hr.querySelectorAll('th,td')].map(x=>x.innerText.trim());
    const iM=h.findIndex(x=>x.includes('機種')), iN=h.findIndex(x=>x.includes('台番'));
    if(iM<0||iN<0) continue;
    for(const tr of tb.querySelectorAll('tr')){
      const c=[...tr.querySelectorAll('td')].map(x=>x.innerText.trim());
      if(c[iN]&&/^\d+$/.test(c[iN])&&c[iM]) res[c[iN]]=c[iM];
    }
  }
  return res;
}"""

JS_MODEL_LINKS = r"""() => {
  const out=[];
  for(const a of document.querySelectorAll('a[href]')){
    const m=a.href.match(/[?&]kishu=([^&]+)/); if(!m) continue;
    let name=decodeURIComponent(m[1]);
    if(name==='all'||name==='z'||/^[0-9]$/.test(name)) continue;
    if(name && !out.includes(name)) out.push(name);
  }
  return out;
}"""


def goto_data(page, url, marker="台番", tries=4):
    """遷移して本文(markerを含む実データ)が出るまで待つ。_d2チャレンジのreloadを吸収。"""
    for i in range(tries):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except Exception:
            pass
        try:
            page.wait_for_function(
                "(mk) => document.body && document.body.innerText.includes(mk) && document.body.innerText.length>2500",
                arg=marker, timeout=12000)
            return True
        except Exception:
            time.sleep(1.5 * (i + 1))
            try: page.reload(wait_until="domcontentloaded")
            except Exception: pass
    return False


def build_date2pid(page, hall):
    page.goto(f"{BASE}/tag/{urllib.parse.quote(HALLS[hall]['tag'])}/",
              wait_until="domcontentloaded", timeout=45000)
    time.sleep(1.2)
    pairs = page.evaluate(JS_DATE2PID)
    d2p = {}
    for pid, md in pairs:
        if md and md not in d2p:      # 新しい順→最初の出現が当年
            d2p[md] = pid
    return d2p


def load_models(hall):
    p = os.path.join(DATA_DIR, f"models_{hall}.json")
    if os.path.exists(p):
        try: return json.load(open(p, encoding="utf-8"))
        except Exception: return {}
    return {}


def build_models(page, hall, pid):
    """最新記事から 台番→機種 マップを作成(機種ごとの ?kishu=<機種> を巡回)。"""
    if not goto_data(page, f"{BASE}/{pid}/", marker="勝率"):
        return {}
    d2m = dict(page.evaluate(JS_DABAN2MODEL))     # まずバラエティ等
    models = page.evaluate(JS_MODEL_LINKS)
    log(f"[{hall}] build-models: {len(models)} 機種を巡回 ...")
    for name in models:
        u = f"{BASE}/{pid}/?kishu={urllib.parse.quote(name)}"
        if goto_data(page, u, marker="台番"):
            for r in page.evaluate(JS_MACHINES):
                d2m[r["daban"]] = name
        time.sleep(PACE)
    p = os.path.join(DATA_DIR, f"models_{hall}.json")
    os.makedirs(DATA_DIR, exist_ok=True)
    json.dump(d2m, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    log(f"[{hall}] models saved: {len(d2m)} 台 -> {os.path.relpath(p)}")
    return d2m


def collect_one(page, hall, y, m, d, pid, models):
    date_str = f"{y:04d}-{m:02d}-{d:02d}"
    if not goto_data(page, f"{BASE}/{pid}/", marker="勝率"):
        raise RuntimeError("記事取得失敗(throttle?)")
    total = page.evaluate(JS_TOTAL)
    agg = page.evaluate(JS_KISHU_AGG)
    variety = dict(page.evaluate(JS_DABAN2MODEL))
    time.sleep(PACE)

    data = {}
    for dg in "0123456789":
        if goto_data(page, f"{BASE}/{pid}/?kishu={dg}", marker="台番"):
            for r in page.evaluate(JS_MACHINES):
                if r["G"]:
                    data[r["daban"]] = r
        time.sleep(PACE)

    if len(data) < 50:      # 全台数は数百のはず。極端に少ない=throttleの可能性→リトライ対象
        raise RuntimeError(f"取得{len(data)}台のみ(throttle?)")

    def model_of(dab):
        return models.get(dab) or variety.get(dab) or ""

    rows = [{"date": date_str, "hall": hall, "model": model_of(no),
             "daban": no, "G": v["G"], "BB": v["BB"], "RB": v["RB"], "samai": v["samai"],
             "deri": v["deri"], "gousei": v["gousei"], "bb_bunbo": v["bb"], "rb_bunbo": v["rb"]}
            for no, v in sorted(data.items(), key=lambda kv: int(kv[0]))]

    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, f"{date_str}_{hall}.csv")
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date","hall","model","daban","G","BB","RB","samai","deri","gousei","bb_bunbo","rb_bunbo"])
        w.writeheader(); w.writerows(rows)

    # 機種別集計も保存
    if agg:
        pk = os.path.join(DATA_DIR, f"{date_str}_{hall}_kishu.csv")
        with open(pk, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["date","hall","model","avg_samai","avg_G","win","total_dai","deri"])
            w.writeheader()
            for a in agg:
                w.writerow({"date": date_str, "hall": hall, **a})

    labeled = sum(1 for r in rows if r["model"])
    cov = f"{len(rows)}/{total}" if total else str(len(rows))
    log(f"[{hall}] wrote {len(rows)} 台 (全台 {cov} / 機種判明 {labeled}) -> {os.path.relpath(path)}")
    if total and len(rows) < total * 0.95:
        log(f"    ⚠ 取得{len(rows)} < 全台{total}：未取得あり")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="M/D（当年）。指定時はその日だけ")
    ap.add_argument("--days", type=int, default=BACKFILL_DAYS)
    ap.add_argument("--hall", help="店舗キーを限定(shinkan/honkan/island_akiba/espace_akiba)")
    ap.add_argument("--build-models", action="store_true", help="台番→機種マップを最新記事から生成/更新")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    now = datetime.now(JST)

    if a.date:
        m, d = map(int, a.date.split("/"))
        targets = [(now.year, m, d)]
    else:
        targets = [((now - timedelta(days=i)).year, (now - timedelta(days=i)).month,
                    (now - timedelta(days=i)).day) for i in range(1, a.days + 1)]
    halls = [a.hall] if a.hall else list(HALLS)
    log("targets: " + ", ".join(f"{y}-{m:02d}-{d:02d}" for y, m, d in targets))

    LAUNCH_ARGS = ["--disable-dev-shm-usage", "--disable-gpu"]
    wrote_any = False
    with sync_playwright() as p:
        def fresh_browser():
            b = p.chromium.launch(headless=True, args=LAUNCH_ARGS)
            c = b.new_context(user_agent=UA, locale="ja-JP")
            return b, c, c.new_page()

        for hall in halls:
            need = [(y, m, d) for (y, m, d) in targets
                    if a.force or not os.path.exists(os.path.join(DATA_DIR, f"{y:04d}-{m:02d}-{d:02d}_{hall}.csv"))]
            if not need and not a.build_models:
                log(f"[{hall}] 対象日はすべて取得済み、スキップ"); continue

            # 店舗ごとにブラウザを新規起動(メモリ蓄積によるクラッシュ回避)
            browser, ctx, page = fresh_browser()
            try:
                log(f"[{hall}] 未取得 {len(need)} 日 → タグ検証中 ...")
                try:
                    d2p = build_date2pid(page, hall)
                except Exception as e:
                    log(f"[{hall}] タグ取得エラー: {e}"); continue
                if not d2p:
                    log(f"[{hall}] 日付マップが空（次回再挑戦）"); continue

                models = load_models(hall)
                if a.build_models:
                    latest_pid = next(iter(d2p.values()), None)
                    if latest_pid:
                        try: models = build_models(page, hall, latest_pid)
                        except Exception as e: log(f"[{hall}] build-models ERROR: {e}")

                for (y, m, d) in sorted(need):
                    pid = d2p.get(f"{m}/{d}")
                    if not pid:
                        log(f"[{hall}] {y}-{m:02d}-{d:02d} 投稿未検出"); continue
                    ok = False
                    for attempt in range(2):     # クラッシュ/throttle時はブラウザ再起動して1回だけ再試行
                        try:
                            page = ctx.new_page()   # 日ごとに新規ページ
                            if collect_one(page, hall, y, m, d, pid, models):
                                wrote_any = True; ok = True
                            try: page.close()
                            except Exception: pass
                            break
                        except Exception as e:
                            log(f"[{hall}] {y}-{m:02d}-{d:02d} ERROR({attempt}): {str(e)[:80]}")
                            try: browser.close()
                            except Exception: pass
                            time.sleep(30)          # クールダウン
                            browser, ctx, page = fresh_browser()
                    time.sleep(4.0)                 # 日ごとの間隔(throttle抑制)
            finally:
                try: browser.close()
                except Exception: pass
    sys.exit(0 if wrote_any else 1)


if __name__ == "__main__":
    main()

# ci-test: cloud collection validation trigger 20260821T030839Z
