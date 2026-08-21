# -*- coding: utf-8 -*-
"""誕生日効果の検証: 指定機種の日別 平均差枚 を店ごとに並べ、誕生日±1日(前夜祭/当日/翌日)が跳ねたか確認。
使い方: python birthday_backtest.py "東京リベンジャーズ" 2026-08-20 [window=1]
"""
import csv, os, glob, sys, statistics as st
from datetime import date, timedelta
DATA=os.path.join(os.path.dirname(os.path.abspath(__file__)),"data")
HALLS={"shinkan":"上野新館","honkan":"上野本館","island_akiba":"アイランド秋葉原","espace_akiba":"秋葉原駅前"}
def nf(s):
    try:return float(str(s).replace(",",""))
    except:return None
def pw(s):
    p=(str(s)or"").split("/")
    try:return int(p[0]),int(p[1])
    except:return 0,0
key=sys.argv[1]; bday=sys.argv[2]; win=int(sys.argv[3]) if len(sys.argv)>3 else 1
by,bm,bd=map(int,bday.split("-")); bdate=date(by,bm,bd)
windays=[(bdate+timedelta(days=k)).isoformat() for k in range(-win,win+1)]
lbl={ (bdate+timedelta(days=k)).isoformat():("前日" if k==-1 else "当日★" if k==0 else "翌日" if k==1 else f"{k:+d}日") for k in range(-win,win+1)}
print(f"=== 誕生日±{win}日 検証: 「{key}」 誕生日={bday}({['月','火','水','木','金','土','日'][bdate.weekday()]}) ===\n")
for hall,jp in HALLS.items():
    series={}
    for p in sorted(glob.glob(os.path.join(DATA,f"*_{hall}_kishu.csv"))):
        for r in csv.DictReader(open(p,encoding="utf-8")):
            if key in (r.get("model") or ""):
                series[r["date"]]=(nf(r.get("avg_samai")), *pw(r.get("win")), r.get("total_dai"))
    if not series:
        print(f"[{jp}] 設置なし\n"); continue
    vals=[v[0] for v in series.values() if v[0] is not None]
    mean=st.mean(vals) if vals else 0
    ranked=sorted(series.items(), key=lambda kv:(kv[1][0] if kv[1][0] is not None else -9e9), reverse=True)
    rank={d:i+1 for i,(d,_) in enumerate(ranked)}; n=len(series)
    print(f"[{jp}]  期間平均差枚={mean:+.0f} ({n}日)  好調TOP3: "+", ".join(f"{d[5:]}({v[0]:+.0f})" for d,v in ranked[:3]))
    hit=False
    for d in windays:
        if d in series:
            v=series[d]; rk=rank[d]
            flag="◎最高!" if rk==1 else ("○上位" if rk<=3 else "△")
            if rk<=3: hit=True
            print(f"    {d[5:]} {lbl[d]:<3}: {v[0]:+.0f} (勝率{v[1]}/{v[2]}) → {n}日中{rk}位 {flag}")
        else:
            print(f"    {d[5:]} {lbl[d]:<3}: データなし")
    print(f"    → 窓内に上位跳ね: {'あり(誕生日プッシュ示唆)' if hit else 'なし'}\n")
