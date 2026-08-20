#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reports/data.json から自己完結HTMLダッシュボード reports/dashboard.html を生成する。"""
import os, json, html
REP=os.path.join(os.path.dirname(os.path.abspath(__file__)),"reports")

def main():
    data=json.load(open(os.path.join(REP,"data.json"),encoding="utf-8"))
    payload=json.dumps(data,ensure_ascii=False)
    htmltext=PAGE.replace("/*__DATA__*/","const DATA="+payload+";")
    open(os.path.join(REP,"dashboard.html"),"w",encoding="utf-8").write(htmltext)
    print("wrote", os.path.join(REP,"dashboard.html"))

PAGE=r"""<!doctype html><html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>エスパス出玉レーダー</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700&family=Noto+Sans+JP:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#FBFAF7; --panel:#FFFFFF; --ink:#1E1A14; --muted:#7A7062; --line:#EAE4D8;
  --accent:#B4791A; --accent-soft:#F5E9CE; --plus:#1E7A4C; --minus:#BE3B2B; --zero:#9A9082;
  --shadow:0 1px 2px rgba(30,26,20,.05),0 6px 20px rgba(30,26,20,.04);
}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){
  --bg:#141109; --panel:#1E1A11; --ink:#EFE9DC; --muted:#A79A84; --line:#2E2717;
  --accent:#E0A63A; --accent-soft:#39301A; --plus:#5FD199; --minus:#F0796C; --zero:#8A8070;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 8px 26px rgba(0,0,0,.35);
}}
:root[data-theme=dark]{
  --bg:#141109; --panel:#1E1A11; --ink:#EFE9DC; --muted:#A79A84; --line:#2E2717;
  --accent:#E0A63A; --accent-soft:#39301A; --plus:#5FD199; --minus:#F0796C; --zero:#8A8070;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 8px 26px rgba(0,0,0,.35);
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:"Noto Sans JP",system-ui,sans-serif;line-height:1.5;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px 80px}
header{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--bg) 88%,transparent);
  backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.head-in{max-width:1180px;margin:0 auto;padding:14px 20px;display:flex;align-items:baseline;gap:16px;flex-wrap:wrap}
.brand{font-family:Oswald,sans-serif;font-weight:700;font-size:26px;letter-spacing:.04em;color:var(--ink)}
.brand b{color:var(--accent)}
.tagline{font-size:12.5px;color:var(--muted)}
.range{margin-left:auto;font-size:12.5px;color:var(--muted);font-variant-numeric:tabular-nums}
.tabs{display:flex;gap:8px;flex-wrap:wrap;margin:22px 0 6px}
.tab{font-family:Oswald,sans-serif;font-weight:600;letter-spacing:.02em;font-size:14px;
  padding:8px 15px;border:1px solid var(--line);border-radius:999px;background:var(--panel);
  color:var(--muted);cursor:pointer;transition:.15s}
.tab:hover{color:var(--ink);border-color:var(--accent)}
.tab.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0 8px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;box-shadow:var(--shadow)}
.kpi .lab{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:700}
.kpi .val{font-family:Oswald,sans-serif;font-weight:700;font-size:30px;margin-top:4px;font-variant-numeric:tabular-nums}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:18px}
@media(max-width:820px){.grid{grid-template-columns:1fr}}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow);overflow:hidden}
.panel.wide{grid-column:1/-1}
.panel h2{margin:0;padding:15px 18px 6px;font-size:15px;font-weight:700;display:flex;align-items:baseline;gap:9px}
.panel h2 .no{font-family:Oswald,sans-serif;color:var(--accent);font-size:13px;font-weight:700}
.panel .sub{padding:0 18px 12px;font-size:12px;color:var(--muted)}
.scroll{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:8px 12px;text-align:right;white-space:nowrap;border-top:1px solid var(--line)}
th:first-child,td:first-child{text-align:left;white-space:normal}
thead th{position:sticky;top:0;background:var(--panel);font-size:11px;letter-spacing:.04em;color:var(--muted);
  text-transform:uppercase;font-weight:700;border-top:none}
tbody tr:hover{background:color-mix(in srgb,var(--accent-soft) 40%,transparent)}
td.num{font-variant-numeric:tabular-nums}
.pos{color:var(--plus);font-weight:700}.neg{color:var(--minus)}.zer{color:var(--zero)}
.model{max-width:230px;overflow:hidden;text-overflow:ellipsis}
.bar{display:flex;align-items:center;gap:9px;padding:5px 18px;font-size:12.5px}
.bar .d{width:78px;color:var(--muted);font-variant-numeric:tabular-nums}
.bar .track{flex:1;height:16px;background:var(--line);border-radius:4px;overflow:hidden;position:relative}
.bar .fill{position:absolute;top:0;bottom:0;left:50%;border-radius:3px}
.bar .v{width:82px;text-align:right;font-variant-numeric:tabular-nums;font-weight:600}
.note{font-size:11.5px;color:var(--muted);margin-top:26px;padding-top:14px;border-top:1px solid var(--line)}
.pill{display:inline-block;font-size:10.5px;font-weight:700;padding:1px 7px;border-radius:999px;
  background:var(--accent-soft);color:var(--accent);letter-spacing:.03em}
</style></head><body>
<header><div class="head-in">
  <div class="brand">エスパス<b>出玉レーダー</b></div>
  <div class="tagline">上野2店・秋葉原2店／全台データ日次集計</div>
  <div class="range" id="range"></div>
</div></header>
<div class="wrap">
  <div class="tabs" id="tabs"></div>
  <div id="view"></div>
  <div class="note" id="note"></div>
</div>
<script>
/*__DATA__*/
const HN=DATA.hall_names, HALLS=Object.keys(DATA.halls);
const el=(t,c,h)=>{const e=document.createElement(t);if(c)e.className=c;if(h!=null)e.innerHTML=h;return e;};
const jp=n=>n==null?'-':n.toLocaleString('ja-JP');
const cls=v=>v==null?'zer':v>0?'pos':v<0?'neg':'zer';
const sign=v=>v==null?'-':(v>0?'+':'')+jp(Math.round(v));
function tbl(cols,rows,render){
  const w=el('div','scroll'),t=el('table'),th=el('thead'),tr=el('tr');
  cols.forEach(c=>tr.appendChild(el('th',null,c)));th.appendChild(tr);t.appendChild(th);
  const tb=el('tbody');rows.forEach(r=>tb.appendChild(render(r)));t.appendChild(tb);w.appendChild(t);return w;
}
function panel(no,title,sub,node){
  const p=el('div','panel');p.appendChild(el('h2',null,`<span class="no">${no}</span> ${title}`));
  if(sub)p.appendChild(el('div','sub',sub));p.appendChild(node);return p;
}
function render(hall){
  const d=DATA.halls[hall], v=document.getElementById('view');v.innerHTML='';
  document.getElementById('range').textContent=d.dates[0]+' 〜 '+d.dates[d.dates.length-1]+'（'+d.dates.length+'日）';
  // KPIs (最新日)
  const last=d.dates[d.dates.length-1], lastTot=d.day_total[last];
  const totals=Object.values(d.day_total), avgHall=totals.reduce((a,b)=>a+b,0)/totals.length;
  const kp=el('div','kpis');
  const mk=(l,val,c)=>{const k=el('div','kpi');k.appendChild(el('div','lab',l));
    const e=el('div','val '+(c||''),val);k.appendChild(e);return k;};
  kp.appendChild(mk('最新営業日',last.slice(5)));
  kp.appendChild(mk('最新日 総差枚',sign(lastTot),cls(lastTot)));
  kp.appendChild(mk('日平均 総差枚',sign(Math.round(avgHall)),cls(avgHall)));
  kp.appendChild(mk('機種数',jp(d.model_summary.length)));
  v.appendChild(kp);

  const grid=el('div','grid');
  // A 機種別サマリ
  grid.appendChild(panel('01','力の入る機種','平均差枚（台加重）上位。勝率＝機種内の勝ち台率',
    tbl(['機種','平均差枚','勝率','設置','出率'],d.model_summary.slice(0,15),r=>{
      const tr=el('tr');
      tr.appendChild(el('td','model',r.model));
      tr.appendChild(el('td','num '+cls(r['平均差枚']),sign(r['平均差枚'])));
      tr.appendChild(el('td','num',r['勝率%']==null?'-':r['勝率%']+'%'));
      tr.appendChild(el('td','num',jp(r['設置台数'])));
      tr.appendChild(el('td','num',r['平均出率']==null?'-':r['平均出率']+'%'));
      return tr;})));
  // B 台番別クセ
  grid.appendChild(panel('02','注目の台番','据え置き/クセの強い台番。スコア＝プラス率×平均差枚',
    tbl(['台番','機種','平均差枚','ﾌﾟﾗｽ率','最新'],d.daban_habits.slice(0,15),r=>{
      const tr=el('tr');
      tr.appendChild(el('td','num',r.daban));
      tr.appendChild(el('td','model',r.model||'—'));
      tr.appendChild(el('td','num '+cls(r['平均差枚']),sign(r['平均差枚'])));
      tr.appendChild(el('td','num',r['プラス率%']+'%'));
      tr.appendChild(el('td','num '+cls(r['最新差枚']),sign(r['最新差枚'])));
      return tr;})));
  v.appendChild(grid);

  // C 日付タイプ(店全体) as bars + 機種別上位
  const dh=d.datetype_hall.filter(x=>x['平均差枚']!=null);
  const maxAbs=Math.max(60,...dh.map(x=>Math.abs(x['平均差枚'])));
  const barNode=el('div');barNode.style.padding='6px 0 12px';
  dh.forEach(x=>{
    const row=el('div','bar');row.appendChild(el('div','d',x['日付タイプ']));
    const track=el('div','track'),fill=el('div','fill');
    const w=Math.abs(x['平均差枚'])/maxAbs*50;
    fill.style.width=w+'%';
    if(x['平均差枚']>=0){fill.style.left='50%';fill.style.background='var(--plus)';}
    else{fill.style.left=(50-w)+'%';fill.style.background='var(--minus)';}
    track.appendChild(fill);row.appendChild(track);
    const val=el('div','v '+cls(x['平均差枚']),sign(x['平均差枚']));row.appendChild(val);
    barNode.appendChild(row);
  });
  const gridC=el('div','grid');
  gridC.appendChild(panel('03','日付タイプ別の出やすさ','店全体の平均差枚/台。曜日・末尾・旧イベント日で比較（日数が増えるほど精度向上）',barNode));
  // 日付タイプ×機種 勝率上位
  const dt=d.datetype.slice().sort((a,b)=>(b['勝率%']||0)-(a['勝率%']||0)).slice(0,15);
  gridC.appendChild(panel('04','日付タイプ×機種 本命','勝率が高い＝その日付タイプで高設定が入りやすいシマ',
    tbl(['日付タイプ','機種','勝率','平均差枚'],dt,r=>{
      const tr=el('tr');
      tr.appendChild(el('td',null,'<span class="pill">'+r['日付タイプ']+'</span>'));
      tr.appendChild(el('td','model',r.model));
      tr.appendChild(el('td','num',r['勝率%']==null?'-':r['勝率%']+'%'));
      tr.appendChild(el('td','num '+cls(r['平均差枚']),sign(r['平均差枚'])));
      return tr;})));
  v.appendChild(gridC);
}
// tabs
const tabs=document.getElementById('tabs');
HALLS.forEach((h,i)=>{const b=el('button','tab'+(i===0?' on':''),HN[h]);
  b.onclick=()=>{document.querySelectorAll('.tab').forEach(t=>t.classList.remove('on'));b.classList.add('on');render(h);};
  tabs.appendChild(b);});
document.getElementById('note').innerHTML='データ出典: みんレポ（独自調査値・参考情報）。設定/勝敗を保証するものではありません。日次自動更新。';
render(HALLS[0]);
</script></body></html>"""

if __name__=="__main__":
    main()
