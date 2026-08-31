# -*- coding: utf-8 -*-
"""看板機種だけに絞った台番→機種マップ生成(軽量・throttle回避)。
直近の機種別集計から『多台設置＆平均差枚上位』の看板機種を~20選び、その機種ページだけ巡回して台番を取得。
models_<hall>.json に統合保存。使い方: python build_kanban_map.py espace_akiba island_akiba
"""
import os, sys, csv, glob, json, time, urllib.parse, statistics as st
from collections import defaultdict
from datetime import date
from playwright.sync_api import sync_playwright
import collect  # BASE/UA/JS_*/goto_data/build_date2pid を再利用

def nf(s):
    try:return float(str(s).replace(",",""))
    except:return None

def kanban_models(hall, recent_days=35, topN=22):
    """直近recent_days内で 台数>=2 の機種を平均差枚(台加重)で上位topN。"""
    agg=defaultdict(lambda:[0.0,0])
    files=sorted(glob.glob(os.path.join(collect.DATA_DIR,f"*_{hall}_kishu.csv")))[-recent_days:]
    for p in files:
        for r in csv.DictReader(open(p,encoding="utf-8")):
            m=(r.get("model")or"").strip(); sa=nf(r.get("avg_samai")); n=int(float(r.get("total_dai")or 0))
            if m and sa is not None and n>=2: agg[m][0]+=sa*n; agg[m][1]+=n
    ranked=sorted(((m,v[0]/v[1]) for m,v in agg.items() if v[1]>0), key=lambda x:-x[1])
    return [m for m,_ in ranked[:topN]]

def build(hall):
    models=kanban_models(hall)
    print(f"[{hall}] 看板機種 {len(models)}件を巡回: {', '.join(m[:12] for m in models[:6])}...", flush=True)
    mp=os.path.join(collect.DATA_DIR,f"models_{hall}.json")
    d2m=json.load(open(mp,encoding="utf-8")) if os.path.exists(mp) else {}
    with sync_playwright() as pw:
        b=pw.chromium.launch(headless=True,args=["--disable-dev-shm-usage","--disable-gpu"])
        page=b.new_context(user_agent=collect.UA,locale="ja-JP").new_page()
        try:
            d2p=collect.build_date2pid(page,hall)
            pid=next(iter(d2p.values()),None)
            if not pid: print(f"[{hall}] pid取得失敗"); b.close(); return
            # 基本記事ページを先に開いて _d2 セッションを確立(これが無いと機種ページが空になる)
            base_ok=collect.goto_data(page,f"{collect.BASE}/{pid}/",marker="勝率")
            print(f"[{hall}] base(pid={pid}) 読込={'OK' if base_ok else 'NG'}",flush=True)
            time.sleep(3)
            got=0
            for i,name in enumerate(models):
                u=f"{collect.BASE}/{pid}/?kishu={urllib.parse.quote(name)}"
                if collect.goto_data(page,u,marker="台番"):
                    for r in page.evaluate(collect.JS_MACHINES): d2m[r["daban"]]=name
                    got+=1
                time.sleep(5)  # gentle pacing
            json.dump(d2m,open(mp,"w",encoding="utf-8"),ensure_ascii=False,indent=0)
            print(f"[{hall}] 完了: {got}/{len(models)}機種取得, マップ計{len(d2m)}台 -> {os.path.basename(mp)}",flush=True)
        finally:
            try:b.close()
            except:pass

if __name__=="__main__":
    for h in (sys.argv[1:] or ["espace_akiba","island_akiba"]):
        build(h); time.sleep(30)
