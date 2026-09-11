"""Local readiness inspection. Prints no credentials; makes no network request."""
import importlib.util
import json
import os
from pathlib import Path
from dotenv import load_dotenv

def configuration():
    load_dotenv(Path(__file__).resolve().parents[1]/'.env',override=False)
    provider=os.getenv('APEX_OCR_PROVIDER','paddle')
    return {
        'ocr_provider':provider,
        'ocr_credentials_configured':bool(os.getenv('BAIDU_OCR_API_KEY') and os.getenv('BAIDU_OCR_SECRET_KEY')) if provider=='baidu_paddle' else bool(os.getenv('PADDLEOCR_ACCESS_TOKEN')),
        'ocr_sdk_installed':importlib.util.find_spec('paddleocr') is not None,
        'model_key_configured':bool(os.getenv('APEX_LLM_API_KEY')),
        'langgraph_installed':importlib.util.find_spec('langgraph') is not None,
        'real_uploads_enabled':os.getenv('APEX_ALLOW_REAL_UPLOADS')=='true',
        'secure_cookies_enabled':os.getenv('APEX_SECURE_COOKIES')=='true',
        'database_configured':bool(os.getenv('DATABASE_URL')),
        'supabase_storage_configured':bool(os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_SERVICE_ROLE_KEY')),
        'network_checked_by_this_command':False,
        'notice':'此检查只确认本机配置存在，不验证线上授权、OCR质量或供应商数据处理边界。',
    }

if __name__=='__main__':
    print(json.dumps(configuration(),ensure_ascii=True,indent=2))
