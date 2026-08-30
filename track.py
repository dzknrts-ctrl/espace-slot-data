#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""予測→答え合わせループ。
  ・predict <date> : その日の狙い島/狙い台を「その日より前のデータだけ」で算出し predictions/<date>.json に保存
  ・evaluate <date>: 保存済み予測を、実際の<date>データで採点 → reports/result_<date>.md ＆ reports/track_record.csv
  ・daily <today>  : 今日を予測＋未採点の過去予測をまとめて採点＋日次レポート reports/daily_report.md を生成
使い方(毎日): python track.py daily 2026-08-22
"""
import csv, os, glob, sys, json, statistics as st
from collections import defaultdict
from datetime import date

BASE=os.path.dirname(os.path.abspath(__file__))
DATA=os.path.join(BASE,"data"); REP=os.path.join(BASE,"reports"); PRED=os.path.join(BASE,"predictions")
HINTS=os.path.join(BASE,"hints")

def load_hint(hall, date):
    p=os.path.join(HINTS,f"{date}_{hall}.json")
    if os.path.exists(p):
        try: return json.load(open(p,encoding="utf-8"))
        except: return None
    return None
HALLS={"shinkan":"エスパス上野新館","honkan":"エスパス上野本館",
       "island_akiba":"アイランド秋葉原","espace_akiba":"エスパス秋葉原駅前"}
WD=["月","火","水","木","金","土","日"]
THR_W,THR_D,THR_N=65.0,108.0,4
N_SHIMA,N_SEAT=3,5

# 機種タイプ: ジャグラー/ハナハナは常に優先。それ以外のノーマルAタイプは打つ機会が少ないため優先度を下げる。
# (このリストはユーザーの実戦に合わせて調整可)
NORMAL_A_KW=["ディスクアップ","ハナビ","サンダーV","アレックス","チバリヨ","ヤバチバ",
             "バーサス","吉宗","クランキー","ドッチ","ニューパルサー","ドンちゃん",
             "ゲッターマウス","マイフラワー","政宗","猪木"]
NICHE_A_PENALTY=1.6   # 非ジャグラー/ハナハナAタイプへの減点(スコアから引く)
def is_niche_A(model):
    m=model or ""
    if "ジャグラー" in m or "ハナハナ" in m: return False
    return any(k in m for k in NORMAL_A_KW)

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
def pdt(s):
    y,m,d=map(int,s.split("-"));return date(y,m,d)
def zz(vals):
    xs=[v for v in vals if v is not None]
    if len(xs)<2:return [0]*len(vals)
    mu=st.mean(xs);sd=st.pstdev(xs) or 1
    return [ (v-mu)/sd if v is not None else 0 for v in vals]

def load_kishu(hall, before=None, on=None):
    rows=[]
    for p in sorted(glob.glob(os.path.join(DATA,f"*_{hall}_kishu.csv"))):
        for r in csv.DictReader(open(p,encoding="utf-8")):
            d=r["date"]
            if before and not d<before: continue
            if on and d!=on: continue
            r["_sa"]=nf(r.get("avg_samai")); r["_de"]=nf(r.get("deri"))
            r["_wn"],r["_wN"]=pw(r.get("win")); r["_n"]=ni(r.get("total_dai")) or 0
            rows.append(r)
    return rows
def load_daban(hall, before=None, on=None):
    rows=[]
    for p in sorted(glob.glob(os.path.join(DATA,f"*_{hall}.csv"))):
        if p.endswith("_kishu.csv"):continue
        for r in csv.DictReader(open(p,encoding="utf-8")):
            d=r["date"]
            if before and not d<before: continue
            if on and d!=on: continue
            r["_sa"]=ni(r.get("samai")); r["_g"]=ni(r.get("gousei")); rows.append(r)
    return rows

# ---------- 予測ロジック ----------
def island_picks(hall, target):
    ty,tm,td=map(int,target.split("-")); twd=date(ty,tm,td).weekday(); tmt=td%10
    ks=load_kishu(hall, before=target)
    if not ks: return []
    dates=sorted({r["date"] for r in ks}); last=dates[-1]
    isl=defaultdict(lambda:{"days":{}, "wn":0,"wN":0,"sa_w":0.0,"dai":0,
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
        rows.append({"model":m,"台数":a["days"].get(last,{}).get("n",0),
            "全体勝率":round(allwr),"平均差枚":round(a["sa_w"]/a["dai"]) if a["dai"] else 0,
            "全ツッパ日数":len(a["push"]),
            "曜勝率":(round(100*a["wd_wn"]/a["wd_wN"]) if a["wd_wN"] else None),"曜N":a["wd_wN"],
            "末尾勝率":(round(100*a["mt_wn"]/a["mt_wN"]) if a["mt_wN"] else None),"末尾N":a["mt_wN"],
            "前日勝率":a["days"].get(last,{}).get("wr"),
            "最終全ツッパ":(sorted(a["push"])[-1] if a["push"] else None),"_allwr":allwr})
    # 検証済み(3ヶ月・持続性r高)シグナルのみで採点: 看板島(全ツッパ頻度)+島勝率+平均差枚。
    # 据え置き/ローテ/曜日/末尾は検証で否定orノイズのため不採用。
    zw=zz([r["全体勝率"] for r in rows]); zp=zz([r["全ツッパ日数"] for r in rows]); zs=zz([r["平均差枚"] for r in rows])
    for i,r in enumerate(rows):
        # 平均差枚を主指標に(検証で島エッジ最大)。看板島(全ツッパ頻度)/勝率は軽い補助。非ジャグラー/ハナハナAタイプは減点。
        r["score"]=zs[i]*1.3 + zp[i]*0.3 + zw[i]*0.1 - (NICHE_A_PENALTY if is_niche_A(r["model"]) else 0)
        reason=[]
        if r["平均差枚"]>=150:  reason.append(f"平均+{r['平均差枚']}")
        if r["全ツッパ日数"]>=3: reason.append(f"看板島(全ツッパ{r['全ツッパ日数']}回)")
        if r["全体勝率"]>=48:   reason.append(f"勝率{r['全体勝率']}%")
        if is_niche_A(r["model"]): reason.append("Aタイプ優先↓")
        r["理由"]="/".join(reason) or "優遇弱"
    rows.sort(key=lambda r:r["score"],reverse=True)
    return rows[:N_SHIMA]

def seat_picks(hall, target):
    db=load_daban(hall, before=target)
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
        seats.append({"daban":dab,"model":model,"プラス率":round(100*plus/len(sa)),
                      "平均差枚":round(st.mean(sa)),"前日差枚":lr["_sa"] if lr else None})
    if seats:   # 平均差枚を主に(勝率は補助)。非ジャグラー/ハナハナAタイプは減点。
        zm=zz([s["平均差枚"] for s in seats]); zp2=zz([s["プラス率"] for s in seats])
        for i,s in enumerate(seats):
            s["_sc"]=zm[i]*1.1 + zp2[i]*0.4 - (NICHE_A_PENALTY if is_niche_A(s["model"]) else 0)
        seats.sort(key=lambda s:s["_sc"],reverse=True)
    return seats[:N_SEAT]

def predict(target):
    os.makedirs(PRED,exist_ok=True)
    picks={}
    for hall in HALLS:
        picks[hall]={"shima":island_picks(hall,target),"seats":seat_picks(hall,target)}
    obj={"date":target,"picks":picks}
    json.dump(obj,open(os.path.join(PRED,f"{target}.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=1)
    return obj

# ---------- 採点ロジック ----------
def evaluate(d):
    pf=os.path.join(PRED,f"{d}.json")
    if not os.path.exists(pf): return None
    pred=json.load(open(pf,encoding="utf-8"))
    # 実データ存在チェック
    if not glob.glob(os.path.join(DATA,f"{d}_*_kishu.csv")): return None
    md=[f"# 答え合わせ  {d}（{WD[pdt(d).weekday()]}）\n"]
    trk=[]
    for hall,jp in HALLS.items():
        ks=load_kishu(hall,on=d); db=load_daban(hall,on=d)
        if not ks: continue
        isl={ (r.get("model")or"").strip():(nf(r.get("avg_samai")),*pw(r.get("win")),ni(r.get("total_dai")) or 0) for r in ks}
        isl_sa=[v[0] for v in isl.values() if v[0] is not None and v[3]>=2]
        med=st.median(isl_sa) if isl_sa else 0
        ranked=sorted([(m,v) for m,v in isl.items() if v[3]>=2], key=lambda kv:(kv[1][0] if kv[1][0] is not None else -9e9),reverse=True)
        irank={m:i+1 for i,(m,_) in enumerate(ranked)}; ni_isl=len(ranked)
        seat={str(r.get("daban")):r["_sa"] for r in db}
        allsa=[r["_sa"] for r in db if r["_sa"] is not None]; hall_avg=st.mean(allsa) if allsa else 0
        p=pred["picks"].get(hall,{})
        # 島採点
        sh_hit=0; sh_tot=0; sh_lines=[]
        for s in p.get("shima",[]):
            m=s["model"]; v=isl.get(m)
            sh_tot+=1
            if v and v[0] is not None:
                hit = v[0] >= med
                sh_hit+= 1 if hit else 0
                sh_lines.append((m, v[0], v[1], v[2], irank.get(m,"-"), ni_isl, hit))
            else:
                sh_lines.append((m, None,0,0,"-",ni_isl,False))
        # 台採点
        se_hit=0; se_tot=0; se_lines=[]; se_sa=[]
        for s in p.get("seats",[]):
            dab=s["daban"]; v=seat.get(dab); se_tot+=1
            if v is not None:
                hit=v>0; se_hit+=1 if hit else 0; se_sa.append(v)
                se_lines.append((dab,s.get("model") or "—",v,hit))
            else:
                se_lines.append((dab,s.get("model") or "—",None,False))
        edge=(st.mean(se_sa)-hall_avg) if se_sa else 0
        md.append(f"\n## {jp}")
        md.append(f"\n**狙い島 {sh_hit}/{sh_tot}的中**（島平均差枚≥当日中央値で的中）")
        md.append("| 島 | 当日平均差枚 | 勝率 | 当日順位 | 判定 |")
        md.append("|---|--:|--:|--:|:--:|")
        for m,sa,wn,wN,rk,nn,hit in sh_lines:
            md.append(f"| {m} | {('%+d'%sa) if sa is not None else '—'} | {wn}/{wN} | {rk}/{nn} | {'⭕' if hit else '❌'} |")
        md.append(f"\n**狙い台 {se_hit}/{se_tot}的中**（差枚プラスで的中） / 狙い台平均 {('%+d'%round(st.mean(se_sa))) if se_sa else '—'} vs 全台平均 {hall_avg:+.0f} → エッジ {edge:+.0f}")
        md.append("| 台番 | 機種 | 当日差枚 | 判定 |")
        md.append("|---|---|--:|:--:|")
        for dab,mo,sa,hit in se_lines:
            md.append(f"| {dab} | {mo} | {('%+d'%sa) if sa is not None else '—'} | {'⭕' if hit else '❌'} |")
        md.append("")
        trk.append({"date":d,"hall":hall,"島的中":sh_hit,"島数":sh_tot,"台的中":se_hit,"台数":se_tot,
                    "狙い台平均差枚":round(st.mean(se_sa)) if se_sa else "","全台平均差枚":round(hall_avg),"エッジ":round(edge)})
    open(os.path.join(REP,f"result_{d}.md"),"w",encoding="utf-8").write("\n".join(md))
    # track_record.csv 追記(重複日は上書き)
    tr=os.path.join(REP,"track_record.csv")
    existing=[]
    if os.path.exists(tr):
        existing=[r for r in csv.DictReader(open(tr,encoding="utf-8-sig")) if r["date"]!=d]
    fields=["date","hall","島的中","島数","台的中","台数","狙い台平均差枚","全台平均差枚","エッジ"]
    with open(tr,"w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for r in existing: w.writerow(r)
        for r in trk: w.writerow(r)
    return "\n".join(md)

def cumulative():
    tr=os.path.join(REP,"track_record.csv")
    if not os.path.exists(tr): return None
    rows=list(csv.DictReader(open(tr,encoding="utf-8-sig")))
    agg=defaultdict(lambda:{"ih":0,"it":0,"sh":0,"stt":0,"edge":[]})
    for r in rows:
        for scope in (r["hall"],"__all__"):
            a=agg[scope]; a["ih"]+=int(r["島的中"]);a["it"]+=int(r["島数"])
            a["sh"]+=int(r["台的中"]);a["stt"]+=int(r["台数"])
            if r["エッジ"]!="":a["edge"].append(int(r["エッジ"]))
    days=sorted({r["date"] for r in rows})
    return {"days":days,"agg":agg}

# ---------- 日次レポート ----------
def build_daily(today):
    pred=predict(today)
    # 未採点の過去予測を採点
    for pf in sorted(glob.glob(os.path.join(PRED,"*.json"))):
        d=os.path.basename(pf)[:-5]
        if d>=today: continue
        if os.path.exists(os.path.join(REP,f"result_{d}.md")): continue
        if glob.glob(os.path.join(DATA,f"{d}_*_kishu.csv")):
            evaluate(d)
    tw=WD[pdt(today).weekday()]; tmt=int(today[-2:])%10
    md=[f"# エスパス4店 デイリー狙い＆結果レポート  {today}（{tw}・末尾{tmt}）\n"]
    # 直近の答え合わせ(あれば)
    results=sorted(glob.glob(os.path.join(REP,"result_*.md")))
    if results:
        lastd=os.path.basename(results[-1])[7:-3]
        md.append(f"## ✅ 直近({lastd})の答え合わせ")
        cum=cumulative()
        if cum:
            a=cum["agg"]["__all__"]
            ir=100*a["ih"]/a["it"] if a["it"] else 0; sr=100*a["sh"]/a["stt"] if a["stt"] else 0
            ed=st.mean(a["edge"]) if a["edge"] else 0
            md.append(f"\n**累積成績（{len(cum['days'])}日）**： 島的中 {a['ih']}/{a['it']}（{ir:.0f}%） / 台的中 {a['sh']}/{a['stt']}（{sr:.0f}%） / 平均エッジ {ed:+.0f}枚\n")
        md.append(f"（各店の詳細は reports/result_{lastd}.md）\n")
        # 直近結果の要約表
        tr=os.path.join(REP,"track_record.csv")
        rows=[r for r in csv.DictReader(open(tr,encoding="utf-8-sig")) if r["date"]==lastd]
        md.append("| 店 | 島的中 | 台的中 | 狙い台平均 | 全台平均 | エッジ |")
        md.append("|---|--:|--:|--:|--:|--:|")
        for r in rows:
            md.append(f"| {HALLS[r['hall']]} | {r['島的中']}/{r['島数']} | {r['台的中']}/{r['台数']} | {r['狙い台平均差枚']} | {r['全台平均差枚']} | {r['エッジ']} |")
        md.append("")
    # 今日の狙い
    md.append(f"## 🎯 今日({today})の狙い")
    for hall,jp in HALLS.items():
        p=pred["picks"][hall]
        h=load_hint(hall,today)
        md.append(f"\n### {jp}")
        # 📢 示唆(画像/メール由来)を最優先で反映
        if h:
            tags=[]
            if h.get("torizai"): tags.append("🎪取材イベント日")
            if h.get("event"): tags.append(h["event"])
            if (h.get("strength")=="strong"): tags.append("【強】")
            if tags: md.append("📢 **示唆**： "+" ／ ".join(tags))
            hk=[k for k in (h.get("kishu") or []) if k]
            if hk: md.append("　示唆機種(全台/強調)： "+"・".join(hk)+" ← 最優先チェック")
            if h.get("tanjoubi"): md.append("　誕生日連動: "+"・".join(h["tanjoubi"]))
            if h.get("raw"): md.append(f"　<sub>{h['raw']}</sub>")
        md.append("**狙い島**： "+(" ／ ".join(f"**{s['model']}**({s['台数']}台・{s['理由']})" for s in p["shima"]) or "—"))
        seat_note = "　※この店は台クセが弱く(検証r低)、台番は参考程度。島単位で狙う" if hall in ("island_akiba","espace_akiba") else ""
        md.append("**狙い台**： "+(" ／ ".join(f"{s['daban']}{'('+s['model']+')' if s['model'] else ''}[プラス率{s['プラス率']}%]" for s in p["seats"]) or "—") + seat_note)
    open(os.path.join(REP,"daily_report.md"),"w",encoding="utf-8").write("\n".join(md))
    print("\n".join(md))

if __name__=="__main__":
    cmd=sys.argv[1] if len(sys.argv)>1 else "daily"
    arg=sys.argv[2] if len(sys.argv)>2 else date.today().isoformat()
    if cmd=="predict": predict(arg); print("predicted",arg)
    elif cmd=="evaluate": print(evaluate(arg) or f"評価不可(予測またはデータなし): {arg}")
    else: build_daily(arg)
