#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""店舗X(Twitter)をPlaywrightで読み、当日の先読み(取材/全台/機種/イベント)を
hints/<date>_<hall>.json に保存する。ログイン不要・APIキー不要。
使い方: python harvest_x.py [YYYY-MM-DD]
"""
import os, re, sys, json, glob, csv
from datetime import date
from playwright.sync_api import sync_playwright

BASE=os.path.dirname(os.path.abspath(__file__))
DATA=os.path.join(BASE,"data"); HINTS=os.path.join(BASE,"hints")
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
# 店キー -> Xハンドル（秋葉原2店のhandleが分かれば追記）
HALLS_X={"honkan":"ueno_honkan0821","shinkan":"espace_ueno_iyo"}

STRONG_KW=["取材","撃パス","全台","全機種全台","周年","S級ホール調査","ピン王","設定6","6確","来店","ライター"]
TORIZAI_KW=["取材","撃パス","来店","ライター"]
ZENDAI_KW=["全台","全機種全台"]
EVENT_KW=["撃パス","S級ホール調査","ファン感謝","周年","ピン王","感謝","超"]

def installed_models():
    ms=set()
    for p in glob.glob(os.path.join(DATA,"*_kishu.csv")):
        for r in csv.DictReader(open(p,encoding="utf-8")):
            m=(r.get("model") or "").strip()
            if m: ms.add(m)
    return sorted(ms,key=len,reverse=True)  # 長い名から照合

def read_x(handle):
    tweets=[]
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True,args=["--disable-blink-features=AutomationControlled","--disable-dev-shm-usage"])
        ctx=b.new_context(user_agent=UA,locale="ja-JP",viewport={"width":1280,"height":1800})
        pg=ctx.new_page()
        try:
            pg.goto(f"https://x.com/{handle}",wait_until="domcontentloaded",timeout=45000)
            pg.wait_for_timeout(6000)
            tweets=pg.evaluate("""() => [...document.querySelectorAll('article')].slice(0,12).map(a=>a.innerText)""")
        except Exception as e:
            print(f"  ! X取得失敗 {handle}: {str(e)[:80]}")
        b.close()
    return tweets

def pick_relevant(tweets, target):
    """当日(target)に関係するツイート本文を選ぶ。M/D一致 or 相対時間(Xh/分)/『本日』。"""
    y,m,d=map(int,target.split("-")); md=f"{m}月{d}日"; md2=f"{m}/{d}"
    rel=[]
    for t in tweets:
        head=t[:400]
        if md in t or md2 in t or "本日" in head or re.search(r"\b\d+h\b",head) or "時間" in head or "分" in head:
            rel.append(t)
    if not rel and tweets:  # 何も一致しなければ最新1件
        rel=[tweets[0]]
    return rel

def extract(hall, tweets, target, models):
    rel=pick_relevant(tweets,target)
    blob="\n".join(rel)
    found_kishu=[mm for mm in models if mm in blob][:6]
    events=sorted({k for k in EVENT_KW if k in blob})
    torizai=any(k in blob for k in TORIZAI_KW)
    zendai=any(k in blob for k in ZENDAI_KW)
    strong=any(k in blob for k in STRONG_KW)
    # rawは関係ツイート先頭を短く
    raw=re.sub(r"\s+"," "," / ".join(rel)[:280])
    return {
        "date":target,"hall":hall,"source":f"X @{HALLS_X[hall]}",
        "event":("・".join(events) + (" 全台系" if zendai else "")).strip(),
        "torizai":torizai,"strength":("strong" if strong else "normal"),
        "kishu":found_kishu,"tanjoubi":[],
        "zendai":zendai,"raw":raw
    }

def main():
    target=sys.argv[1] if len(sys.argv)>1 else date.today().isoformat()
    os.makedirs(HINTS,exist_ok=True)
    models=installed_models()
    for hall,handle in HALLS_X.items():
        out=os.path.join(HINTS,f"{target}_{hall}.json")
        if os.path.exists(out):
            print(f"[{hall}] 既存hintあり→スキップ {os.path.basename(out)}"); continue
        tw=read_x(handle)
        if not tw:
            print(f"[{hall}] ツイート取得0"); continue
        h=extract(hall,tw,target,models)
        json.dump(h,open(out,"w",encoding="utf-8"),ensure_ascii=False,indent=1)
        flag=" ".join(x for x in ["取材" if h["torizai"] else "", "全台" if h["zendai"] else "", "強" if h["strength"]=="strong" else ""] if x)
        print(f"[{hall}] hint保存 {flag} 機種={h['kishu']} event={h['event']}")

if __name__=="__main__":
    main()
