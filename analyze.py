#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
出玉データ分析 — エスパス4店(上野新館/本館・アイランド秋葉原・エスパス秋葉原駅前)

3つの視点で狙い台の絞り込み材料を出す:
  A) 機種別サマリ   … data/*_<hall>_kishu.csv(機種別集計)を全日集計。店がどの機種に力を入れているか。
  B) 台番別クセ     … data/*_<hall>.csv(台番別)を全日集計。特定台番の据え置き/優遇傾向。
  C) 日付タイプ別   … 曜日/末尾/ゾロ目/旧イベント日 × 機種 の勝率・平均差枚。本命シマ学習。

出力(reports/):
  model_summary_<hall>.csv / daban_habits_<hall>.csv / datetype_<hall>.csv
  summary.md / data.json(ダッシュボード用)
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
  "shinkan":      lambda d,w: "4/7のつく日" if d%10 in (4,7) else "",
  "honkan":       lambda d,w: "7のつく日"   if d%10==7 else "",
  "island_akiba": lambda d,w: "",
  "espace_akiba": lambda d,w: "6のつく日/特定日" if (d%10==6 or d in (1,11,22,25)) else "",
}
WD = ["月","火","水","木","金","土","日"]

def ni(s):
    try: return int(float(str(s).replace(",","")))
    except: return None
def nf(s):
    try: return float(str(s).replace(",",""))
    except: return None
def parse_date(s):
    y,m,d=map(int,s.split("-")); return date(y,m,d)
def parse_win(s):
    m=(str(s) or "").split("/")
    if len(m)==2:
        try: return int(m[0]), int(m[1])
        except: return 0,0
    return 0,0
def fmt(x, nd=0):
    if x is None: return "-"
    return f"{x:,.{nd}f}"

def load_daban(hall):
    rows=[]
    for p in sorted(glob.glob(os.path.join(DATA_DIR, f"*_{hall}.csv"))):
        if p.endswith("_kishu.csv"): continue
        for r in csv.DictReader(open(p, encoding="utf-8")):
            r["_G"]=ni(r.get("G")); r["_BB"]=ni(r.get("BB")); r["_RB"]=ni(r.get("RB")); r["_sa"]=ni(r.get("samai"))
            rows.append(r)
    return rows

def load_kishu(hall):
    rows=[]
    for p in sorted(glob.glob(os.path.join(DATA_DIR, f"*_{hall}_kishu.csv"))):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            rows.append(r)
    return rows

def load_models(hall):
    p=os.path.join(DATA_DIR,f"models_{hall}.json")
    if os.path.exists(p):
        try: return json.load(open(p,encoding="utf-8"))
        except: return {}
    return {}

def dtype_tags(hall, dt):
    d=parse_date(dt); w=d.weekday()
    tags=[f"曜:{WD[w]}", f"末尾:{d.day%10}"]
    if d.day%10==0 or (d.day>=11 and d.day//10==d.day%10): tags.append("ゾロ目/0")
    ev=EVENT[hall](d.day,w)
    if ev: tags.append(f"ｲﾍﾞﾝﾄ:{ev}")
    return tags

def analyze_hall(hall):
    kishu=load_kishu(hall); daban=load_daban(hall); mmap=load_models(hall)
    dates=sorted({r["date"] for r in daban}) or sorted({r["date"] for r in kishu})
    if not dates: return None

    # ---- A) 機種別サマリ(kishuベース, 台加重) ----
    agg=defaultdict(lambda:{"sa_w":0.0,"dai":0,"win_n":0,"win_N":0,"deri":[],"days":set(),"last_dai":0,"last":""})
    for r in kishu:
        model=(r.get("model") or "").strip() or "(不明)"
        dai=ni(r.get("total_dai")) or 0
        sa=nf(r.get("avg_samai"))
        wn,wN=parse_win(r.get("win"))
        a=agg[model]
        if sa is not None: a["sa_w"]+=sa*dai
        a["dai"]+=dai; a["win_n"]+=wn; a["win_N"]+=wN
        de=nf(r.get("deri"));
        if de: a["deri"].append(de)
        a["days"].add(r["date"])
        if r["date"]>=a["last"]: a["last"]=r["date"]; a["last_dai"]=dai
    model_summary=[]
    for model,a in agg.items():
        model_summary.append({
            "model":model, "設置台数":a["last_dai"], "延べ台日":a["dai"], "日数":len(a["days"]),
            "平均差枚": round(a["sa_w"]/a["dai"],1) if a["dai"] else None,
            "勝率%": round(100*a["win_n"]/a["win_N"],1) if a["win_N"] else None,
            "勝": a["win_n"], "全": a["win_N"],
            "平均出率": round(st.mean(a["deri"]),1) if a["deri"] else None,
        })
    model_summary.sort(key=lambda x:(x["平均差枚"] is not None, x["平均差枚"] or -9e9), reverse=True)

    # ---- B) 台番別クセ(dabanベース) ----
    byd=defaultdict(list)
    for r in daban: byd[str(r.get("daban"))].append(r)
    latest=dates[-1]; daban_habits=[]
    for dab,rs in byd.items():
        rs=sorted(rs,key=lambda r:r["date"])
        sa=[r["_sa"] for r in rs if r["_sa"] is not None]
        if not sa: continue
        plus=sum(1 for x in sa if x>0)
        last=next((r for r in reversed(rs) if r["date"]==latest), None)
        model=next((r.get("model") for r in reversed(rs) if (r.get("model") or "").strip()), "") or mmap.get(dab,"")
        pr=100*plus/len(sa)
        score=round(pr/100*0.5 + min(1.0,max(0,st.mean(sa)/2000))*0.5, 3)
        daban_habits.append({"daban":dab,"model":model,"日数":len(sa),
            "平均差枚":round(st.mean(sa),1),"プラス率%":round(pr,1),
            "最大差枚":max(sa),"最新差枚":last["_sa"] if last else None,"スコア":score})
    daban_habits.sort(key=lambda x:x["スコア"], reverse=True)

    # ---- C) 日付タイプ別(kishuベース: 勝率と平均差枚) ----
    dt=defaultdict(lambda:defaultdict(lambda:{"sa_w":0.0,"dai":0,"win_n":0,"win_N":0}))
    dt_hall=defaultdict(lambda:{"sa_w":0.0,"dai":0,"days":set()})
    for r in kishu:
        model=(r.get("model") or "").strip() or "(不明)"
        dai=ni(r.get("total_dai")) or 0; sa=nf(r.get("avg_samai")); wn,wN=parse_win(r.get("win"))
        for t in dtype_tags(hall, r["date"]):
            c=dt[t][model]
            if sa is not None: c["sa_w"]+=sa*dai
            c["dai"]+=dai; c["win_n"]+=wn; c["win_N"]+=wN
            h=dt_hall[t]; h["sa_w"]+= (sa*dai if sa is not None else 0); h["dai"]+=dai; h["days"].add(r["date"])
    datetype=[]
    for t,mm in dt.items():
        for model,c in mm.items():
            if c["win_N"]<8: continue
            datetype.append({"日付タイプ":t,"model":model,"延べ台日":c["dai"],
                "平均差枚":round(c["sa_w"]/c["dai"],1) if c["dai"] else None,
                "勝率%":round(100*c["win_n"]/c["win_N"],1) if c["win_N"] else None})
    datetype.sort(key=lambda x:(x["日付タイプ"], -(x["勝率%"] or 0)))
    datetype_hall=[{"日付タイプ":t,"日数":len(v["days"]),
                    "平均差枚":round(v["sa_w"]/v["dai"],1) if v["dai"] else None} for t,v in dt_hall.items()]
    datetype_hall.sort(key=lambda x:-(x["平均差枚"] or -9e9))

    # 日別の店全体差枚
    day_total=defaultdict(int)
    for r in daban:
        if r["_sa"] is not None: day_total[r["date"]]+=r["_sa"]
    return {"dates":dates,"model_summary":model_summary,"daban_habits":daban_habits,
            "datetype":datetype,"datetype_hall":datetype_hall,
            "day_total":dict(sorted(day_total.items()))}

def write_csv(path, rows, fields):
    with open(path,"w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore"); w.writeheader(); w.writerows(rows)

def main():
    os.makedirs(REP_DIR,exist_ok=True)
    md=["# エスパス4店 出玉分析サマリ",""]
    dash={"halls":{}, "hall_names":HALLS}
    for hall,jp in HALLS.items():
        res=analyze_hall(hall)
        if not res:
            md.append(f"## {jp}\nデータなし\n"); continue
        ds=res["dates"]
        write_csv(os.path.join(REP_DIR,f"model_summary_{hall}.csv"), res["model_summary"],
                  ["model","設置台数","延べ台日","日数","平均差枚","勝率%","勝","全","平均出率"])
        write_csv(os.path.join(REP_DIR,f"daban_habits_{hall}.csv"), res["daban_habits"],
                  ["daban","model","日数","平均差枚","プラス率%","最大差枚","最新差枚","スコア"])
        write_csv(os.path.join(REP_DIR,f"datetype_{hall}.csv"), res["datetype"],
                  ["日付タイプ","model","延べ台日","平均差枚","勝率%"])
        dash["halls"][hall]=res
        md.append(f"## {jp}  ({ds[0]}〜{ds[-1]}, {len(ds)}日)\n")
        md.append("**力の入る機種 TOP8（平均差枚・台加重）**\n")
        md.append("| 機種 | 平均差枚 | 勝率 | 設置 | 平均出率 |")
        md.append("|---|--:|--:|--:|--:|")
        for m in res["model_summary"][:8]:
            md.append(f"| {m['model']} | {fmt(m['平均差枚'],0)} | {fmt(m['勝率%'],0)}% | {m['設置台数']} | {fmt(m['平均出率'],1)}% |")
        md.append("\n**注目台番 TOP8（据え置き/クセ）**\n")
        md.append("| 台番 | 機種 | 平均差枚 | プラス率 | 最新 |")
        md.append("|---|---|--:|--:|--:|")
        for x in res["daban_habits"][:8]:
            md.append(f"| {x['daban']} | {x['model'] or '-'} | {fmt(x['平均差枚'],0)} | {fmt(x['プラス率%'],0)}% | {fmt(x['最新差枚'],0)} |")
        md.append("\n**日付タイプ別 店全体の出やすさ（平均差枚/台）**\n")
        md.append("| 日付タイプ | 平均差枚 | 日数 |")
        md.append("|---|--:|--:|")
        for x in res["datetype_hall"][:6]:
            md.append(f"| {x['日付タイプ']} | {fmt(x['平均差枚'],0)} | {x['日数']} |")
        md.append("")
    open(os.path.join(REP_DIR,"summary.md"),"w",encoding="utf-8").write("\n".join(md))
    # ダッシュボード用JSON(sets除去)
    def clean(o):
        if isinstance(o,dict): return {k:clean(v) for k,v in o.items() if not isinstance(v,set)}
        if isinstance(o,list): return [clean(x) for x in o]
        return o
    json.dump(clean(dash), open(os.path.join(REP_DIR,"data.json"),"w",encoding="utf-8"), ensure_ascii=False)
    print("wrote reports to", REP_DIR)
    print("\n".join(md))

if __name__=="__main__":
    main()
