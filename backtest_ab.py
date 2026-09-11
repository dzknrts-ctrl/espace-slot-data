#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A/Bバックテスト: 旧ロジック(初版24f81dd) vs 新ロジック(現行track.py) を同一期間・同一採点で対戦。
採点は現行 evaluate と同じ定義(島=当日平均差枚≥当日中央値で的中 / 台=当日差枚>0で的中 / エッジ=狙い台平均−全台平均)。
予測は各日「その日より前のデータのみ」(ウォークフォワード)。使い方: python backtest_ab.py
"""
import os, glob, csv, statistics as st
from collections import defaultdict
from datetime import date
import track as T   # 現行の load_kishu/load_daban/island_picks/seat_picks/定数を再利用

pdt=T.pdt; zz=T.zz; nf=T.nf; ni=T.ni; pw=T.pw

# ---- 高速化: 店舗ごと一度だけ全CSVを読み、以後はメモリ内フィルタ ----
_KC={}; _DC={}
def _k_cached(hall, before=None, on=None):
    if hall not in _KC:
        rows=[]
        for p in sorted(glob.glob(os.path.join(T.DATA,f"*_{hall}_kishu.csv"))):
            for r in csv.DictReader(open(p,encoding="utf-8")):
                r["_sa"]=nf(r.get("avg_samai")); r["_de"]=nf(r.get("deri"))
                r["_wn"],r["_wN"]=pw(r.get("win")); r["_n"]=ni(r.get("total_dai")) or 0
                rows.append(r)
        _KC[hall]=rows
    return [r for r in _KC[hall] if (not before or r["date"]<before) and (not on or r["date"]==on)]
def _d_cached(hall, before=None, on=None):
    if hall not in _DC:
        rows=[]
        for p in sorted(glob.glob(os.path.join(T.DATA,f"*_{hall}.csv"))):
            if p.endswith("_kishu.csv"): continue
            for r in csv.DictReader(open(p,encoding="utf-8")):
                r["_sa"]=ni(r.get("samai")); r["_g"]=ni(r.get("gousei")); rows.append(r)
        _DC[hall]=rows
    return [r for r in _DC[hall] if (not before or r["date"]<before) and (not on or r["date"]==on)]
T.load_kishu=_k_cached; T.load_daban=_d_cached   # island/seat/score すべてに反映
WD=T.WD; HALLS=T.HALLS
THR_W,THR_D,THR_N=T.THR_W,T.THR_D,T.THR_N
N_SHIMA,N_SEAT=T.N_SHIMA,T.N_SEAT

# ---------- 旧ロジック(初版) ----------
def old_island_picks(hall, target):
    ty,tm,td=map(int,target.split("-")); twd=date(ty,tm,td).weekday(); tmt=td%10
    ks=T.load_kishu(hall, before=target)          # ★ウィンドウ無し(全history)
    if not ks: return []
    dates=sorted({r["date"] for r in ks}); last=dates[-1]
    isl=defaultdict(lambda:{"days":{},"wn":0,"wN":0,"sa_w":0.0,"dai":0,
                            "wd_wn":0,"wd_wN":0,"mt_wn":0,"mt_wN":0,"push":[]})
    for r in ks:
        m=(r.get("model")or"").strip() or "(不明)"
        if r["_n"]<2: continue
        a=isl[m]; wr=100*r["_wn"]/r["_wN"] if r["_wN"] else None
        a["days"][r["date"]]={"wr":wr,"n":r["_n"]}
        a["wn"]+=r["_wn"];a["wN"]+=r["_wN"];a["dai"]+=r["_n"]
        if r["_sa"] is not None:a["sa_w"]+=r["_sa"]*r["_n"]
        dt=pdt(r["date"])
        if dt.weekday()==twd:a["wd_wn"]+=r["_wn"];a["wd_wN"]+=r["_wN"]
        if dt.day%10==tmt:a["mt_wn"]+=r["_wn"];a["mt_wN"]+=r["_wN"]
        if wr is not None and wr>=THR_W and (r["_de"] or 0)>=THR_D and r["_n"]>=THR_N:
            a["push"].append(r["date"])
    rows=[]
    for m,a in isl.items():
        if a["wN"]<10: continue
        allwr=100*a["wn"]/a["wN"]
        rows.append({"model":m,"全体勝率":round(allwr),
            "平均差枚":round(a["sa_w"]/a["dai"]) if a["dai"] else 0,"全ツッパ日数":len(a["push"]),
            "曜勝率":(round(100*a["wd_wn"]/a["wd_wN"]) if a["wd_wN"] else None),
            "末尾勝率":(round(100*a["mt_wn"]/a["mt_wN"]) if a["mt_wN"] else None),
            "最終全ツッパ":(sorted(a["push"])[-1] if a["push"] else None),"_allwr":allwr})
    zw=zz([r["全体勝率"] for r in rows]); zp=zz([r["全ツッパ日数"] for r in rows]); zs=zz([r["平均差枚"] for r in rows])
    for i,r in enumerate(rows):
        wd=(r["曜勝率"] if r["曜勝率"] is not None else r["全体勝率"])
        mt=(r["末尾勝率"] if r["末尾勝率"] is not None else r["全体勝率"])
        gap=(pdt(last)-pdt(r["最終全ツッパ"])).days if r["最終全ツッパ"] else 0
        rot=min(gap,10)/10 if r["全ツッパ日数"]>=2 else 0
        r["score"]=zw[i]*1.0+zp[i]*0.8+zs[i]*0.5+((wd-r['_allwr'])/100)*0.6+((mt-r['_allwr'])/100)*0.4+rot*0.4
    rows.sort(key=lambda r:r["score"],reverse=True)
    return rows[:N_SHIMA]

def old_seat_picks(hall, target):
    db=T.load_daban(hall, before=target)
    byd=defaultdict(list)
    for r in db: byd[str(r.get("daban"))].append(r)
    dates=sorted({r["date"] for r in db}); last=dates[-1] if dates else None
    seats=[]
    for dab,rs in byd.items():                    # ★現存台番フィルタ無し(ゴースト台込み)
        rs=sorted(rs,key=lambda r:r["date"]); sa=[r["_sa"] for r in rs if r["_sa"] is not None]
        if len(sa)<5:continue
        plus=sum(1 for x in sa if x>0)
        model=next((r.get("model") for r in reversed(rs) if (r.get("model")or"").strip()),"")
        seats.append({"daban":dab,"model":model,"プラス率":round(100*plus/len(sa)),
                      "平均差枚":round(st.mean(sa))})
    seats.sort(key=lambda s:(s["プラス率"],s["平均差枚"]),reverse=True)   # ★勝率主導
    return seats[:N_SEAT]

# ---------- 採点はtrack.py本体のpredict/evaluateを使用(実システムと完全一致) ----------
def eval_dates():
    ds=set()
    for p in glob.glob(os.path.join(T.DATA,"*_kishu.csv")):
        d=os.path.basename(p)[:10]
        if "2026-06-02"<=d<="2026-09-30": ds.add(d)
    return sorted(ds)

def run(logic):
    # 一時ディレクトリに predictions/track_record を吐かせ、実 evaluate で採点
    tmp=os.path.join(T.BASE,f"_ab_{logic}"); os.makedirs(tmp,exist_ok=True)
    T.PRED=os.path.join(tmp,"pred"); T.REP=os.path.join(tmp,"rep")
    os.makedirs(T.PRED,exist_ok=True); os.makedirs(T.REP,exist_ok=True)
    if logic=="old":
        T.island_picks=old_island_picks; T.seat_picks=old_seat_picks
    else:
        T.island_picks=_NEW_ISL; T.seat_picks=_NEW_SEAT
    for d in eval_dates():
        T.predict(d); T.evaluate(d)
    # 集計
    bym=defaultdict(lambda:{"edge":[],"sh":0,"st":0,"ph":0,"pt":0})
    byh=defaultdict(lambda:{"edge":[],"sh":0,"st":0,"ph":0,"pt":0})
    import csv as _csv
    for r in _csv.DictReader(open(os.path.join(T.REP,"track_record.csv"),encoding="utf-8-sig")):
        m=r["date"][:7]; hall=r["hall"]
        e=nf(r["エッジ"]) if r["エッジ"] not in ("",None) else None
        sh,stt=ni(r["島的中"]),ni(r["島数"]); ph,pt=ni(r["台的中"]),ni(r["台数"])
        for bucket in (bym[m],byh[hall],bym["ALL"]):
            if e is not None: bucket["edge"].append(e)
            bucket["sh"]+=sh; bucket["st"]+=stt; bucket["ph"]+=ph; bucket["pt"]+=pt
    return bym,byh

def line(b):
    e=st.mean(b["edge"]) if b["edge"] else 0
    ir=100*b["sh"]/b["st"] if b["st"] else 0
    pr=100*b["ph"]/b["pt"] if b["pt"] else 0
    return e,ir,pr,len(b["edge"])

# 新ロジックの実体を退避(runでT.island_picksを差し替えるため)
_NEW_ISL=T.island_picks; _NEW_SEAT=T.seat_picks

if __name__=="__main__":
    print("集計中... (新旧2回のウォークフォワード・実evaluate採点)",flush=True)
    nb,nh=run("new"); ob,oh=run("old")
    months=sorted(k for k in nb if k!="ALL")
    print("\n=== 月別 エッジ(狙い台平均差枚−全台平均) 新 vs 旧 ===")
    print(f"{'月':<8}{'新エッジ':>9}{'旧エッジ':>9}{'差':>8}   {'新台的中':>8}{'旧台的中':>8}")
    for m in months+["ALL"]:
        ne,nir,npr,nn=line(nb[m]); oe,oir,opr,on=line(ob[m])
        print(f"{m:<8}{ne:>+9.0f}{oe:>+9.0f}{ne-oe:>+8.0f}   {npr:>7.0f}%{opr:>7.0f}%")
    print("\n=== 店舗別 平均エッジ 新 vs 旧(全期間) ===")
    print(f"{'店舗':<14}{'新エッジ':>9}{'旧エッジ':>9}{'差':>8}   {'新島的中':>8}{'旧島的中':>8}")
    for hall in HALLS:
        ne,nir,npr,nn=line(nh[hall]); oe,oir,opr,on=line(oh[hall])
        print(f"{hall:<14}{ne:>+9.0f}{oe:>+9.0f}{ne-oe:>+8.0f}   {nir:>7.0f}%{oir:>7.0f}%")
