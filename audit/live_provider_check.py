"""Explicit live smoke test with generated fictional data only; no secrets in output."""
import json
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
load_dotenv(ROOT/'app/.env',override=False)
os.environ['APEX_WORKER']='false'
OUT=ROOT/'deliverables/verification'

def run_ocr():
    from PIL import Image,ImageDraw,ImageFont
    from app.backend.providers import parse_pages,ServiceError
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',32)
    image=Image.new('RGB',(1100,500),'white');draw=ImageDraw.Draw(image)
    draw.text((40,40),'APEX 虚构测试资料，不是真实患者',font=font,fill='black')
    draw.text((40,130),'复诊安排：2030年9月10日09:00复诊。',font=font,fill='black')
    draw.text((40,220),'请携带既往检查报告。',font=font,fill='black')
    path=OUT/'fictional-ocr-smoke.png';image.save(path)
    started=time.monotonic()
    try:
        pages=parse_pages(path,'.png');text='\n'.join(p['text'] for p in pages)
        result={'service':'baidu-hosted-paddleocr-vl','success':True,'pages':len(pages),'date_present':'2030' in text and '9月10日' in text,'time_present':'09:00' in text,'elapsed_seconds':round(time.monotonic()-started,2),'data':'generated fictional PNG only'}
    except ServiceError as e:result={'service':'baidu-hosted-paddleocr-vl','success':False,'error':str(e),'elapsed_seconds':round(time.monotonic()-started,2)}
    (OUT/'live-ocr.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=True))

def run_kimi():
    from app.backend.main import knowledge,retrieve_chunks
    from app.backend.providers import chat_json,ServiceError
    from app.backend.conversation import run_conversation
    started=time.monotonic()
    try:
        answer,chunks=run_conversation('复诊前可以准备哪些问题？',[],knowledge(),retrieve_chunks,chat_json)
        result={'service':'kimi-k3-langgraph','success':True,'status':answer.status,'citations':answer.citations,'answer_characters':len(answer.answer),'elapsed_seconds':round(time.monotonic()-started,2),'data':'generic health education question and bundled public excerpts only'}
    except ServiceError as e:result={'service':'kimi-k3-langgraph','success':False,'error':str(e),'elapsed_seconds':round(time.monotonic()-started,2)}
    (OUT/'live-kimi.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=True))

if __name__=='__main__':
    {'ocr':run_ocr,'kimi':run_kimi}[sys.argv[1]]()
