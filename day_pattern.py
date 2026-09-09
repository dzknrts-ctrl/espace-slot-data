#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""指定店舗の日付パターン(曜日/末尾/特定日)を平均総差枚・平均差枚でランキングし、イベント日を推定。
使い方: python day_pattern.py bigdipper
"""
import csv, os, glob, sys, statistics as st
from collections import defaultdict
from datetime import date

DATA_DIR=os.path.join(os.path.dirname(os.path.abspath(__file__)),"data")
HALL=sys.argv[1] if len(sys.argv)>1 else "bigdipper"
WD=["月","火","水","木","金","土","日"]

def ni(s):
    try:return int(float(str(s).replace(",","")))
    except:return None

def load():
    byday={}
    for p in sorted(glob.glob(os.path.join(DATA_DIR,f"*_{HALL}.csv"))):
        if p.endswith("_kishu.csv"):continue
        d=os.path.basename(p)[:10]
        sa=[ni(r.get("samai")) for r in csv.DictReader(open(p,encoding="utf-8"))]
        sa=[x for x in sa if x is not None]
        if sa: byday[d]=(sum(sa),sum(sa)/len(sa),len(sa),100*sum(1 for x in sa if x>0)/len(sa))
    return byday

def main():
    byday=load()
    if not byday:
        print(f"[{HALL}] データなし");return
    days=sorted(byday)
    tot=[byday[d][0] for d in days]
    base_tot=st.mean(tot); base_avg=st.mean([byday[d][1] for d in days])
    print(f"# {HALL} 日付パターン分析  ({days[0]}〜{days[-1]} {len(days)}日)")
    print(f"全体平均: 総差枚/日 {base_tot:+,.0f} ・ 台平均 {base_avg:+,.0f}\n")

    def rank(keyfn,label,order):
        g=defaultdict(list)
        for d in days: g[keyfn(d)].append(byday[d])
        rows=[]
        for k,v in g.items():
            mt=st.mean([x[0] for x in v]); ma=st.mean([x[1] for x in v])
            rows.append((k,mt,ma,len(v)))
        rows.sort(key=lambda r:-r[1])
        print(f"## {label}（平均総差枚の高い順）")
        print("| "+label+" | 平均総差枚/日 | 台平均差枚 | 日数 | 全体比 |")
        print("|---|--:|--:|--:|--:|")
        for k,mt,ma,n in rows:
            disp=order.get(k,str(k)) if order else str(k)
            print(f"| {disp} | {mt:+,.0f} | {ma:+,.0f} | {n} | {mt-base_tot:+,.0f} |")
        print()

    rank(lambda d:date(*map(int,d.split("-"))).weekday(),"曜日",{i:WD[i]+"曜" for i in range(7)})
    rank(lambda d:int(d[8:10])%10,"末尾",{i:f"末尾{i}" for i in range(10)})
    # 特定日(日にち)は2サンプル程度だが、突出日の把握用に上位のみ
    g=defaultdict(list)
    for d in days: g[int(d[8:10])].append(byday[d])
    rows=sorted(((k,st.mean([x[0] for x in v]),len(v)) for k,v in g.items()),key=lambda r:-r[1])
    print("## 日にち別 上位10（サンプル少・参考）")
    print("| 日 | 平均総差枚 | 日数 |")
    print("|---|--:|--:|")
    for k,mt,n in rows[:10]:
        print(f"| {k}日 | {mt:+,.0f} | {n} |")

if __name__=="__main__":
    main()
