#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""8のつく日(8/18/28)イベント傾向アナライザ。既定=stardust(門前仲町スターダスト)。
店全体の底上げ / 機種別の8のつく日優遇 / 末尾傾向 を、平常日をベースラインに比較する。
使い方: python analyze_day8.py [hall] [event_matsu]   例: python analyze_day8.py stardust 8
"""
import csv, os, glob, sys, statistics as st
from collections import defaultdict
from datetime import date

DATA_DIR=os.path.join(os.path.dirname(os.path.abspath(__file__)),"data")
HALL=sys.argv[1] if len(sys.argv)>1 else "stardust"
EVENT_MATSU=int(sys.argv[2]) if len(sys.argv)>2 else 8

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

def load_daban():
    rows=[]
    for p in sorted(glob.glob(os.path.join(DATA_DIR,f"*_{HALL}.csv"))):
        if p.endswith("_kishu.csv"):continue
        for r in csv.DictReader(open(p,encoding="utf-8")):
            r["_sa"]=ni(r.get("samai"))
            rows.append(r)
    return rows
def load_kishu():
    rows=[]
    for p in sorted(glob.glob(os.path.join(DATA_DIR,f"*_{HALL}_kishu.csv"))):
        rows+=list(csv.DictReader(open(p,encoding="utf-8")))
    return rows

def is_event(dstr): return pd(dstr).day%10==EVENT_MATSU

def main():
    daban=load_daban(); kishu=load_kishu()
    if not daban:
        print(f"[{HALL}] データがまだありません（収集待ち）"); return
    dates=sorted({r["date"] for r in daban})
    ev_dates=[d for d in dates if is_event(d)]
    nm_dates=[d for d in dates if not is_event(d)]
    out=[]
    out.append(f"# {HALL}  {EVENT_MATSU}のつく日トレンド分析")
    out.append(f"\n収集期間: {dates[0]}〜{dates[-1]}（全{len(dates)}日）")
    out.append(f"- {EVENT_MATSU}のつく日: {len(ev_dates)}日  {', '.join(ev_dates)}")
    out.append(f"- 平常日: {len(nm_dates)}日\n")

    # 店全体: 日別 総差枚/平均差枚（台別samaiから算出）
    def day_stats(ds):
        tot=[]; avg=[]; plus=[]
        for d in ds:
            sa=[r["_sa"] for r in daban if r["date"]==d and r["_sa"] is not None]
            if not sa: continue
            tot.append(sum(sa)); avg.append(sum(sa)/len(sa))
            plus.append(100*sum(1 for x in sa if x>0)/len(sa))
        return tot,avg,plus
    et,ea,ep=day_stats(ev_dates); nt,na,npl=day_stats(nm_dates)
    def me(x): return st.mean(x) if x else 0
    out.append("## ① 店全体の底上げ（イベント vs 平常）")
    out.append("| 指標 | "+f"{EVENT_MATSU}のつく日"+" | 平常日 | 差 |")
    out.append("|---|--:|--:|--:|")
    out.append(f"| 平均総差枚/日 | {me(et):+,.0f} | {me(nt):+,.0f} | {me(et)-me(nt):+,.0f} |")
    out.append(f"| 平均差枚/台 | {me(ea):+,.0f} | {me(na):+,.0f} | {me(ea)-me(na):+,.0f} |")
    out.append(f"| 平均プラス率 | {me(ep):.0f}% | {me(npl):.0f}% | {me(ep)-me(npl):+.0f}pt |")

    # ② 機種別: 8のつく日の平均差枚 vs 平常（台加重）, サンプル明示
    def kishu_agg(pred):
        agg=defaultdict(lambda:[0.0,0,0,0])  # sa*n合計, n合計, win, N(勝率分母)
        for r in kishu:
            if not pred(r["date"]):continue
            m=(r.get("model")or"").strip()
            sa=nf(r.get("avg_samai")); n=ni(r.get("total_dai")) or 0
            wn,wN=pw(r.get("win"))
            if m and sa is not None and n>0:
                agg[m][0]+=sa*n; agg[m][1]+=n; agg[m][2]+=wn; agg[m][3]+=wN
        return agg
    ev=kishu_agg(is_event); nmk=kishu_agg(lambda d:not is_event(d))
    rows=[]
    for m,v in ev.items():
        if v[1]<4: continue   # イベント台数サンプル最低
        ev_avg=v[0]/v[1]; ev_wr=100*v[2]/v[3] if v[3] else None
        nv=nmk.get(m)
        nm_avg=(nv[0]/nv[1]) if nv and nv[1] else None
        rows.append({"model":m,"ev_avg":ev_avg,"ev_n":v[1],"ev_wr":ev_wr,
                     "nm_avg":nm_avg,"lift":(ev_avg-nm_avg) if nm_avg is not None else None})
    rows.sort(key=lambda r:r["ev_avg"],reverse=True)
    out.append(f"\n## ② 機種別 {EVENT_MATSU}のつく日の強さ（平均差枚・台加重、上位12）")
    out.append(f"| 機種 | {EVENT_MATSU}日平均差枚(延台) | {EVENT_MATSU}日勝率 | 平常平均差枚 | イベント上乗せ |")
    out.append("|---|--:|--:|--:|--:|")
    for r in rows[:12]:
        wr=f"{r['ev_wr']:.0f}%" if r['ev_wr'] is not None else "-"
        nm=f"{r['nm_avg']:+.0f}" if r['nm_avg'] is not None else "-"
        lift=f"{r['lift']:+.0f}" if r['lift'] is not None else "-"
        out.append(f"| {r['model']} | {r['ev_avg']:+.0f}（{r['ev_n']}） | {wr} | {nm} | {lift} |")

    # ③ 末尾別: 8のつく日の台番末尾ごと平均差枚
    def matsu_agg(pred):
        agg=defaultdict(list)
        for r in daban:
            if not pred(r["date"]) or r["_sa"] is None:continue
            dab=str(r.get("daban") or "")
            if dab and dab[-1].isdigit(): agg[dab[-1]].append(r["_sa"])
        return agg
    em=matsu_agg(is_event); nmm=matsu_agg(lambda d:not is_event(d))
    out.append(f"\n## ③ 末尾別 {EVENT_MATSU}のつく日の平均差枚")
    out.append(f"| 末尾 | {EVENT_MATSU}日平均差枚(延台) | 平常平均差枚 | 差 |")
    out.append("|---|--:|--:|--:|")
    for k in "0123456789":
        e=em.get(k,[]); n=nmm.get(k,[])
        if not e: continue
        ev_a=st.mean(e); nm_a=st.mean(n) if n else None
        d=f"{ev_a-nm_a:+.0f}" if nm_a is not None else "-"
        nm=f"{nm_a:+.0f}" if nm_a is not None else "-"
        out.append(f"| 末尾{k} | {ev_a:+.0f}（{len(e)}） | {nm} | {d} |")

    txt="\n".join(out)
    os.makedirs(os.path.join(os.path.dirname(__file__),"reports"),exist_ok=True)
    open(os.path.join(os.path.dirname(__file__),"reports",f"day{EVENT_MATSU}_{HALL}.md"),"w",encoding="utf-8").write(txt)
    print(txt)

if __name__=="__main__":
    main()
