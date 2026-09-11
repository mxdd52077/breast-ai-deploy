import json
from unittest.mock import patch
import httpx
import pytest

from app.backend.baidu_ocr import decode_pages,BaiduError
from app.backend.providers import chat_json,ServiceError
from app.backend.contracts import Answer
from app.backend.conversation import run_conversation

def test_paddle_page_numbers_tables_and_missing_page():
    result={'pages':[{'page_num':1,'text':'第二页','tables':[{'markdown':'|日期|2030-09-10|'}]},{'page_num':0,'text':'第一页'}]}
    pages=decode_pages(result,2)
    assert pages[0]['text']=='第一页' and pages[1]['page']==2
    assert '2030-09-10' in pages[1]['text']
    with pytest.raises(BaiduError):decode_pages(result,3)
    result['pages'][0]['page_num']=0
    with pytest.raises(BaiduError):decode_pages(result,2)

def test_kimi_uses_strict_schema_and_no_reasoning_output(monkeypatch):
    monkeypatch.setenv('APEX_LLM_API_KEY','fake-only')
    monkeypatch.setenv('APEX_LLM_BASE_URL','https://api.moonshot.cn/v1')
    monkeypatch.setenv('APEX_LLM_MODEL','kimi-k3')
    seen={}
    def handle(request):
        seen.update(json.loads(request.content))
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'reasoning_content':'never expose reasoning','content':json.dumps({'answer':'可核对答案','status':'supported','citations':['source-1']})}}]})
    client=httpx.Client(transport=httpx.MockTransport(handle))
    with patch('app.backend.providers.httpx.Client',return_value=client):answer=chat_json('system','fictional',Answer)
    assert seen['model']=='kimi-k3' and 'temperature' not in seen
    assert seen['response_format']['json_schema']['strict'] is True
    assert 'never expose' not in answer.answer

def test_graph_followup_context_does_not_leak_between_invocations(monkeypatch):
    from app.backend.main import knowledge
    monkeypatch.setenv('APEX_LLM_API_KEY','fake-only')
    captured=[]
    def retrieve(q,library,limit):return library[:1]
    def generate(system,content,schema):
        captured.append(json.loads(content))
        return Answer(answer='回答',status='supported',citations=[knowledge()[0].id])
    run_conversation('如何记录？',[{'role':'user','text':'疲劳记录'}],knowledge(),retrieve,generate)
    run_conversation('新的问题',[],knowledge(),retrieve,generate)
    assert captured[0]['conversation_context'][0]['text']=='疲劳记录'
    assert captured[1]['conversation_context']==[]

def test_graph_urgent_route_does_not_call_llm():
    def forbidden(*args,**kwargs):raise AssertionError('must not call external service')
    answer,sources=run_conversation('呼吸困难',[],[],forbidden,forbidden)
    assert answer.status=='safety_escalation' and not sources
