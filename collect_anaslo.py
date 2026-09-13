#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""アナスロ(ana-slo.com)からBig Apple秋葉原の機種別差枚を収集。
みんレポが差枚を掲載しない店(bigapple)の補完用。取れるのは機種別TOP20(優秀機種・実差枚)。
出力: data/YYYY-MM-DD_<hall>_kishu.csv (みんレポ版と同スキーマ) と models_src_<hall>=anaslo 記録。
使い方: python collect_anaslo.py --hall bigapple --days 62
"""
import argparse, csv, os, re, time, urllib.parse
from datetime import datetime, timedelta, timezone, date
from playwright.sync_api import sync_playwright

BASE="https://ana-slo.com"
JST=timezone(timedelta(hours=9))
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
DATA_DIR=os.path.join(os.path.dirname(os.path.abspath(__file__)),"data")
# アナスロ上の店名(全角ピリオド． に注意)
HALLS_ANASLO={"bigapple":"ビッグアップル．秋葉原店"}
def listing_url(hall):
    return f"{BASE}/"+urllib.parse.quote(f"ホールデータ/東京都/{HALLS_ANASLO[hall]}-データ一覧")+"/"

def log(*a): print(*a, flush=True)
def ni(s):
    try:return int(str(s).replace(",","").replace("+",""))
    except:return None

# 機種別ピックアップ1ブロック: "N位：名前 … 機種別差枚 平均差枚 平均G数 勝率 <total> <avg> <G> <r>%(n/N)"
BLOCK=re.compile(
    r"\d+位：([^\n]+?)\s*\n+\s*機種別差枚\s+平均差枚\s+平均G数\s+勝率\s*\n+\s*"
    r"([+\-]?[\d,]+)\s+([+\-]?[\d,]+)\s+([\d,]+)\s+[\d.]+%\((\d+)\s*/\s*(\d+)\)")

def new_ctx(b, hall):
    ctx=b.new_context(user_agent=UA,locale="ja-JP",
                      extra_http_headers={"Referer":listing_url(hall)})
    ctx.route("**/*", lambda r: r.abort()
              if r.request.resource_type in ("image","media","font") else r.continue_())
    return ctx

def fetch_day(b, hall, dstr):
    name=HALLS_ANASLO[hall]
    url=f"{BASE}/{dstr}-{urllib.parse.quote(name)}-data/"
    text=None
    for attempt in range(2):               # 日ごとに新規コンテキストで1回リトライ
        ctx=new_ctx(b,hall); page=ctx.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_function(
                "() => document.body && /\\d+位：/.test(document.body.innerText) && document.body.innerText.length>1500",
                timeout=35000)
            text=page.evaluate("() => document.body.innerText")
        except Exception:
            text=None
        finally:
            try: ctx.close()
            except Exception: pass
        if text: break
        time.sleep(6)
    if not text: return None
    rows=[]
    for m in BLOCK.finditer(text):
        name_i,tot,avg,g,wn,wN=m.group(1).strip(),ni(m.group(2)),ni(m.group(3)),ni(m.group(4)),m.group(5),m.group(6)
        if not name_i or avg is None: continue
        rows.append({"date":dstr,"hall":hall,"model":name_i,"avg_samai":avg,
                     "avg_G":g if g is not None else "","win":f"{wn}/{wN}",
                     "total_dai":wN,"deri":""})
    return rows

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--hall",default="bigapple")
    ap.add_argument("--days",type=int,default=62)
    ap.add_argument("--date",help="YYYY-MM-DD 単日")
    ap.add_argument("--force",action="store_true")
    a=ap.parse_args()
    now=datetime.now(JST)
    if a.date:
        targets=[a.date]
    else:
        targets=[(now-timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1,a.days+1)]
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True,args=["--disable-dev-shm-usage","--disable-gpu",
                                                 "--js-flags=--max-old-space-size=512"])
        wrote=0
        for dstr in targets:
            path=os.path.join(DATA_DIR,f"{dstr}_{a.hall}_kishu.csv")
            if os.path.exists(path) and not a.force:
                # みんレポ由来の壊れたkishu(avg_samaiが0/±1)は上書きしたい。
                # anaslo版は差枚が数百〜数千なので、最大絶対値>10 なら既に実データ→スキップ。
                try:
                    ex=list(csv.DictReader(open(path,encoding="utf-8")))
                    vals=[abs(float(r.get("avg_samai") or 0)) for r in ex]
                    if vals and max(vals)>10:
                        continue
                except Exception: pass
            rows=fetch_day(b,a.hall,dstr)
            time.sleep(4.0)
            if not rows:
                log(f"[{a.hall}] {dstr} 取得なし(未掲載/描画待ちタイムアウト)"); continue
            os.makedirs(DATA_DIR,exist_ok=True)
            with open(path,"w",encoding="utf-8",newline="") as f:
                w=csv.DictWriter(f,fieldnames=["date","hall","model","avg_samai","avg_G","win","total_dai","deri"])
                w.writeheader(); w.writerows(rows)
            wrote+=1
            log(f"[{a.hall}] {dstr} 機種別{len(rows)}件 -> {os.path.basename(path)}")
        b.close()
        log(f"完了: {wrote}日 書き込み")

if __name__=="__main__":
    main()
