#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""月次自動更新: 前月＋当月の 機種別差枚ランキング(JSON)・スプレッドシート風PNG・データ帳・画像ギャラリーを再生成。
毎日のワークフローから呼ぶ(当月は集計途中として日々更新、月初に前月が確定)。使い方: python monthly_update.py
"""
import subprocess, sys, os, json, glob
from datetime import datetime, timedelta, timezone

BASE=os.path.dirname(os.path.abspath(__file__)); PY=sys.executable
REP=os.path.join(BASE,"reports")
JST=timezone(timedelta(hours=9))
HALLS=[("shinkan","エスパス上野新館"),("honkan","エスパス上野本館"),
       ("island_akiba","アイランド秋葉原"),("espace_akiba","エスパス秋葉原駅前"),
       ("bigdipper","BIGディッパー門前仲町"),("stardust","門前仲町スターダスト"),
       ("bigapple","ビッグアップル秋葉原")]

def run(*args):
    subprocess.run([PY]+list(args), cwd=BASE, check=False)

def months_to_refresh():
    now=datetime.now(JST); cur=f"{now.year:04d}-{now.month:02d}"
    first=now.replace(day=1); prevd=first-timedelta(days=1)
    prev=f"{prevd.year:04d}-{prevd.month:02d}"
    return [prev, cur]

def has_data(m):
    p=os.path.join(REP,f"monthly_{m}.json")
    if not os.path.exists(p): return False
    try: return bool(json.load(open(p,encoding="utf-8")).get("halls"))
    except: return False

def build_gallery():
    # 画像が存在する月を新しい順に。各月=全店のPNGを縦積み。
    months=sorted({os.path.basename(p)[:7] for p in glob.glob(os.path.join(REP,"img","2026-*.png"))}, reverse=True)
    data={m:[h for h,_ in HALLS if os.path.exists(os.path.join(REP,"img",f"{m}_{h}.png"))] for m in months}
    names={h:n for h,n in HALLS}
    html=r"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>機種別差枚 画像ギャラリー</title>
<style>
:root{--bg:#f2efe8;--panel:#fff;--ink:#1b1e26;--muted:#6a6f7d;--line:#e2ddd2;--accent:#b4791a}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#12141a;--panel:#1a1d25;--ink:#eceef3;--muted:#8b91a1;--line:#282c37;--accent:#e0a63a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:"Noto Sans JP",system-ui,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:22px 16px 70px}
h1{font-size:22px;margin:0 0 4px}.sub{color:var(--muted);font-size:13px;margin-bottom:16px}
.row{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px}
select{font:inherit;font-weight:700;padding:9px 12px;border:1px solid var(--line);border-radius:9px;background:var(--panel);color:var(--ink)}
a.back{color:var(--accent);font-size:13px;text-decoration:none;margin-left:auto;align-self:center}
figure{margin:0 0 26px;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:10px;overflow-x:auto}
figcaption{font-weight:700;font-size:14px;margin:2px 4px 8px}
img{width:100%;height:auto;display:block;border-radius:6px}
.note{color:var(--muted);font-size:12px;margin-top:8px}
</style></head><body><div class="wrap">
<h1>機種別差枚 画像ギャラリー</h1>
<div class="sub">左＝地雷(マイナス) / 右＝優秀(プラス・黄橙ほど大量放出)。みんレポ自動集計。<b>画像をタップで拡大</b>。</div>
<div class="row"><select id="mon"></select><a class="back" href="./dashboard.html">← ダッシュボードへ</a></div>
<div id="view"></div>
<div class="note">当月は集計途中(日々更新)。上野2店=2月〜 / 門前仲町2店=7月〜。</div>
</div>
<script>
const DATA=__DATA__, NAMES=__NAMES__;
const months=Object.keys(DATA);
const mlabel=m=>m.slice(0,4)+"年 "+(+m.slice(5,7))+"月";
const sel=document.getElementById('mon'), view=document.getElementById('view');
months.forEach(m=>{const o=document.createElement('option');o.value=m;o.textContent=mlabel(m);sel.appendChild(o);});
function render(){const m=sel.value;view.innerHTML=(DATA[m]||[]).map(h=>
  `<figure><figcaption>${NAMES[h]}</figcaption><a href="img/${m}_${h}.png" target="_blank" rel="noopener"><img loading="lazy" src="img/${m}_${h}.png" alt="${NAMES[h]} ${m}"></a></figure>`).join('');}
sel.addEventListener('change',render); if(months.length){sel.value=months[0];} render();
</script></body></html>"""
    html=html.replace("__DATA__",json.dumps(data,ensure_ascii=False)).replace("__NAMES__",json.dumps(names,ensure_ascii=False))
    open(os.path.join(REP,"gallery.html"),"w",encoding="utf-8").write(html)
    print("gallery: months",months)

def main():
    for m in months_to_refresh():
        run("monthly_kishu.py", m)
        if has_data(m):
            run("build_sheet_images.py", m)
    # 統合JSON(全月)→データ帳
    c={"months":[]}
    for p in sorted(glob.glob(os.path.join(REP,"monthly_2026-*.json"))):
        d=json.load(open(p,encoding="utf-8")); c["months"].append(d["month"]); c[d["month"]]=d["halls"]
    open(os.path.join(REP,"monthly_all.json"),"w",encoding="utf-8").write(json.dumps(c,ensure_ascii=False,separators=(",",":")))
    run("build_monthly_html.py")
    build_gallery()
    print("monthly_update done")

if __name__=="__main__":
    main()
