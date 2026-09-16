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

def test_kimi_retries_transient_connect_failures(monkeypatch):
    monkeypatch.setenv('APEX_LLM_API_KEY','fake-only')
    monkeypatch.setenv('APEX_LLM_BASE_URL','https://api.moonshot.cn/v1')
    request=httpx.Request('POST','https://api.moonshot.cn/v1/chat/completions')

    class FlakyClient:
        attempts=0
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def post(self,*args,**kwargs):
            self.attempts+=1
            if self.attempts<3:
                raise httpx.ConnectTimeout('temporary timeout',request=request)
            return httpx.Response(200,request=request,json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'answer':'已恢复','status':'supported','citations':['source-1']})}}]})

    client=FlakyClient()
    with patch('app.backend.providers.httpx.Client',return_value=client):
        answer=chat_json('system','fictional',Answer)
    assert client.attempts==3
    assert answer.answer=='已恢复'

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

def test_report_request_uses_fixed_sections_and_more_verified_sources(monkeypatch):
    from app.backend.main import knowledge
    monkeypatch.setenv('APEX_LLM_API_KEY','fake-only')
    captured={}
    limits=[]
    def retrieve(q,library,limit):
        limits.append(limit)
        return library[:1]
    def generate(system,content,schema):
        captured.update({'system':system,'content':json.loads(content),'schema':schema.__name__})
        if schema.__name__=='CareReport':
            return schema.model_validate({
                'summary':['已确认资料1份'],
                'key_findings':['资料记录一项关键发现'],
                'treatment_medication':[],
                'schedule':[],
                'pending_items':['下一步时间仍需确认'],
                'visit_preparation':[],
                'safety_note':'涉及治疗与用药请咨询治疗团队。',
                'citations':[knowledge()[0].id],
            })
        return Answer(answer='普通回答',status='supported',citations=[knowledge()[0].id])
    answer,_=run_conversation('请根据已确认资料生成一份规范照护报告',[],knowledge(),retrieve,generate)
    assert limits==[8]
    assert captured['schema']=='CareReport'
    assert all(title in captured['system'] for title in ['资料概况','关键发现','治疗与用药','时间安排','待确认事项','就诊准备'])
    assert all(title in answer.answer for title in ['一、资料概况','二、关键发现','三、治疗与用药','四、时间安排','五、待确认事项','六、就诊准备','重要说明'])
    assert '未在已确认资料中找到' in answer.answer
