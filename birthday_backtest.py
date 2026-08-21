# -*- coding: utf-8 -*-
"""誕生日効果の検証: 指定機種の日別 平均差枚/勝率 を店ごとに並べ、誕生日当日が跳ねたか確認。
使い方: python birthday_backtest.py "東京リベンジャーズ" 2026-08-20
"""
import csv, os, glob, sys, statistics as st
from collections import defaultdict
DATA=os.path.join(os.path.dirname(os.path.abspath(__file__)),"data")
HALLS={"shinkan":"上野新館","honkan":"上野本館","island_akiba":"アイランド秋葉原","espace_akiba":"秋葉原駅前"}
def nf(s):
    try:return float(str(s).replace(",",""))
    except:return None
def pw(s):
    p=(str(s)or"").split("/")
    try:return int(p[0]),int(p[1])
    except:return 0,0
key=sys.argv[1]; bday=sys.argv[2]
print(f"=== 誕生日効果検証: 「{key}」 誕生日={bday} ===\n")
for hall,jp in HALLS.items():
    series={}
    for p in sorted(glob.glob(os.path.join(DATA,f"*_{hall}_kishu.csv"))):
        for r in csv.DictReader(open(p,encoding="utf-8")):
            if key in (r.get("model") or ""):
                sa=nf(r.get("avg_samai")); wn,wN=pw(r.get("win")); dai=r.get("total_dai")
                series[r["date"]]=(sa,wn,wN,dai)
    if not series:
        print(f"[{jp}] 設置なし\n"); continue
    vals=[v[0] for v in series.values() if v[0] is not None]
    mean=st.mean(vals) if vals else 0
    ranked=sorted(series.items(), key=lambda kv:(kv[1][0] if kv[1][0] is not None else -9e9), reverse=True)
    rank={d:i+1 for i,(d,_) in enumerate(ranked)}
    n=len(series)
    print(f"[{jp}] 設置 {series.get(bday,('','','',''))[3] or '-'}台  期間平均差枚={mean:+.0f}  ({n}日)")
    bd=series.get(bday)
    if bd:
        mark = "★誕生日"
        print(f"  {bday} {mark}: 平均差枚 {bd[0]:+.0f} / 勝率 {bd[1]}/{bd[2]}  → 期間{n}日中 {rank[bday]}位"
              + ("  ◎当日が最高!" if rank[bday]==1 else ("  ○上位" if rank[bday]<=3 else "  △目立たず")))
    # 上位3日を表示(誕生日が入っているか)
    top=", ".join(f"{d[5:]}({v[0]:+.0f})" for d,v in ranked[:3])
    print(f"  好調日TOP3: {top}\n")
