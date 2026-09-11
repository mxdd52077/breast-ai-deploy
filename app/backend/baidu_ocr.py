"""Baidu-hosted PaddleOCR-VL document parser. Credentials never enter logs or responses."""
import base64
import hashlib
import os
import time
from io import BytesIO
from threading import Lock
from urllib.parse import urlsplit

import httpx
from PIL import Image
from pypdf import PdfReader

_lock=Lock()
_cached={"fingerprint":"","token":"","expires":0.0}

class BaiduError(ValueError):
    pass

def configured():
    return bool(os.getenv('BAIDU_OCR_API_KEY') and os.getenv('BAIDU_OCR_SECRET_KEY'))

def access_token(client,force=False):
    key=os.getenv('BAIDU_OCR_API_KEY','');secret=os.getenv('BAIDU_OCR_SECRET_KEY','')
    if not key or not secret:raise BaiduError('百度图片识别服务尚未配置，资料已保留。')
    fingerprint=hashlib.sha256((key+':'+secret).encode()).hexdigest()
    with _lock:
        if not force and _cached['fingerprint']==fingerprint and _cached['expires']>time.time():return _cached['token']
        response=client.post('https://aip.baidubce.com/oauth/2.0/token',data={'grant_type':'client_credentials','client_id':key,'client_secret':secret})
        response.raise_for_status();data=response.json()
        token=data.get('access_token')
        if not token:raise BaiduError('百度OCR授权失败，请管理员检查应用密钥。')
        _cached.update(fingerprint=fingerprint,token=token,expires=time.time()+max(0,int(data.get('expires_in',0))-300))
        return token

def _request(client,route,payload,token):
    response=client.post('https://aip.baidubce.com/rest/2.0/brain/online/v2/paddle-vl-parser/'+route,params={'access_token':token},data=payload)
    response.raise_for_status();data=response.json()
    code=int(data.get('error_code',0))
    if code in {110,111}:
        token=access_token(client,force=True)
        response=client.post('https://aip.baidubce.com/rest/2.0/brain/online/v2/paddle-vl-parser/'+route,params={'access_token':token},data=payload)
        response.raise_for_status();data=response.json();code=int(data.get('error_code',0))
    if code:
        if code in {6,17,18,19}:raise BaiduError('PaddleOCR-VL权限、额度或并发受限，请管理员检查该接口开通情况。')
        raise BaiduError(f'PaddleOCR-VL请求未完成（错误码{code}），文件已保留。')
    if not isinstance(data.get('result'),dict):raise BaiduError('PaddleOCR-VL结果格式异常。')
    return data['result']

def decode_pages(result,expected_count):
    rows=result.get('pages')
    if not isinstance(rows,list) or len(rows)!=expected_count:raise BaiduError('PaddleOCR-VL返回页数与原文件不一致。')
    ordered=sorted(rows,key=lambda p:p.get('page_num',-1))
    if [p.get('page_num') for p in ordered]!=list(range(expected_count)):raise BaiduError('PaddleOCR-VL页码缺失或重复，本次结果未采用。')
    pages=[]
    for index,page in enumerate(ordered,1):
        text=page.get('text','')
        if not isinstance(text,str):raise BaiduError('PaddleOCR-VL文字格式异常。')
        # Preserve table markdown as a separately labeled source section when absent from text.
        tables=[t['markdown'] for t in page.get('tables',[]) if isinstance(t.get('markdown'),str) and t['markdown'] not in text]
        if tables:text+='\n\n表格识别：\n'+'\n\n'.join(tables)
        blocks=[{'text':l.get('text',''),'box':l.get('position'),'type':l.get('type')} for l in page.get('layouts',[])]
        pages.append({'page':index,'text':text,'location':f'第{index}页 · PaddleOCR-VL','ocr':True,'blocks':blocks})
    if not any(p['text'].strip() for p in pages):raise BaiduError('PaddleOCR-VL未识别到文字，请检查图片清晰度。')
    return pages

def recognize(path):
    raw=path.read_bytes();suffix=path.suffix.lower()
    if suffix=='.pdf':
        reader=PdfReader(BytesIO(raw))
        if reader.is_encrypted:raise BaiduError('请移除PDF密码后重新上传。')
        count=len(reader.pages)
    else:
        with Image.open(BytesIO(raw)) as img:
            if max(img.size)>8192:raise BaiduError('PaddleOCR-VL图片长边不能超过8192像素。')
            if img.format=='WEBP':
                output=BytesIO();img.convert('RGB').save(output,format='PNG');raw=output.getvalue();suffix='.png'
        count=1
    if not 1<=count<=40:raise BaiduError('每份资料最多支持40页，请拆分文件。')
    if len(raw)>10*1024*1024:raise BaiduError('单份文件不能超过10MB。')
    try:
        with httpx.Client(timeout=httpx.Timeout(45,connect=10),follow_redirects=False) as client:
            token=access_token(client)
            result=_request(client,'task',{'file_data':base64.b64encode(raw).decode(),'file_name':'document'+suffix},token)
            task_id=result.get('task_id')
            if not isinstance(task_id,str):raise BaiduError('PaddleOCR-VL未返回任务编号。')
            deadline=time.monotonic()+300
            while time.monotonic()<deadline:
                time.sleep(5)
                result=_request(client,'task/query',{'task_id':task_id},token)
                status=result.get('status')
                if status=='failed':raise BaiduError('PaddleOCR-VL解析失败，请检查接口额度或文件格式后重试。')
                if status=='success':break
                if status not in {'pending','processing'}:raise BaiduError('PaddleOCR-VL返回未知任务状态。')
            else:raise BaiduError('PaddleOCR-VL处理超时，文件已保留，请稍后重试。')
            url=result.get('parse_result_url','');parsed=urlsplit(url)
            if parsed.scheme!='https' or parsed.username or parsed.password or parsed.port not in {None,443} or not (parsed.hostname or '').endswith('.bcebos.com'):
                raise BaiduError('PaddleOCR-VL结果地址不在允许的百度对象存储域名范围。')
            # Result URL is a provider-issued capability; never log or persist it.
            with client.stream('GET',url) as response:
                response.raise_for_status();chunks=[];size=0
                for chunk in response.iter_bytes():
                    size+=len(chunk)
                    if size>20*1024*1024:raise BaiduError('识别结果过大，请拆分文件后重试。')
                    chunks.append(chunk)
            import json
            return decode_pages(json.loads(b''.join(chunks)),count)
    except BaiduError:raise
    except (httpx.HTTPError,ValueError,KeyError,TypeError):raise BaiduError('PaddleOCR-VL请求暂未完成，文件已保留，请稍后重试。') from None
