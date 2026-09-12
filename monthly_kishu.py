#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""月間・機種別トータル差枚ランキング。各店舗ごとに 優秀機種/マイナス機種 を集計。
月間差枚(機種) = Σ_日 (avg_samai × total_dai)。使い方: python monthly_kishu.py 2026-08
出力: reports/monthly_<month>.json （ダッシュボード生成用）+ 標準出力サマリ
"""
import csv, os, glob, sys, json
from collections import defaultdict

DATA_DIR=os.path.join(os.path.dirname(os.path.abspath(__file__)),"data")
HALLS={"shinkan":"エスパス上野新館","honkan":"エスパス上野本館",
       "island_akiba":"アイランド秋葉原","espace_akiba":"エスパス秋葉原駅前",
       "bigdipper":"BIGディッパー門前仲町","stardust":"門前仲町スターダスト",
       "bigapple":"ビッグアップル秋葉原"}  # bigappleはアナスロ由来の機種別TOP20(優秀機種)

def ni(s):
    try:return int(float(str(s).replace(",","")))
    except:return None
def nf(s):
    try:return float(str(s).replace(",",""))
    except:return None

def month_of(hall, month):
    """{model: {'sa':総差枚, 'dai_days':延台, 'days':日数}} と 店全体総差枚, 稼働日数"""
    agg=defaultdict(lambda:{"sa":0,"dai_days":0,"days":0})
    days=set()
    for p in sorted(glob.glob(os.path.join(DATA_DIR,f"{month}-*_{hall}_kishu.csv"))):
        day=os.path.basename(p)[:10]; days.add(day)
        for r in csv.DictReader(open(p,encoding="utf-8")):
            m=(r.get("model")or"").strip()
            sa=nf(r.get("avg_samai")); n=ni(r.get("total_dai")) or 0
            if not m or sa is None or n<=0: continue
            agg[m]["sa"]+=sa*n; agg[m]["dai_days"]+=n; agg[m]["days"]+=1
    total=sum(v["sa"] for v in agg.values())
    return agg, total, len(days)

def main():
    month=sys.argv[1] if len(sys.argv)>1 else "2026-08"
    result={"month":month,"halls":[]}
    print(f"# 月間機種別差枚ランキング  {month}\n")
    for hall,jp in HALLS.items():
        agg,total,ndays=month_of(hall,month)
        if not agg: continue
        rows=[{"model":m,"sa":round(v["sa"]),"dai_days":v["dai_days"],"days":v["days"]}
              for m,v in agg.items()]
        rows.sort(key=lambda r:r["sa"],reverse=True)
        result["halls"].append({"hall":hall,"name":jp,"total":round(total),
                                "ndays":ndays,"models":rows})
        pos=[r for r in rows if r["sa"]>0]; neg=[r for r in rows if r["sa"]<0]
        print(f"## {jp}  月間総差枚 {round(total):+,}  ({ndays}日・{len(rows)}機種)")
        print(f"  優秀TOP5: " + " / ".join(f"{r['model'][:14]} {r['sa']:+,}" for r in rows[:5]))
        print(f"  マイナスWORST5: " + " / ".join(f"{r['model'][:14]} {r['sa']:+,}" for r in rows[-5:][::-1]) + "\n")
    os.makedirs(os.path.join(os.path.dirname(__file__),"reports"),exist_ok=True)
    json.dump(result,open(os.path.join(os.path.dirname(__file__),"reports",f"monthly_{month}.json"),
              "w",encoding="utf-8"),ensure_ascii=False,indent=1)

if __name__=="__main__":
    main()
