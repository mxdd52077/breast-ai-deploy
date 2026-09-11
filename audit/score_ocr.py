"""Offline OCR quality scoring. Reads exported predictions; sends no patient data."""
import argparse
import json
import statistics
import unicodedata
from pathlib import Path

def normalize(text):
    return ''.join(unicodedata.normalize('NFKC',text).split())

def distance(a,b):
    # Row-bounded Levenshtein; segment documents into physical pages in the corpus.
    if len(a)<len(b):a,b=b,a
    row=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        nxt=[i]
        for j,y in enumerate(b,1):nxt.append(min(nxt[-1]+1,row[j]+1,row[j-1]+(x!=y)))
        row=nxt
    return row[-1]

def score(corpus,predictions):
    lookup={p['id']:p for p in predictions};rows=[]
    if len(lookup)!=len(predictions):raise ValueError('Duplicate prediction IDs')
    if len({p['id'] for p in corpus})!=len(corpus):raise ValueError('Duplicate corpus IDs')
    for expected in corpus:
        p=lookup.get(expected['id'],{});truth=normalize(expected['text']);actual=normalize(p.get('text',''))
        if len(truth)>15000 or len(actual)>15000:raise ValueError('Split long documents into pages; max 15000 normalized characters per sample')
        keys=expected.get('critical_fields',{})
        # Field agreement uses separately reviewed structured output, not substring presence.
        fields=p.get('critical_fields',{})
        exact=sum(normalize(str(fields.get(k,'')))==normalize(str(v)) for k,v in keys.items())
        rows.append({'id':expected['id'],'category':expected.get('category','unspecified'),'missing':not bool(p),'failed':bool(p.get('error')) or not bool(actual),'reference_chars':len(truth),'edit_distance':distance(truth,actual),'critical_exact':exact,'critical_total':len(keys),'page_count_match':p.get('page_count')==expected.get('page_count',1),'latency_seconds':p.get('latency_seconds'),'cost':p.get('cost')})
    chars=sum(r['reference_chars'] for r in rows);fields=sum(r['critical_total'] for r in rows)
    latencies=sorted(r['latency_seconds'] for r in rows if isinstance(r['latency_seconds'],(int,float)))
    return {'samples':len(rows),'character_error_rate':sum(r['edit_distance'] for r in rows)/chars if chars else None,'critical_field_exact_rate':sum(r['critical_exact'] for r in rows)/fields if fields else None,'failed_samples':sum(r['failed'] for r in rows),'missing_samples':sum(r['missing'] for r in rows),'page_count_mismatches':sum(not r['page_count_match'] for r in rows),'median_latency_seconds':statistics.median(latencies) if latencies else None,'reported_cost_total':sum(r['cost'] for r in rows if isinstance(r['cost'],(int,float))),'rows':rows}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('corpus',type=Path);parser.add_argument('predictions',type=Path);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    result=score(json.loads(a.corpus.read_text(encoding='utf-8')),json.loads(a.predictions.read_text(encoding='utf-8')))
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f"Scored {result['samples']} samples; report saved.")
