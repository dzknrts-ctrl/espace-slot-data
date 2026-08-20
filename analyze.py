#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
出玉データ分析 — エスパス4店(上野新館/本館・アイランド秋葉原・エスパス秋葉原駅前)
data/*_<hall>.csv(台番別)を集計し、狙い台の絞り込みに使う3種のレポートを出力する。

出力(reports/):
  model_summary_<hall>.csv   … 機種別サマリ(平均差枚/平均合成/勝率台率/総差枚 等)
  daban_habits_<hall>.csv    … 台番別クセ(平均差枚/プラス率/据え置きスコア/最新差枚)
  datetype_<hall>.csv        … 日付タイプ別(曜日/末尾/ゾロ目/イベント日)×機種の平均差枚・勝率
  summary.md                 … 人が読む総括(店ごとの強機種・注目台番・日付タイプ本命)

使い方: python analyze.py
"""
import csv, os, glob, json, statistics as st
from collections import defaultdict
from datetime import date

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
REP_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
HALLS = {"shinkan":"エスパス上野新館","honkan":"エスパス上野本館",
         "island_akiba":"アイランド秋葉原","espace_akiba":"エスパス秋葉原駅前"}
# 店舗別 旧イベント日(みんレポ記載)。d=日にち, w=曜日(0=月)
EVENT = {
  "shinkan":      lambda d,w: ("4のつく日" if d%10==4 else "")+("7のつく日" if d%10==7 else ""),
  "honkan":       lambda d,w: ("7のつく日" if d%10==7 else ""),
  "island_akiba": lambda d,w: "",
  "espace_akiba": lambda d,w: ("6のつく日" if d%10==6 else "")+("特定日" if d in (1,11,22,25) else ""),
}
WD = ["月","火","水","木","金","土","日"]

def to_int(s):
    try: return int(str(s).replace(",",""));
    except: return None
def to_float(s):
    try: return float(str(s).replace(",",""));
    except: return None

def load_rows(hall):
    rows=[]
    for p in sorted(glob.glob(os.path.join(DATA_DIR, f"*_{hall}.csv"))):
        if p.endswith("_kishu.csv"): continue
        with open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                r["_G"]=to_int(r.get("G")); r["_BB"]=to_int(r.get("BB"))
                r["_RB"]=to_int(r.get("RB")); r["_sa"]=to_int(r.get("samai"))
                rows.append(r)
    return rows

def gousei(r):
    """合成確率 分母 = G/(BB+RB)。BB+RB=0や不明はNone。"""
    g,b,rb=r["_G"],r["_BB"],r["_RB"]
    if g is None or b is None or rb is None: return None
    t=b+rb
    return round(g/t,1) if t>0 else None

def load_models(hall):
    p=os.path.join(DATA_DIR,f"models_{hall}.json")
    if os.path.exists(p):
        try: return json.load(open(p,encoding="utf-8"))
        except: return {}
    return {}

def model_of(r, mmap):
    return (r.get("model") or "").strip() or mmap.get(str(r.get("daban")),"") or "(不明)"

def parse_date(s):
    y,m,d=map(int,s.split("-")); return date(y,m,d)

def fmt(x, nd=0):
    if x is None: return "-"
    return f"{x:.{nd}f}" if nd else f"{x:.0f}"

def analyze_hall(hall):
    rows=load_rows(hall); mmap=load_models(hall)
    if not rows: return None
    dates=sorted({r["date"] for r in rows})
    # ---- A) 機種別サマリ ----
    bym=defaultdict(list)
    for r in rows:
        bym[model_of(r,mmap)].append(r)
    model_summary=[]
    for model, rs in bym.items():
        sa=[r["_sa"] for r in rs if r["_sa"] is not None]
        gs=[gousei(r) for r in rs]; gs=[x for x in gs if x]
        ndays=len({r["date"] for r in rs})
        plus=sum(1 for x in sa if x>0)
        model_summary.append({
            "model":model, "延べ台数":len(rs), "設置日数":ndays,
            "平均差枚": round(st.mean(sa),1) if sa else None,
            "総差枚": sum(sa) if sa else 0,
            "プラス率%": round(100*plus/len(sa),1) if sa else None,
            "平均合成": round(st.mean(gs),1) if gs else None,
            "最良合成": min(gs) if gs else None,
        })
    model_summary.sort(key=lambda x:(x["平均差枚"] is not None, x["平均差枚"] or -9e9), reverse=True)

    # ---- B) 台番別クセ ----
    byd=defaultdict(list)
    for r in rows:
        byd[str(r.get("daban"))].append(r)
    daban_habits=[]
    latest=dates[-1]
    for dab, rs in byd.items():
        rs=sorted(rs,key=lambda r:r["date"])
        sa=[r["_sa"] for r in rs if r["_sa"] is not None]
        gs=[gousei(r) for r in rs]; gs=[x for x in gs if x]
        plus=sum(1 for x in sa if x>0)
        n=len(sa)
        last=next((r for r in reversed(rs) if r["date"]==latest), None)
        # 据え置き/クセ スコア: プラス率 と 平均差枚 を正規化した簡易指標
        score = (round(100*plus/n,1) if n else 0)/100.0 * 0.5 + (min(1.0,(st.mean(sa)/2000)) if sa else 0)*0.5
        daban_habits.append({
            "daban":dab, "model":model_of(rs[-1],mmap),
            "回数":n, "平均差枚":round(st.mean(sa),1) if sa else None,
            "プラス率%":round(100*plus/n,1) if n else None,
            "最大差枚":max(sa) if sa else None, "平均合成":round(st.mean(gs),1) if gs else None,
            "最新差枚": last["_sa"] if last else None,
            "スコア":round(score,3),
        })
    daban_habits.sort(key=lambda x:x["スコア"], reverse=True)

    # ---- C) 日付タイプ別 ----
    # 日ごとの店全体差枚合計 と 機種別
    day_hall=defaultdict(int); day_cnt=defaultdict(int)
    dt_model=defaultdict(lambda: defaultdict(list))  # dtype -> model -> [samai]
    def dtypes(dt):
        d=parse_date(dt); w=d.weekday(); tags=[f"曜:{WD[w]}", f"末尾:{d.day%10}"]
        if d.day%10==0 or (d.day//10==d.day%10): tags.append("ゾロ目/0")
        ev=EVENT[hall](d.day,w)
        if ev: tags.append(f"ｲﾍﾞﾝﾄ:{ev}")
        return tags
    for r in rows:
        if r["_sa"] is None: continue
        day_hall[r["date"]]+=r["_sa"]; day_cnt[r["date"]]+=1
        for t in dtypes(r["date"]):
            dt_model[t][model_of(r,mmap)].append(r["_sa"])
    datetype=[]
    for t, mm in dt_model.items():
        for model, sa in mm.items():
            if len(sa)<3: continue
            plus=sum(1 for x in sa if x>0)
            datetype.append({"日付タイプ":t,"model":model,"延べ台":len(sa),
                             "平均差枚":round(st.mean(sa),1),"プラス率%":round(100*plus/len(sa),1)})
    datetype.sort(key=lambda x:(x["日付タイプ"], -x["平均差枚"]))

    return {"dates":dates,"model_summary":model_summary,"daban_habits":daban_habits,
            "datetype":datetype,"day_hall":day_hall,"day_cnt":day_cnt}

def write_csv(path, rows, fields):
    with open(path,"w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

def main():
    os.makedirs(REP_DIR,exist_ok=True)
    md=["# エスパス4店 出玉分析サマリ", ""]
    for hall,jp in HALLS.items():
        res=analyze_hall(hall)
        if not res:
            md.append(f"## {jp}\nデータなし\n"); continue
        ds=res["dates"]
        write_csv(os.path.join(REP_DIR,f"model_summary_{hall}.csv"), res["model_summary"],
                  ["model","延べ台数","設置日数","平均差枚","総差枚","プラス率%","平均合成","最良合成"])
        write_csv(os.path.join(REP_DIR,f"daban_habits_{hall}.csv"), res["daban_habits"],
                  ["daban","model","回数","平均差枚","プラス率%","最大差枚","平均合成","最新差枚","スコア"])
        write_csv(os.path.join(REP_DIR,f"datetype_{hall}.csv"), res["datetype"],
                  ["日付タイプ","model","延べ台","平均差枚","プラス率%"])
        # markdown 総括
        md.append(f"## {jp}  ({ds[0]}〜{ds[-1]}, {len(ds)}日)")
        md.append("")
        md.append("**強い機種 TOP5(平均差枚)**")
        md.append("| 機種 | 平均差枚 | プラス率 | 平均合成 | 延べ台 |")
        md.append("|---|--:|--:|--:|--:|")
        for m in res["model_summary"][:5]:
            md.append(f"| {m['model']} | {fmt(m['平均差枚'],1)} | {fmt(m['プラス率%'],1)}% | {fmt(m['平均合成'],1)} | {m['延べ台数']} |")
        md.append("")
        md.append("**注目台番 TOP5(クセ・据え置きスコア)**")
        md.append("| 台番 | 機種 | 平均差枚 | プラス率 | 最新差枚 |")
        md.append("|---|---|--:|--:|--:|")
        for x in res["daban_habits"][:5]:
            md.append(f"| {x['daban']} | {x['model']} | {fmt(x['平均差枚'],1)} | {fmt(x['プラス率%'],1)}% | {fmt(x['最新差枚'])} |")
        md.append("")
    open(os.path.join(REP_DIR,"summary.md"),"w",encoding="utf-8").write("\n".join(md))
    print("wrote reports to", REP_DIR)
    print("\n".join(md))

if __name__=="__main__":
    main()
