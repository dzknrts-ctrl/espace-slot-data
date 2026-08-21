#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""示唆画像/メール画像をClaudeの画像認識で読み、構造化して hints/<date>_<hall>.json に保存する。
無人のパイプラインから画像内の文字(イベント/全台/末尾/機種/取材/誕生日)を抽出するための工程。

必要: 環境変数 ANTHROPIC_API_KEY、 pip install anthropic
使い方:
  python hints_vision.py --date 2026-08-22 --hall espace_akiba img1.jpg img2.webp
  （画像はローカルパス。URLの場合は事前にダウンロードして渡す）
"""
import argparse, base64, json, os, sys, mimetypes

MODEL = os.environ.get("HINTS_MODEL", "claude-sonnet-5")
PROMPT = (
 "あなたはパチスロ店の示唆画像/メール画像を読むアシスタントです。"
 "画像内の文字を読み取り、以下をJSONだけで返してください（説明文なし）。\n"
 "{\n"
 '  "event": "イベント名(取材名など。無ければ空)",\n'
 '  "torizai": true/false,   // 取材(ライター/メディア来店)が明示されているか\n'
 '  "strength": "strong|normal|weak",  // 煽りの強さ(全台系/取材/設定6確定などはstrong)\n'
 '  "zendai": ["全台系が示唆された機種名"],\n'
 '  "matsubi": ["示唆された末尾(数字)"],\n'
 '  "kishu": ["強調された機種名"],\n'
 '  "tanjoubi": ["誕生日連動のキャラ/作品"],\n'
 '  "raw": "画像から読めた主要な文言(日本語そのまま、120字以内)"\n'
 "}\n"
 "機種名は一般的な呼称で。判断できない項目は空配列/空文字に。"
)

def img_block(path):
    mime = mimetypes.guess_type(path)[0] or ("image/webp" if path.endswith(".webp") else "image/jpeg")
    data = base64.standard_b64encode(open(path,"rb").read()).decode()
    return {"type":"image","source":{"type":"base64","media_type":mime,"data":data}}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--date",required=True); ap.add_argument("--hall",required=True)
    ap.add_argument("images",nargs="+")
    a=ap.parse_args()
    try:
        import anthropic
    except ImportError:
        sys.exit("pip install anthropic が必要です")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("環境変数 ANTHROPIC_API_KEY を設定してください")
    client=anthropic.Anthropic()
    content=[img_block(p) for p in a.images if os.path.exists(p)]
    if not content: sys.exit("有効な画像がありません")
    content.append({"type":"text","text":PROMPT})
    msg=client.messages.create(model=MODEL,max_tokens=700,
        messages=[{"role":"user","content":content}])
    text="".join(b.text for b in msg.content if b.type=="text").strip()
    # ```json フェンス除去
    if text.startswith("```"): text=text.strip("`"); text=text[text.find("{"):text.rfind("}")+1]
    try: data=json.loads(text)
    except Exception: data={"raw":text}
    data.update({"date":a.date,"hall":a.hall,"source":"vision:"+MODEL})
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)),"hints"),exist_ok=True)
    out=os.path.join(os.path.dirname(os.path.abspath(__file__)),"hints",f"{a.date}_{a.hall}.json")
    json.dump(data,open(out,"w",encoding="utf-8"),ensure_ascii=False,indent=1)
    print("wrote",out); print(json.dumps(data,ensure_ascii=False))

if __name__=="__main__":
    main()
