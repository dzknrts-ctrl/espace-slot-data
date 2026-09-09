#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reports/monthly_all.json から月間差枚データ帳HTML(reports/monthly.html)を生成。"""
import json, os
BASE=os.path.dirname(os.path.abspath(__file__))
data=open(os.path.join(BASE,"reports","monthly_all.json"),encoding="utf-8").read()

HTML = r"""<title>月間差枚データ帳</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Zen+Kaku+Gothic+New:wght@500;700;900&family=IBM+Plex+Sans+JP:wght@400;500;600;700&display=swap">
<style>
:root{
  --bg:#f2efe8; --panel:#fbfaf6; --panel2:#f6f3ec; --ink:#1b1e26; --muted:#6a6f7d;
  --line:#e2ddd2; --line2:#d3cdbf;
  --plus:#0e7a52; --plus-bar:#1fae76; --plus-soft:#e7f4ec;
  --minus:#b23b2b; --minus-bar:#df5a48; --minus-soft:#faeae6;
  --gold:#b8860b; --gold-soft:#f6eccf;
  --accent:#2b4a6f;
  --shadow:0 1px 2px rgba(20,22,30,.05),0 8px 24px rgba(20,22,30,.06);
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --bg:#12141a; --panel:#1a1d25; --panel2:#161922; --ink:#eceef3; --muted:#8b91a1;
    --line:#282c37; --line2:#333846;
    --plus:#34d399; --plus-bar:#2b9c72; --plus-soft:#122a22;
    --minus:#f4796a; --minus-bar:#b1463a; --minus-soft:#2c1815;
    --gold:#e7b64a; --gold-soft:#2e2610;
    --accent:#7ea6d6;
    --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35);
  }
}
:root[data-theme="dark"]{
  --bg:#12141a; --panel:#1a1d25; --panel2:#161922; --ink:#eceef3; --muted:#8b91a1;
  --line:#282c37; --line2:#333846;
  --plus:#34d399; --plus-bar:#2b9c72; --plus-soft:#122a22;
  --minus:#f4796a; --minus-bar:#b1463a; --minus-soft:#2c1815;
  --gold:#e7b64a; --gold-soft:#2e2610;
  --accent:#7ea6d6;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35);
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:"IBM Plex Sans JP",system-ui,sans-serif;
  -webkit-font-smoothing:antialiased;line-height:1.5;
  font-feature-settings:"palt";}
.wrap{max-width:1180px;margin:0 auto;padding:28px 20px 80px;}
.tnum{font-variant-numeric:tabular-nums}
/* masthead */
.mast{display:flex;flex-wrap:wrap;align-items:flex-end;gap:14px 22px;
  border-bottom:2px solid var(--ink);padding-bottom:16px;margin-bottom:8px;}
.mast h1{font-family:"Zen Kaku Gothic New",sans-serif;font-weight:900;
  font-size:clamp(26px,4.4vw,40px);letter-spacing:.01em;margin:0;line-height:1.02;
  text-wrap:balance;}
.mast .sub{color:var(--muted);font-size:13px;letter-spacing:.02em;margin-top:6px;}
.mast .spacer{flex:1}
.mfield{display:flex;flex-direction:column;gap:5px}
.mfield label{font-size:10.5px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
select{font-family:inherit;font-size:15px;font-weight:600;color:var(--ink);
  background:var(--panel);border:1px solid var(--line2);border-radius:9px;
  padding:9px 32px 9px 12px;appearance:none;cursor:pointer;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'><path d='M2 4l4 4 4-4' fill='none' stroke='%238a90a0' stroke-width='1.6'/></svg>");
  background-repeat:no-repeat;background-position:right 11px center;}
select:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
/* hall pills */
.halls{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 22px}
.pill{font-family:inherit;font-size:13.5px;font-weight:600;color:var(--muted);
  background:transparent;border:1px solid var(--line2);border-radius:999px;
  padding:8px 15px;cursor:pointer;transition:.15s;white-space:nowrap}
.pill:hover{color:var(--ink);border-color:var(--ink)}
.pill[aria-pressed="true"]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.pill:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
/* summary band */
.band{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px 26px;
  background:var(--panel);border:1px solid var(--line);border-radius:14px;
  box-shadow:var(--shadow);padding:20px 24px;margin-bottom:24px}
.band .hn{font-family:"Zen Kaku Gothic New",sans-serif;font-weight:700;font-size:20px}
.band .total{font-family:"Zen Kaku Gothic New",sans-serif;font-weight:900;
  font-size:clamp(30px,6vw,46px);line-height:1;letter-spacing:-.01em}
.band .tlabel{font-size:11px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
.band .meta{color:var(--muted);font-size:13px}
.pos{color:var(--plus)} .neg{color:var(--minus)}
/* columns */
.cols{display:grid;grid-template-columns:1fr 1fr;gap:22px}
@media(max-width:760px){.cols{grid-template-columns:1fr;gap:30px}}
.col h2{font-family:"Zen Kaku Gothic New",sans-serif;font-size:15px;font-weight:700;
  margin:0 0 3px;display:flex;align-items:center;gap:8px}
.col .cap{font-size:11.5px;color:var(--muted);margin:0 0 12px}
.dot{width:10px;height:10px;border-radius:3px;display:inline-block}
.dot.p{background:var(--plus-bar)} .dot.m{background:var(--minus-bar)}
table{width:100%;border-collapse:collapse}
tr{border-bottom:1px solid var(--line)}
tr:last-child{border-bottom:none}
td{padding:8px 4px;vertical-align:middle}
.rk{width:26px;color:var(--muted);font-size:12px;font-weight:600;text-align:right;padding-right:8px}
.nm{font-size:13.5px;font-weight:500;line-height:1.3}
.nm .cnt{color:var(--muted);font-weight:400;font-size:11px;margin-left:2px}
.val{width:96px;text-align:right;font-weight:600;font-size:13.5px;white-space:nowrap}
.barcell{width:34%;padding-left:10px}
.bar{height:8px;border-radius:5px;min-width:2px}
.bar.p{background:linear-gradient(90deg,var(--plus-soft),var(--plus-bar))}
.bar.m{background:linear-gradient(90deg,var(--minus-soft),var(--minus-bar))}
tr.top .rk{color:var(--gold)}
tr.top .rk::before{content:"●";font-size:8px;margin-right:3px;color:var(--gold)}
.empty{color:var(--muted);font-size:13px;padding:14px 4px}
.foot{margin-top:34px;padding-top:16px;border-top:1px solid var(--line);
  color:var(--muted);font-size:12px;line-height:1.7}
.foot b{color:var(--ink);font-weight:600}
</style>

<div class="wrap">
  <div class="mast">
    <div>
      <h1>月間差枚データ帳</h1>
      <div class="sub">6店舗 ／ 機種別トータル差枚（＝Σ 平均差枚×台数）</div>
    </div>
    <div class="spacer"></div>
    <div class="mfield">
      <label for="mon">対象月</label>
      <select id="mon"></select>
    </div>
  </div>
  <div class="halls" id="halls"></div>
  <div class="band" id="band"></div>
  <div class="cols">
    <div class="col">
      <h2><span class="dot p"></span>優秀機種（プラス）</h2>
      <p class="cap" id="capP"></p>
      <table id="tblP"></table>
    </div>
    <div class="col">
      <h2><span class="dot m"></span>マイナス機種</h2>
      <p class="cap" id="capM"></p>
      <table id="tblM"></table>
    </div>
  </div>
  <div class="foot" id="foot"></div>
</div>

<script id="data" type="application/json">__DATA__</script>
<script>
const DB=JSON.parse(document.getElementById('data').textContent);
const monSel=document.getElementById('mon'), hallsEl=document.getElementById('halls');
const monthLabel=m=>({'01':'1月','02':'2月','03':'3月','04':'4月','05':'5月','06':'6月','07':'7月','08':'8月','09':'9月','10':'10月','11':'11月','12':'12月'})[m.split('-')[1]];
const fmt=n=>(n>0?'+':'')+n.toLocaleString('en-US');
const _now=new Date(), _cur=_now.getFullYear()+'-'+String(_now.getMonth()+1).padStart(2,'0');
const _complete=DB.months.filter(m=>m<_cur);
let state={month:(_complete[_complete.length-1]||DB.months[DB.months.length-1]), hall:null};

DB.months.slice().reverse().forEach(m=>{const o=document.createElement('option');o.value=m;o.textContent='2026年 '+monthLabel(m);monSel.appendChild(o);});
monSel.value=state.month;
monSel.addEventListener('change',()=>{state.month=monSel.value;state.hall=null;render();});

function render(){
  const halls=DB[state.month]||[];
  if(!state.hall||!halls.find(h=>h.hall===state.hall)) state.hall=(halls[0]||{}).hall;
  // pills
  hallsEl.innerHTML='';
  halls.forEach(h=>{
    const b=document.createElement('button');b.className='pill';b.textContent=h.name;
    b.setAttribute('aria-pressed',h.hall===state.hall);
    b.onclick=()=>{state.hall=h.hall;render();};
    hallsEl.appendChild(b);
  });
  const H=halls.find(h=>h.hall===state.hall);
  const band=document.getElementById('band');
  if(!H){band.innerHTML='<span class="meta">この月のデータはありません</span>';
    document.getElementById('tblP').innerHTML='';document.getElementById('tblM').innerHTML='';
    document.getElementById('capP').textContent='';document.getElementById('capM').textContent='';
    document.getElementById('foot').innerHTML='';return;}
  const sign=H.total>=0?'pos':'neg';
  band.innerHTML=`<span class="hn">${H.name}</span>
    <div style="display:flex;flex-direction:column;gap:2px">
      <span class="tlabel">月間総差枚</span>
      <span class="total ${sign}">${fmt(H.total)}</span>
    </div>
    <span class="meta">稼働 ${H.ndays}日 ・ ${H.models.length}機種${state.month===_cur?' ・ <b style="color:var(--gold)">集計途中</b>':''}</span>`;
  const pos=H.models.filter(m=>m.sa>0);
  const neg=H.models.filter(m=>m.sa<0).sort((a,b)=>a.sa-b.sa);
  const maxAbs=Math.max(1,...H.models.map(m=>Math.abs(m.sa)));
  document.getElementById('capP').textContent=`${pos.length}機種 ・ 差枚の高い順`;
  document.getElementById('capM').textContent=`${neg.length}機種 ・ マイナスの大きい順`;
  const rowsHtml=(arr,cls)=>arr.map((m,i)=>{
    const w=Math.max(2,Math.round(Math.abs(m.sa)/maxAbs*100));
    const top=i<3?' top':'';
    const bar=`<div class="bar ${cls}" style="width:${w}%"></div>`;
    const cnt=m.days?`<span class="cnt">${m.days}日</span>`:'';
    return `<tr class="${top}"><td class="rk">${i+1}</td>`+
      `<td class="nm">${escapeHtml(m.model)} ${cnt}</td>`+
      (cls==='p'?`<td class="barcell">${bar}</td><td class="val pos tnum">${fmt(m.sa)}</td>`
                :`<td class="val neg tnum">${fmt(m.sa)}</td><td class="barcell">${bar}</td>`)+
      `</tr>`;
  }).join('');
  document.getElementById('tblP').innerHTML=pos.length?rowsHtml(pos,'p'):'<tr><td class="empty">プラス機種なし</td></tr>';
  document.getElementById('tblM').innerHTML=neg.length?rowsHtml(neg,'m'):'<tr><td class="empty">マイナス機種なし</td></tr>';
  document.getElementById('foot').innerHTML=
    `<b>見方</b> ： 各数値はその月の機種別トータル差枚（プラス＝客が勝ち＝店が出した / マイナス＝店の回収）。バーは店内での大きさ比較。<br>`+
    `<b>データ</b> ： みんレポ集計（自動収集）。上野2店は2月〜、門前仲町2店は7月〜。金色●＝各カテゴリTOP3。`;
}
function escapeHtml(s){return s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
render();
</script>
"""
out=HTML.replace("__DATA__",data)
op=os.path.join(BASE,"reports","monthly.html")
open(op,"w",encoding="utf-8").write(out)
print("wrote",op,len(out),"bytes")
