# -*- coding: utf-8 -*-
"""3ヶ月フル歩進バックテスト: 各日をその日より前のデータで予測→当日実績で採点。track_record.csvを再構築。"""
import os, glob, csv, statistics as st
from datetime import date, timedelta
import track

tr=os.path.join(track.REP,"track_record.csv")
if os.path.exists(tr): os.remove(tr)

# 全4店にデータがある日を対象(採点は当日実データ必須)。予測は14日以上の履歴がつく日から。
have=lambda ds,h: os.path.exists(os.path.join(track.DATA,f"{ds}_{h}.csv"))
alldates=sorted({os.path.basename(p)[:10] for p in glob.glob(os.path.join(track.DATA,"2026-*_shinkan.csv")) if "_kishu" not in p})
start=date.fromisoformat(alldates[0])+timedelta(days=14)
n=0
for ds in alldates:
    d=date.fromisoformat(ds)
    if d<start: continue
    if not all(have(ds,h) for h in track.HALLS): continue
    track.predict(ds)
    if track.evaluate(ds): n+=1
print(f"評価日数: {n}")

rows=list(csv.DictReader(open(tr,encoding="utf-8-sig")))
from collections import defaultdict
agg=defaultdict(lambda:{"ih":0,"it":0,"sh":0,"stt":0,"e":[]})
for r in rows:
    for k in (r["hall"],"ZZ"):
        a=agg[k];a["ih"]+=int(r["島的中"]);a["it"]+=int(r["島数"]);a["sh"]+=int(r["台的中"]);a["stt"]+=int(r["台数"])
        if r["エッジ"]!="":a["e"].append(int(r["エッジ"]))
H={"shinkan":"上野新館","honkan":"上野本館","island_akiba":"アイランド秋葉原","espace_akiba":"秋葉原駅前","ZZ":"【全体】"}
days=sorted({r["date"] for r in rows})
print(f"\n=== 3ヶ月バックテスト成績  {days[0]}〜{days[-1]} ({len(days)}日) ===")
for k in ["shinkan","honkan","island_akiba","espace_akiba","ZZ"]:
    a=agg[k];ir=100*a["ih"]/a["it"] if a["it"] else 0;sr=100*a["sh"]/a["stt"] if a["stt"] else 0
    e=st.mean(a["e"]) if a["e"] else 0
    print(f'{H[k]:<9} 島的中 {a["ih"]:>3}/{a["it"]:<3}({ir:>2.0f}%)  台的中 {a["sh"]:>3}/{a["stt"]:<3}({sr:>2.0f}%)  平均エッジ {e:>+6.0f}枚')
