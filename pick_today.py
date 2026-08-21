#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""指定日の狙い台を選定する。既存data/から、機種の店内優遇度・台番のクセ・曜日/末尾傾向・直近据え置き期待を合成。
使い方: python pick_today.py 2026-08-21
"""
import csv, os, glob, sys, statistics as st
from collections import defaultdict
from datetime import date

DATA_DIR=os.path.join(os.path.dirname(os.path.abspath(__file__)),"data")
HALLS={"shinkan":"エスパス上野新館","honkan":"エスパス上野本館",
       "island_akiba":"アイランド秋葉原","espace_akiba":"エスパス秋葉原駅前"}
WD=["月","火","水","木","金","土","日"]

def ni(s):
    try:return int(float(str(s).replace(",","")))
    except:return None
def nf(s):
    try:return float(str(s).replace(",",""))
    except:return None
def pw(s):
    p=(str(s)or"").split("/")
    if len(p)==2:
        try:return int(p[0]),int(p[1])
        except:return 0,0
    return 0,0
def pd(s):
    y,m,d=map(int,s.split("-"));return date(y,m,d)

def load_daban(hall):
    rows=[]
    for p in sorted(glob.glob(os.path.join(DATA_DIR,f"*_{hall}.csv"))):
        if p.endswith("_kishu.csv"):continue
        for r in csv.DictReader(open(p,encoding="utf-8")):
            r["_sa"]=ni(r.get("samai"));r["_g"]=ni(r.get("gousei"))
            rows.append(r)
    return rows
def load_kishu(hall):
    rows=[]
    for p in sorted(glob.glob(os.path.join(DATA_DIR,f"*_{hall}_kishu.csv"))):
        rows+=list(csv.DictReader(open(p,encoding="utf-8")))
    return rows

def zscores(vals):
    xs=[v for v in vals if v is not None]
    if len(xs)<2:return {i:0 for i in range(len(vals))}
    mu=st.mean(xs);sd=st.pstdev(xs) or 1
    return [ (v-mu)/sd if v is not None else 0 for v in vals]

def main():
    target=sys.argv[1] if len(sys.argv)>1 else "2026-08-21"
    ty,tm,td=map(int,target.split("-")); tdate=date(ty,tm,td)
    twd=tdate.weekday(); tmatsu=td%10
    out=[f"# 狙い台選定  {target}（{WD[twd]}曜・末尾{tmatsu}）\n"]
    for hall,jp in HALLS.items():
        daban=load_daban(hall); kishu=load_kishu(hall)
        if not daban: continue
        dates=sorted({r["date"] for r in daban}); last=dates[-1]
        # 機種別: 全体勝率, 曜日勝率, 末尾勝率
        mo=defaultdict(lambda:{"wn":0,"wN":0,"sa":0.0,"dai":0})
        mwd=defaultdict(lambda:{"wn":0,"wN":0}); mmt=defaultdict(lambda:{"wn":0,"wN":0})
        for r in kishu:
            model=(r.get("model")or"").strip() or "(不明)"
            wn,wN=pw(r.get("win")); dai=ni(r.get("total_dai")) or 0; sa=nf(r.get("avg_samai"))
            mo[model]["wn"]+=wn;mo[model]["wN"]+=wN;mo[model]["dai"]+=dai
            if sa is not None:mo[model]["sa"]+=sa*dai
            dt=pd(r["date"])
            if dt.weekday()==twd:mwd[model]["wn"]+=wn;mwd[model]["wN"]+=wN
            if dt.day%10==tmatsu:mmt[model]["wn"]+=wn;mmt[model]["wN"]+=wN
        def wr(d): return 100*d["wn"]/d["wN"] if d["wN"] else None
        # 台番別
        byd=defaultdict(list)
        for r in daban: byd[str(r.get("daban"))].append(r)
        cand=[]
        for dab,rs in byd.items():
            rs=sorted(rs,key=lambda r:r["date"])
            sa=[r["_sa"] for r in rs if r["_sa"] is not None]
            if len(sa)<5:continue
            plus=sum(1 for x in sa if x>0)
            model=next((r.get("model") for r in reversed(rs) if (r.get("model")or"").strip()),"")
            lastrow=next((r for r in reversed(rs) if r["date"]==last),None)
            last_sa=lastrow["_sa"] if lastrow else None
            last_g=lastrow["_g"] if lastrow else None
            cand.append({"daban":dab,"model":model,"plus":100*plus/len(sa),
                "mean":st.mean(sa),"last_sa":last_sa,"last_g":last_g,
                "mo_wr":wr(mo.get(model,{"wn":0,"wN":0})) if model else None,
                "wd_wr":wr(mwd.get(model,{"wn":0,"wN":0})) if model else None,
                "mt_wr":wr(mmt.get(model,{"wn":0,"wN":0})) if model else None})
        # スコア合成
        zp=zscores([c["plus"] for c in cand]); zm=zscores([c["mean"] for c in cand])
        zmo=zscores([c["mo_wr"] for c in cand])
        for i,c in enumerate(cand):
            wd=c["wd_wr"] or 0; mt=c["mt_wr"] or 0
            c["score"]=round(zp[i]*1.0+zm[i]*0.7+zmo[i]*0.8+(wd/100)*0.6+(mt/100)*0.6,3)
        cand.sort(key=lambda c:c["score"],reverse=True)

        # 機種シマ本命(曜日・末尾, サンプル明示)
        shima=[]
        for model in mo:
            d=mo[model]
            if d["wN"]<10:continue
            wdd=mwd.get(model,{"wn":0,"wN":0}); mtd=mmt.get(model,{"wn":0,"wN":0})
            shima.append({"model":model,"all_wr":wr(d),"all_N":d["wN"],
                "wd_wr":wr(wdd),"wd_N":wdd["wN"],"mt_wr":wr(mtd),"mt_N":mtd["wN"],
                "avg_sa":round(d["sa"]/d["dai"],0) if d["dai"] else 0})
        # 曜日勝率>全体 かつ サンプル十分 を優先
        shima.sort(key=lambda s:((s["wd_wr"] or 0)*0.6+(s["mt_wr"] or 0)*0.4 + (s["all_wr"] or 0)*0.3),reverse=True)

        out.append(f"\n## {jp}（{dates[0]}〜{last} {len(dates)}日）")
        out.append(f"\n### 本命シマ（{WD[twd]}・末尾{tmatsu}傾向＋店内優遇）")
        out.append("| 機種 | 全体勝率(N) | "+WD[twd]+"勝率(N) | 末尾"+str(tmatsu)+"勝率(N) | 平均差枚 |")
        out.append("|---|--:|--:|--:|--:|")
        for s in shima[:6]:
            f=lambda w,n:(f"{w:.0f}%({n})" if w is not None else f"-({n})")
            out.append(f"| {s['model']} | {f(s['all_wr'],s['all_N'])} | {f(s['wd_wr'],s['wd_N'])} | {f(s['mt_wr'],s['mt_N'])} | {s['avg_sa']:+.0f} |")
        out.append(f"\n### 狙い台 TOP8（台番クセ＋据え置き期待）")
        out.append("| 台番 | 機種 | プラス率 | 平均差枚 | 前日(8/20)差枚 | 前日合成 |")
        out.append("|---|---|--:|--:|--:|--:|")
        for c in cand[:8]:
            g=f"1/{c['last_g']}" if c['last_g'] else "-"
            out.append(f"| {c['daban']} | {c['model'] or '—'} | {c['plus']:.0f}% | {c['mean']:+.0f} | {(c['last_sa'] if c['last_sa'] is not None else 0):+.0f} | {g} |")
    txt="\n".join(out)
    open(os.path.join(os.path.dirname(__file__),"reports",f"picks_{target}.md"),"w",encoding="utf-8").write(txt)
    print(txt)

if __name__=="__main__":
    main()
