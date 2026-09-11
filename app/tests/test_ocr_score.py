from audit.score_ocr import score

def test_ocr_score_penalizes_wrong_critical_field_and_missing_page():
    truth=[{'id':'one','text':'复诊2030年9月10日','page_count':1,'critical_fields':{'date':'2030-09-10'}},{'id':'two','text':'第二页','page_count':1}]
    result=score(truth,[{'id':'one','text':'复诊2030年9月10日','page_count':1,'critical_fields':{'date':'2030-09-11'}}])
    assert result['critical_field_exact_rate']==0
    assert result['missing_samples']==1
    assert result['page_count_mismatches']==1
    assert result['character_error_rate']>0
