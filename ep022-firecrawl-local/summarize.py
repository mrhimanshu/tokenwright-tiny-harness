import json, statistics as st, collections
R=[json.loads(l) for l in open('results.jsonl')]
M=[json.loads(l) for l in open('mem.jsonl')]
Q=[json.loads(l) for l in open('qa_results.jsonl')]
tools=['fc_static','fc_local','fc_cloud','trafilatura','crawl4ai']
out={}
for t in tools:
    m=[x for x in M if x['tool']==t]; r=[x for x in R if x['tool']==t]
    q=[x for x in Q if x['tool']==t]
    rep0=[x for x in q if x['rep']==0]
    d=dict(runs=len(m), idle_mb=[round(x['idle_mb'],1) for x in m], peak_mb=[round(x['peak_mb']) for x in m],
           total_s=[round(x['total_s'],1) for x in m], median_page_s=round(st.median(x['secs'] for x in r),3),
           ok_pages=[sum(1 for x in r if x['round']==k and x['chars']>200) for k in (1,2,3)],
           cloud_pages=sorted({x['id'] for x in r if x.get('source')=='firecrawl-cloud'}),
           warned=sorted({x['id'] for x in r if x.get('warning')}))
    if q:
        corr=[c for x in q for c in x['correct']]
        per_rep=[round(100*sum(c for x in q if x['rep']==k for c in x['correct'])/sum(len(x['correct']) for x in q if x['rep']==k),1) for k in range(3)]
        d.update(qa_n=len(corr), qa_pct=round(100*sum(corr)/len(corr),1), qa_pct_by_rep=per_rep,
                 doc_tokens_total=sum(x['usage']['input']+x['usage']['cache_write']+x['usage']['cache_read'] for x in rep0),
                 wrong_pages=sorted({x['id'] for x in q if not all(x['correct'])}))
    out[t]=d
json.dump(out,open('summary.json','w'),indent=1)
for t,d in out.items(): print(t, json.dumps(d))
