import json, statistics as st
R=[json.loads(l) for l in open('results/race.jsonl')]
med=st.median
out={}
cells=sorted({(r['test'],r['threads']) for r in R})
for test,t in cells:
    c=[r for r in R if r['test']==test and r['threads']==t]
    arms=sorted({r['arm'] for r in c})
    row={}
    for a in arms:
        x=[r for r in c if r['arm']==a]
        row[a]=dict(n=len(x),decode_med=round(med([r['decode_tps'] for r in x]),1),decode_min=round(min(r['decode_tps'] for r in x),1),decode_max=round(max(r['decode_tps'] for r in x),1),
                    prefill_med=round(med([r['prefill_tps'] for r in x]),1),prefill_ms_med=round(med([r['prefill_ms'] for r in x])),decode_ms_med=round(med([r['decode_ms'] for r in x])),
                    total_ms_med=round(med([r['prefill_ms']+r['decode_ms'] for r in x])),steal_med=round(med([r['steal_pct'] for r in x]),2))
    rounds=sorted({r['round'] for r in c})
    def ratio(a,b,k):
        v=[]
        for rd in rounds:
            xa=[r for r in c if r['round']==rd and r['arm']==a]; xb=[r for r in c if r['round']==rd and r['arm']==b]
            if xa and xb: v.append(xa[0][k]/xb[0][k])
        return dict(median=round(med(v),3),min=round(min(v),3),max=round(max(v),3),wins=sum(1 for q in v if q>1),n=len(v))
    row['paired']={f'asm_q8/{b} decode':ratio('asm_q8',b,'decode_tps') for b in ['llama_native','llama_avx2']}
    row['paired'].update({f'asm_q8/{b} prefill':ratio('asm_q8',b,'prefill_tps') for b in ['llama_native','llama_avx2']})
    row['paired']['llama_native/llama_avx2 decode']=ratio('llama_native','llama_avx2','decode_tps')
    if 'asm_fp32act' in arms: row['paired']['asm_fp32act/llama_native decode']=ratio('asm_fp32act','llama_native','decode_tps'); row['paired']['asm_q8/asm_fp32act decode']=ratio('asm_q8','asm_fp32act','decode_tps')
    out[f'{test}_t{t}']=row
# break-even prompt length at 4 threads, 64 output tokens (asm prefill from long test, decode from short)
s=out['short_t4']; L=out['long_t4']
pa=L['asm_q8']['prefill_med']; pl=L['llama_native']['prefill_med']; da=s['asm_q8']['decode_med']; dl=s['llama_native']['decode_med']
for N in (64,256,1000):
    be=(N/dl-N/da)/(1/pa-1/pl)
    out.setdefault('break_even_prompt_tokens',{})[f'out_{N}']=round(be)
out['break_even_inputs']=dict(asm_prefill=pa,llama_prefill=pl,asm_decode=da,llama_decode=dl)
json.dump(out,open('summary.json','w'),indent=1)
for k,v in out.items():
    print('==',k)
    if isinstance(v,dict):
        for a,b in v.items(): print('  ',a,b)
