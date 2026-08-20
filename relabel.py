#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""既存 data/*_<hall>.csv の空欄 model を models_<hall>.json で埋め直す(サイト非接触)。"""
import csv, os, glob, json

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
HALLS = ["shinkan","honkan","island_akiba","espace_akiba"]

def main():
    for hall in HALLS:
        mp = os.path.join(DATA_DIR, f"models_{hall}.json")
        if not os.path.exists(mp):
            print(f"[{hall}] models_{hall}.json なし → skip"); continue
        mmap = json.load(open(mp, encoding="utf-8"))
        for p in glob.glob(os.path.join(DATA_DIR, f"*_{hall}.csv")):
            if p.endswith("_kishu.csv"): continue
            rows = list(csv.DictReader(open(p, encoding="utf-8")))
            if not rows or "model" not in rows[0]: continue
            changed = 0
            for r in rows:
                if not (r.get("model") or "").strip():
                    m = mmap.get(str(r.get("daban")))
                    if m: r["model"] = m; changed += 1
            if changed:
                with open(p, "w", encoding="utf-8", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                    w.writeheader(); w.writerows(rows)
        # 判明率
        tot=lab=0
        for p in glob.glob(os.path.join(DATA_DIR, f"*_{hall}.csv")):
            if p.endswith("_kishu.csv"): continue
            for r in csv.DictReader(open(p, encoding="utf-8")):
                tot+=1; lab+= 1 if (r.get("model") or "").strip() else 0
        print(f"[{hall}] 機種判明 {lab}/{tot} ({100*lab/tot:.0f}%)" if tot else f"[{hall}] no rows")

if __name__=="__main__":
    main()
