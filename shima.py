#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""島（機種列）単位の設定投入分析。機種別集計(_kishu.csv)から、島ごとに
  ・全ツッパ日（島の大半が勝ち＝まとめて設定投入）を検出
  ・看板島（常連で設定が入る島）をランキング
  ・指定日の狙い島（優遇度＋曜日/末尾傾向＋ローテ/据え置き）を算出
併せて台番別データから島内の個別狙い台（角台/据え置き）を補助表示。
使い方: python shima.py 2026-08-21
"""
import csv, os, glob, sys, statistics as st
from collections import defaultdict
from datetime import date
DATA=os.path.join(os.path.dirname(os.path.abspath(__file__)),"data")
REP=os.path.join(os.path.dirname(os.path.abspath(__file__)),"reports")
HALLS={"shinkan":"エスパス上野新館","honkan":"エスパス上野本館",
       "island_akiba":"アイランド秋葉原","espace_akiba":"エスパス秋葉原駅前"}
WD=["月","火","水","木","金","土","日"]
# 全ツッパ判定: 島の勝率≥THR_W かつ 平均出率≥THR_D かつ 台数≥THR_N
THR_W, THR_D, THR_N = 65.0, 108.0, 4

def nf(s):
    try:return float(str(s).replace(",",""))
    except:return None
def ni(s):
    try:return int(float(str(s).replace(",","")))
    except:return None
def pw(s):
    p=(str(s)or"").split("/")
    try:return int(p[0]),int(p[1])
    except:return 0,0
def pd(s):
    y,m,d=map(int,s.split("-"));return date(y,m,d)
def z(vals):
    xs=[v for v in vals if v is not None]
    if len(xs)<2:return [0]*len(vals)
    mu=st.mean(xs);sd=st.pstdev(xs) or 1
    return [ (v-mu)/sd if v is not None else 0 for v in vals]

def load_kishu(hall):
    rows=[]
    for p in sorted(glob.glob(os.path.join(DATA,f"*_{hall}_kishu.csv"))):
        for r in csv.DictReader(open(p,encoding="utf-8")):
            r["_sa"]=nf(r.get("avg_samai")); r["_de"]=nf(r.get("deri"))
            r["_wn"],r["_wN"]=pw(r.get("win")); r["_n"]=ni(r.get("total_dai")) or 0
            rows.append(r)
    return rows
def load_daban(hall):
    rows=[]
    for p in sorted(glob.glob(os.path.join(DATA,f"*_{hall}.csv"))):
        if p.endswith("_kishu.csv"):continue
        for r in csv.DictReader(open(p,encoding="utf-8")):
            r["_sa"]=ni(r.get("samai")); r["_g"]=ni(r.get("gousei")); rows.append(r)
    return rows

def analyze(hall, target):
    ty,tm,tdd=map(int,target.split("-")); tdate=date(ty,tm,tdd); twd=tdate.weekday(); tmt=tdd%10
    ks=load_kishu(hall)
    if not ks:return None
    dates=sorted({r["date"] for r in ks}); last=dates[-1]
    # 島(機種)ごとに日別集計
    isl=defaultdict(lambda:{"days":{}, "wn":0,"wN":0,"sa_w":0.0,"dai":0,
                            "wd_wn":0,"wd_wN":0,"mt_wn":0,"mt_wN":0,"push":[]})
    for r in ks:
        m=(r.get("model")or"").strip() or "(不明)"
        if r["_n"]<2: continue          # 1台島は"島"扱いしない(個別枠)
        a=isl[m]; d=r["date"]
        wr=100*r["_wn"]/r["_wN"] if r["_wN"] else None
        a["days"][d]={"wr":wr,"de":r["_de"],"sa":r["_sa"],"n":r["_n"]}
        a["wn"]+=r["_wn"];a["wN"]+=r["_wN"];a["dai"]+=r["_n"]
        if r["_sa"] is not None:a["sa_w"]+=r["_sa"]*r["_n"]
        dt=pd(d)
        if dt.weekday()==twd:a["wd_wn"]+=r["_wn"];a["wd_wN"]+=r["_wN"]
        if dt.day%10==tmt:a["mt_wn"]+=r["_wn"];a["mt_wN"]+=r["_wN"]
        # 全ツッパ判定
        if wr is not None and wr>=THR_W and (r["_de"] or 0)>=THR_D and r["_n"]>=THR_N:
            a["push"].append(d)
    rows=[]
    for m,a in isl.items():
        if a["wN"]<10: continue
        rows.append({"model":m,"台数":a["days"].get(last,{}).get("n", a["dai"]//max(1,len(a["days"]))),
            "全体勝率":100*a["wn"]/a["wN"], "平均差枚":round(a["sa_w"]/a["dai"]) if a["dai"] else 0,
            "全ツッパ日数":len(a["push"]), "全ツッパ日":sorted(a["push"]),
            "曜勝率":(100*a["wd_wn"]/a["wd_wN"] if a["wd_wN"] else None),"曜N":a["wd_wN"],
            "末尾勝率":(100*a["mt_wn"]/a["mt_wN"] if a["mt_wN"] else None),"末尾N":a["mt_wN"],
            "前日勝率":a["days"].get(last,{}).get("wr"),"前日差枚":a["days"].get(last,{}).get("sa"),
            "最終全ツッパ":(sorted(a["push"])[-1] if a["push"] else None)})
    # 今日の狙い島スコア
    zw=z([r["全体勝率"] for r in rows]); zp=z([r["全ツッパ日数"] for r in rows]); zs=z([r["平均差枚"] for r in rows])
    for i,r in enumerate(rows):
        wd=(r["曜勝率"] or r["全体勝率"]); mt=(r["末尾勝率"] or r["全体勝率"])
        # ローテ: 最終全ツッパからの経過日(空きが大きい看板島=そろそろ入る期待)
        gap=0
        if r["最終全ツッパ"]:
            gap=(pd(last)-pd(r["最終全ツッパ"])).days
        rot=min(gap,10)/10 if r["全ツッパ日数"]>=2 else 0
        r["狙い島スコア"]=round(zw[i]*1.0+zp[i]*0.8+zs[i]*0.5+((wd-r['全体勝率'])/100)*0.6+((mt-r['全体勝率'])/100)*0.4+rot*0.4,3)
    return {"dates":dates,"last":last,"twd":twd,"tmt":tmt,"rows":rows}

def top_seats(hall, models_hint=None, k=3):
    """島内の個別狙い台（台番別: 高プラス率＋据え置き）。機種名がある店はmodelで島特定。"""
    db=load_daban(hall)
    byd=defaultdict(list)
    for r in db: byd[str(r.get("daban"))].append(r)
    dates=sorted({r["date"] for r in db}); last=dates[-1] if dates else None
    seats=[]
    for dab,rs in byd.items():
        rs=sorted(rs,key=lambda r:r["date"]); sa=[r["_sa"] for r in rs if r["_sa"] is not None]
        if len(sa)<5:continue
        plus=sum(1 for x in sa if x>0)
        model=next((r.get("model") for r in reversed(rs) if (r.get("model")or"").strip()),"")
        lr=next((r for r in reversed(rs) if r["date"]==last),None)
        seats.append({"daban":dab,"model":model,"plus":100*plus/len(sa),"mean":st.mean(sa),
                      "last_sa":lr["_sa"] if lr else None,"last_g":lr["_g"] if lr else None})
    seats.sort(key=lambda s:(s["plus"],s["mean"]),reverse=True)
    return seats

def main():
    target=sys.argv[1] if len(sys.argv)>1 else "2026-08-21"
    ty,tm,tdd=map(int,target.split("-")); twd=date(ty,tm,tdd).weekday(); tmt=tdd%10
    out=[f"# 島単位・設定投入 狙い分析  {target}（{WD[twd]}曜・末尾{tmt}）",
         f"\n全ツッパ判定＝島の勝率≥{THR_W:.0f}% かつ 平均出率≥{THR_D:.0f}% かつ {THR_N}台以上（＝島の大半が高設定挙動）\n"]
    for hall,jp in HALLS.items():
        res=analyze(hall,target)
        if not res:continue
        rows=res["rows"]; last=res["last"]
        out.append(f"\n## {jp}（{res['dates'][0]}〜{last} {len(res['dates'])}日）")
        # 看板島(常連設定投入)
        board=sorted(rows,key=lambda r:(r["全ツッパ日数"],r["全体勝率"]),reverse=True)[:6]
        out.append(f"\n### 看板島（設定が入りやすい常連島）")
        out.append("| 島(機種) | 台数 | 全体勝率 | 全ツッパ日数 | 平均差枚 | 直近全ツッパ |")
        out.append("|---|--:|--:|--:|--:|--:|")
        for r in board:
            out.append(f"| {r['model']} | {r['台数']} | {r['全体勝率']:.0f}% | {r['全ツッパ日数']}日 | {r['平均差枚']:+.0f} | {(r['最終全ツッパ'] or '-')[5:] if r['最終全ツッパ'] else '-'} |")
        # 今日の狙い島
        pick=sorted(rows,key=lambda r:r["狙い島スコア"],reverse=True)[:6]
        out.append(f"\n### ★今日の狙い島 TOP6（優遇度＋{WD[twd]}/末尾{tmt}傾向＋ローテ）")
        out.append("| 島(機種) | 台数 | "+WD[twd]+"勝率(N) | 末尾"+str(tmt)+"勝率(N) | 前日 | 空き日数 | 判断 |")
        out.append("|---|--:|--:|--:|--:|--:|---|")
        for r in pick:
            wd=f"{r['曜勝率']:.0f}%({r['曜N']})" if r['曜勝率'] is not None else f"-({r['曜N']})"
            mt=f"{r['末尾勝率']:.0f}%({r['末尾N']})" if r['末尾勝率'] is not None else f"-({r['末尾N']})"
            gap=(date.fromisoformat(last)-date.fromisoformat(r['最終全ツッパ'])).days if r['最終全ツッパ'] else '-'
            note=[]
            if r["前日勝率"] is not None and r["前日勝率"]>=65: note.append("前日好調→据置期待")
            if isinstance(gap,int) and gap>=5 and r["全ツッパ日数"]>=2: note.append("そろそろ入る?")
            out.append(f"| {r['model']} | {r['台数']} | {wd} | {mt} | {('好' if (r['前日勝率'] or 0)>=65 else '-')} | {gap} | {'/'.join(note) or '-'} |")
        # 直近3日の全ツッパ島(据え置き候補)
        recent=sorted([r for r in rows if r["最終全ツッパ"] and (date.fromisoformat(last)-date.fromisoformat(r["最終全ツッパ"])).days<=2],
                      key=lambda r:r["最終全ツッパ"],reverse=True)
        out.append(f"\n### 直近3日で全ツッパした島（据え置き狙いの候補）")
        if recent:
            out.append(", ".join(f"{r['model']}({r['最終全ツッパ'][5:]})" for r in recent[:8]))
        else:
            out.append("（該当なし）")
        out.append("")
    txt="\n".join(out)
    os.makedirs(REP,exist_ok=True)
    open(os.path.join(REP,f"shima_{target}.md"),"w",encoding="utf-8").write(txt)
    print(txt)

if __name__=="__main__":
    main()
