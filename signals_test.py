# -*- coding: utf-8 -*-
"""残シグナルの検証(3ヶ月): 曜日/末尾の島偏り、ローテ(全ツッパ間隔)。"""
import csv, glob, os, statistics as st
from collections import defaultdict
from datetime import date
DATA=os.path.join(os.path.dirname(os.path.abspath(__file__)),"data")
HALLS={"shinkan":"上野新館","honkan":"上野本館","island_akiba":"アイランド秋葉原","espace_akiba":"秋葉原駅前"}
def pw(s):
    p=(s or "").split("/")
    try:return int(p[0]),int(p[1])
    except:return 0,0
def corr(xy):
    xy=[(a,b) for a,b in xy if a is not None and b is not None]
    if len(xy)<8:return None,len(xy)
    xs=[a for a,_ in xy];ys=[b for _,b in xy];mx=st.mean(xs);my=st.mean(ys)
    num=sum((a-mx)*(b-my) for a,b in xy);den=(sum((a-mx)**2 for a in xs)*sum((b-my)**2 for b in ys))**0.5
    return (num/den if den else None),len(xy)

def load(hall):
    rows=defaultdict(list) # model -> [(date, wr, zentu)]
    for p in sorted(glob.glob(os.path.join(DATA,f"*_{hall}_kishu.csv"))):
        for r in csv.DictReader(open(p,encoding="utf-8")):
            wn,wN=pw(r.get("win")); n=int(float(r.get("total_dai") or 0)); de=float(r.get("deri") or 0)
            if n<4 or wN==0: continue
            wr=100*wn/wN; rows[(r.get("model") or "").strip()].append((r["date"],wr,wr>=65 and de>=108))
    return rows

print("=== 曜日の島偏り 持続性(島×曜日 勝率 前半vs後半 相関) ===")
for hall,jp in HALLS.items():
    rows=load(hall)
    # (model, weekday) -> winrates split by half of that model's dates
    pairs=[]
    for m,recs in rows.items():
        recs=sorted(recs)
        bywd=defaultdict(list)
        for d,wr,z in recs: bywd[date.fromisoformat(d).weekday()].append(wr)
        for wd,vals in bywd.items():
            if len(vals)<4: continue
            h=len(vals)//2
            pairs.append((st.mean(vals[:h]), st.mean(vals[h:])))
    r,n=corr(pairs)
    print(f"  {jp}: r={r:+.2f} (n={n})" if r is not None else f"  {jp}: n不足({n})")

print("\n=== ローテ検証: 全ツッパからの経過日数 → 当日全ツッパ確率 ===")
for hall,jp in HALLS.items():
    rows=load(hall)
    bucket=defaultdict(lambda:[0,0]) # gapbucket -> [zentu, total]
    for m,recs in rows.items():
        recs=sorted(recs)
        last_z=None
        for i,(d,wr,z) in enumerate(recs):
            if last_z is not None:
                gap=(date.fromisoformat(d)-date.fromisoformat(last_z)).days
                b = "1-3日" if gap<=3 else ("4-7日" if gap<=7 else "8日+")
                bucket[b][0]+= 1 if z else 0; bucket[b][1]+=1
            if z: last_z=d
    base_z=sum(1 for m in rows for d,wr,z in rows[m] if z)
    base_t=sum(len(rows[m]) for m in rows)
    line=" / ".join(f"{k}:{100*v[0]/v[1]:.0f}%(n{v[1]})" for k,v in sorted(bucket.items()))
    print(f"  {jp}: 全体全ツッパ率{100*base_z/base_t:.0f}% | 前回全ツッパから {line}")
