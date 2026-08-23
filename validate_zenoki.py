# -*- coding: utf-8 -*-
"""据え置き仮説の検証: ある島が「全ツッパ」した翌日、その島は強いままか(据え置き)を測る。
全ツッパ = 勝率≥65% & 平均出率≥108% & 4台以上。
翌日指標: 再全ツッパ率 / 平均差枚プラス率 / 勝率≥55%率 を、ベースレート(全島全日)と比較。
"""
import csv, glob, os, statistics as st
from collections import defaultdict
from datetime import date, timedelta
DATA=os.path.join(os.path.dirname(os.path.abspath(__file__)),"data")
HALLS={"shinkan":"上野新館","honkan":"上野本館","island_akiba":"アイランド秋葉原","espace_akiba":"秋葉原駅前"}
THR_W,THR_D,THR_N=65.0,108.0,4
def pw(s):
    p=(s or "").split("/")
    try:return int(p[0]),int(p[1])
    except:return 0,0
def nf(s):
    try:return float(str(s).replace(",",""))
    except:return None

def load(hall):
    # {date: {model: (wr, deri, samai, n, zentu)}}
    dd=defaultdict(dict)
    for p in sorted(glob.glob(os.path.join(DATA,f"*_{hall}_kishu.csv"))):
        for r in csv.DictReader(open(p,encoding="utf-8")):
            wn,wN=pw(r.get("win")); n=int(float(r.get("total_dai") or 0)); de=nf(r.get("deri")); sa=nf(r.get("avg_samai"))
            if n<THR_N or wN==0: continue
            wr=100*wn/wN
            zentu = wr>=THR_W and (de or 0)>=THR_D
            dd[r["date"]][(r.get("model") or "").strip()]=(wr,de,sa,n,zentu)
    return dd

def main():
    print("据え置き検証: 『全ツッパ島は翌日も強いか』 (4台以上の島のみ)\n")
    print(f"{'店':<10}{'全ツッパ→翌日':<16}{'再全ツッパ':>10}{'翌日プラス':>10}{'翌日勝率55+':>12}")
    print(f"{'':10}{'(ベースレート)':<16}{'':>10}{'':>10}{'':>12}")
    allev=defaultdict(int); allbase=defaultdict(int); alln=[0,0]
    for hall,jp in HALLS.items():
        dd=load(hall)
        dates=sorted(dd)
        # ベースレート(全島全日)
        base_z=base_p=base_w=base_tot=0
        for d in dates:
            for m,(wr,de,sa,n,z) in dd[d].items():
                base_tot+=1
                base_z+= 1 if z else 0
                base_p+= 1 if (sa or 0)>0 else 0
                base_w+= 1 if wr>=55 else 0
        # イベント: 全ツッパ島→翌日
        ev=0; nz=0; npl=0; nw=0
        for i,d in enumerate(dates[:-1]):
            nd=(date.fromisoformat(d)+timedelta(days=1)).isoformat()
            if nd not in dd: continue
            for m,(wr,de,sa,n,z) in dd[d].items():
                if not z: continue
                if m not in dd[nd]: continue   # 翌日その島が無い(データ欠)ならスキップ
                wr2,de2,sa2,n2,z2=dd[nd][m]
                ev+=1
                nz+= 1 if z2 else 0
                npl+= 1 if (sa2 or 0)>0 else 0
                nw+= 1 if wr2>=55 else 0
        def pct(a,b): return f"{100*a/b:.0f}%" if b else "-"
        print(f"{jp:<10}{('n='+str(ev)):<16}{pct(nz,ev):>10}{pct(npl,ev):>10}{pct(nw,ev):>12}")
        print(f"{'':10}{'ベース':<16}{pct(base_z,base_tot):>10}{pct(base_p,base_tot):>10}{pct(base_w,base_tot):>12}")
        allev['z']+=nz;allev['p']+=npl;allev['w']+=nw;allev['n']+=ev
        allbase['z']+=base_z;allbase['p']+=base_p;allbase['w']+=base_w;allbase['n']+=base_tot
        print()
    print("=== 全体 ===")
    def pct(a,b): return f"{100*a/b:.0f}%" if b else "-"
    print(f"全ツッパ→翌日(n={allev['n']}):  再全ツッパ {pct(allev['z'],allev['n'])} / 翌日プラス {pct(allev['p'],allev['n'])} / 勝率55+ {pct(allev['w'],allev['n'])}")
    print(f"ベースレート(n={allbase['n']}): 全ツッパ {pct(allbase['z'],allbase['n'])} / プラス {pct(allbase['p'],allbase['n'])} / 勝率55+ {pct(allbase['w'],allbase['n'])}")

if __name__=="__main__":
    main()
