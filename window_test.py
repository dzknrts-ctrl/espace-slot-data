# -*- coding: utf-8 -*-
import glob,csv,os,statistics as st
from collections import defaultdict
from datetime import date
def nf(s):
    try:return float(str(s).replace(",",""))
    except:return None
H={"shinkan":"上野新館","honkan":"上野本館","island_akiba":"アイランド秋葉原","espace_akiba":"秋葉原駅前"}
def load(hall):
    dd=defaultdict(dict)
    for p in sorted(glob.glob(f"data/*_{hall}_kishu.csv")):
        d=os.path.basename(p)[:10]
        for r in csv.DictReader(open(p,encoding="utf-8")):
            m=(r.get("model")or"").strip(); sa=nf(r.get("avg_samai")); n=int(float(r.get("total_dai")or 0))
            if m and sa is not None and n>=1: dd[d][m]=(sa,n)
    return dd
def islandEV(dd,W):
    dates=sorted(dd); picks=[];floors=[]
    for i,d in enumerate(dates):
        if i<7: continue
        hist=[x for x in dates[:i] if (date.fromisoformat(d)-date.fromisoformat(x)).days<=W]
        if len(hist)<4: continue
        agg=defaultdict(lambda:[0.0,0,0])
        for hd in hist:
            for m,(sa,n) in dd[hd].items(): agg[m][0]+=sa*n;agg[m][1]+=n;agg[m][2]+=1
        rank=sorted([(m,v[0]/v[1]) for m,v in agg.items() if v[2]>=3 and v[1]>=2*v[2]],key=lambda x:-x[1])[:3]
        today=dd[d]; vals=[today[m][0] for m,_ in rank if m in today]
        if vals:
            fl=[(sa,n) for sa,n in today.values()];floor=sum(s*n for s,n in fl)/sum(n for _,n in fl)
            picks.append(st.mean(vals));floors.append(floor)
    return (st.mean(picks)-st.mean(floors)) if picks else 0
WS=[14,21,28,42,90]
print("=== 島エッジ(直近W日で平均差枚選定, walk-forward) ===")
print("店".ljust(10)+"".join(f"{w}日".rjust(9) for w in WS))
for hall,jp in H.items():
    dd=load(hall)
    print(jp.ljust(10)+"".join(f"{islandEV(dd,W):+8.0f} " for W in WS))
