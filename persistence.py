# -*- coding: utf-8 -*-
"""各シグナルが『本物か』を持続性で検証する。
期間を前半/後半に分け、指標が前半→後半で相関するか(=予測力があるか)を見る。
相関が高い=安定した実在シグナル、ゼロ付近=ノイズ(でっち上げ)。
検証対象:
  A) 看板島(島の全ツッパ率)     … 島単位の店の優遇は持続するか
  B) 島の勝率                  … 島の強さは持続するか
  C) 台の一貫プラス率           … 個別台のクセは持続するか
"""
import csv, glob, os, statistics as st
from collections import defaultdict
DATA=os.path.join(os.path.dirname(os.path.abspath(__file__)),"data")
HALLS={"shinkan":"上野新館","honkan":"上野本館","island_akiba":"アイランド秋葉原","espace_akiba":"秋葉原駅前"}
def pw(s):
    p=(s or "").split("/")
    try:return int(p[0]),int(p[1])
    except:return 0,0
def ni(s):
    try:return int(float(str(s).replace(",","")))
    except:return None
def corr(xy):
    xy=[(a,b) for a,b in xy if a is not None and b is not None]
    if len(xy)<5: return None,len(xy)
    xs=[a for a,_ in xy]; ys=[b for _,b in xy]
    mx=st.mean(xs); my=st.mean(ys)
    num=sum((a-mx)*(b-my) for a,b in xy)
    den=(sum((a-mx)**2 for a in xs)*sum((b-my)**2 for b in ys))**0.5
    return (num/den if den else None), len(xy)

def halves(dates):
    dates=sorted(dates); h=len(dates)//2
    return set(dates[:h]), set(dates[h:])

def main():
    print("持続性検証: 前半の指標が後半でも成り立つか(相関r)。r高=実在シグナル / r≈0=ノイズ\n")
    print(f"{'店':<10}{'A.看板島(全ツッパ率)':>20}{'B.島の勝率':>14}{'C.台の一貫プラス率':>18}")
    for hall,jp in HALLS.items():
        # 島データ
        isl=defaultdict(dict)  # date->model->(zentu, wr)
        seat=defaultdict(dict) # date->daban->plus(0/1)
        dates=set()
        for p in sorted(glob.glob(os.path.join(DATA,f"*_{hall}_kishu.csv"))):
            for r in csv.DictReader(open(p,encoding="utf-8")):
                wn,wN=pw(r.get("win")); n=ni(r.get("total_dai")) or 0
                if n<4 or wN==0: continue
                wr=100*wn/wN
                de=float(r.get("deri") or 0)
                isl[r["date"]][(r.get("model") or "").strip()]=(1 if (wr>=65 and de>=108) else 0, wr)
                dates.add(r["date"])
        for p in sorted(glob.glob(os.path.join(DATA,f"*_{hall}.csv"))):
            if p.endswith("_kishu.csv"): continue
            for r in csv.DictReader(open(p,encoding="utf-8")):
                sa=ni(r.get("samai"))
                if sa is None: continue
                seat[r["date"]][str(r.get("daban"))]=1 if sa>0 else 0
                dates.add(r["date"])
        h1,h2=halves(dates)
        # A) 看板島: 島ごと 全ツッパ率 h1 vs h2
        models=set()
        for d in isl: models|=set(isl[d])
        def isl_rate(days,model,idx):
            vals=[isl[d][model][idx] for d in days if model in isl.get(d,{})]
            return st.mean(vals) if vals else None
        A=[(isl_rate(h1,m,0),isl_rate(h2,m,0)) for m in models]
        B=[(isl_rate(h1,m,1),isl_rate(h2,m,1)) for m in models]
        # C) 台ごと プラス率 h1 vs h2
        dabans=set()
        for d in seat: dabans|=set(seat[d])
        def seat_rate(days,dab):
            vals=[seat[d][dab] for d in days if dab in seat.get(d,{})]
            return st.mean(vals) if len(vals)>=2 else None
        C=[(seat_rate(h1,x),seat_rate(h2,x)) for x in dabans]
        ra,na=corr(A); rb,nb=corr(B); rc,nc=corr(C)
        def f(r,n): return (f"{r:+.2f}(n={n})" if r is not None else f"-(n={n})")
        print(f"{jp:<10}{f(ra,na):>20}{f(rb,nb):>14}{f(rc,nc):>18}")
    print("\n目安: r≥0.3 弱い予測力あり / r≥0.5 まあ実在 / r<0.2 ほぼノイズ")

if __name__=="__main__":
    main()
