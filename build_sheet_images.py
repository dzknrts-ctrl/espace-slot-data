#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""月間機種別差枚を『スプレッドシート画像』風に各店PNG出力。
左=地雷(マイナス/赤字)・右=優秀(プラス/黄・橙ハイライト)・上部に店名＋総差枚。
使い方: python build_sheet_images.py 2026-09
出力: reports/img/<month>_<hall>.png
"""
import json, os, sys, html
from playwright.sync_api import sync_playwright

BASE=os.path.dirname(os.path.abspath(__file__))
MONTH=sys.argv[1] if len(sys.argv)>1 else "2026-09"
DATA=json.load(open(os.path.join(BASE,"reports",f"monthly_{MONTH}.json"),encoding="utf-8"))
MLABEL=f"{int(MONTH[5:7])}月"
NEG_MAX=20   # 左(地雷)最大行
POS_MAX=24   # 右(優秀)最大行

def fmt(n): return ("+" if n>0 else "")+format(n,",")

def heat(sa, mx):
    r=sa/mx if mx else 0
    if r>=0.55: return "#ffff2e"      # 黄=大量放出
    if r>=0.30: return "#ffd24d"      # 濃橙
    if r>=0.12: return "#ffe1a6"      # 薄橙
    return "#ffffff"

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#fff;font-family:'Meiryo','Yu Gothic','MS PGothic',sans-serif}
.sheet{width:1360px;padding:14px 16px 18px;background:#fff}
.title{font-size:26px;font-weight:700;color:#111;padding:6px 4px 12px;letter-spacing:.02em}
.title .tot{margin-left:14px}
.cols{display:flex;gap:22px}
table{width:50%;border-collapse:collapse;table-layout:fixed}
col.kishu{width:78%} col.sa{width:22%}
th{font-size:19px;font-weight:700;padding:7px 8px;border:1px solid #b7b7b7;text-align:center}
th.k{}
.neg th{background:#9dc3e6}          /* 青=地雷側ヘッダ */
.pos th{background:#a9d08e}          /* 緑=優秀側ヘッダ */
td{font-size:17px;padding:5px 9px;border:1px solid #c9c9c9;line-height:1.25;
   white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
td.sa{text-align:right;font-variant-numeric:tabular-nums;font-weight:700}
td.neg{color:#c00000}
td.pos{color:#1a1a1a}
"""

def rows_html(items, side, mx):
    out=[]
    for it in items:
        nm=html.escape(it["model"]); sa=it["sa"]
        if side=="neg":
            out.append(f'<tr><td>{nm}</td><td class="sa neg">{fmt(sa)}</td></tr>')
        else:
            bg=heat(sa,mx)
            out.append(f'<tr style="background:{bg}"><td>{nm}</td><td class="sa pos">{fmt(sa)}</td></tr>')
    return "".join(out)

def sheet_html(h):
    models=h["models"]
    pos=[m for m in models if m["sa"]>0][:POS_MAX]
    neg=sorted([m for m in models if m["sa"]<0],key=lambda m:m["sa"])[:NEG_MAX]
    mx=max((m["sa"] for m in pos),default=1)
    total=h["total"]; tcol="#c00000" if total<0 else "#111"
    return f"""<div class="sheet" id="{h['hall']}">
 <div class="title">【{MLABEL}集計】{html.escape(h['name'])}<span class="tot" style="color:{tcol}">{fmt(total)}</span></div>
 <div class="cols">
  <table class="neg"><colgroup><col class="kishu"><col class="sa"></colgroup>
   <tr><th class="k">機種</th><th>差枚</th></tr>{rows_html(neg,'neg',mx)}</table>
  <table class="pos"><colgroup><col class="kishu"><col class="sa"></colgroup>
   <tr><th class="k">機種</th><th>差枚</th></tr>{rows_html(pos,'pos',mx)}</table>
 </div></div>"""

def main():
    halls=DATA["halls"]
    body="".join(sheet_html(h) for h in halls)
    page_html=f"<!doctype html><meta charset='utf-8'><style>{CSS}</style>{body}"
    tmp=os.path.join(BASE,"reports",f"_sheets_{MONTH}.html")
    open(tmp,"w",encoding="utf-8").write(page_html)
    outdir=os.path.join(BASE,"reports","img"); os.makedirs(outdir,exist_ok=True)
    made=[]
    with sync_playwright() as p:
        b=p.chromium.launch()
        pg=b.new_context(device_scale_factor=2).new_page()
        pg.goto("file:///"+tmp.replace("\\","/"))
        pg.wait_for_timeout(400)
        for h in halls:
            fn=os.path.join(outdir,f"{MONTH}_{h['hall']}.png")
            pg.locator(f"#{h['hall']}").screenshot(path=fn)
            made.append(fn); print("wrote",os.path.basename(fn))
        b.close()
    os.remove(tmp)
    print("DONE",len(made))

if __name__=="__main__":
    main()
