# -*- coding: utf-8 -*-
"""島型 vs 単体型 の傾向分析。
各店・各日で「島集中度」= その日の勝ち台のうち“島ごと丸ごと高設定(島勝率≥STRONG)”で説明できる割合 を計算。
高い=島型(まとめて入る)、低い=単体型(バラけて入る)。曜日別の違いも出す。
使い方: python concentration.py
"""
import csv, os, glob, statistics as st
from collections import defaultdict
from datetime import date
DATA=os.path.join(os.path.dirname(os.path.abspath(__file__)),"data")
HALLS={"shinkan":"エスパス上野新館","honkan":"エスパス上野本館",
       "island_akiba":"アイランド秋葉原","espace_akiba":"エスパス秋葉原駅前"}
WD=["月","火","水","木","金","土","日"]
STRONG=65.0   # 島勝率がこれ以上なら「島ごと上げ」とみなす
MINN=3        # 島とみなす最小設置台数

def pw(s):
    p=(str(s)or"").split("/")
    try:return int(p[0]),int(p[1])
    except:return 0,0
def ni(s):
    try:return int(float(str(s).replace(",","")))
    except:return 0

def day_conc(hall):
    """日別: (date, 島集中度, 全ツッパ島数, 島数, 総勝ち台)"""
    byday=defaultdict(list)
    for p in sorted(glob.glob(os.path.join(DATA,f"*_{hall}_kishu.csv"))):
        for r in csv.DictReader(open(p,encoding="utf-8")):
            wn,wN=pw(r.get("win")); n=ni(r.get("total_dai"))
            if n>=MINN and wN>0:
                byday[r["date"]].append((wn,wN,100*wn/wN))
    out=[]
    for d,isls in sorted(byday.items()):
        plus_total=sum(wn for wn,wN,wr in isls)
        strong=[(wn,wN,wr) for wn,wN,wr in isls if wr>=STRONG]
        plus_strong=sum(wn for wn,wN,wr in strong)
        conc=plus_strong/plus_total if plus_total else 0
        out.append((d,conc,len(strong),len(isls),plus_total))
    return out

def main():
    print(f"島集中度 = その日の勝ち台のうち『島勝率≥{STRONG:.0f}%の“島ごと上げ”』に含まれる割合（高=島型 / 低=単体型）\n")
    for hall,jp in HALLS.items():
        days=day_conc(hall)
        if not days: continue
        concs=[c for _,c,_,_,_ in days]
        mean=st.mean(concs)
        # 曜日別
        bywd=defaultdict(list)
        for d,c,ns,ni_,pt in days:
            bywd[date.fromisoformat(d).weekday()].append(c)
        wdstr=" ".join(f"{WD[w]}{100*st.mean(bywd[w]):.0f}" for w in range(7) if w in bywd)
        verdict = "島型が強い" if mean>=0.5 else ("単体型が強い" if mean<0.35 else "混合")
        print(f"■ {jp}  平均島集中度 {100*mean:.0f}%  → 【{verdict}】")
        print(f"    曜日別集中度(%): {wdstr}")
        # 集中度が高い日/低い日の例
        top=sorted(days,key=lambda x:x[1],reverse=True)[:3]
        low=sorted(days,key=lambda x:x[1])[:3]
        print("    島型だった日: "+", ".join(f"{d[5:]}({WD[date.fromisoformat(d).weekday()]},{100*c:.0f}%,全ツッパ{ns}島)" for d,c,ns,_,_ in top))
        print("    単体型だった日: "+", ".join(f"{d[5:]}({WD[date.fromisoformat(d).weekday()]},{100*c:.0f}%,全ツッパ{ns}島)" for d,c,ns,_,_ in low))
        print()

if __name__=="__main__":
    main()
