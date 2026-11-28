import json, re, collections, sys
def load(c): return [json.loads(l) for l in open(f'data/{c}/test/test_samples.jsonl')]
def balacc(rows, pred):
    tp=collections.Counter(); n=collections.Counter()
    for r in rows:
        y=r['decision']; n[y]+=1; tp[y]+= (pred(r)==y)
    return 50*(tp['SPEAK']/n['SPEAK']+tp['SILENT']/n['SILENT'])
def name_in_current(r):
    t=r['current_turn']['text'].lower()
    return 'SPEAK' if re.search(r'\b'+re.escape(r['target_speaker'].lower())+r'\b', t) else 'SILENT'
def spoke_before(r):
    # target was the speaker right before the current turn
    ct=r['context_turns']
    return 'SPEAK' if ct and ct[-1]['speaker']==r['target_speaker'] else 'SILENT'
def two_party(r):
    return 'SPEAK' if len(r['all_speakers'])==2 else 'SILENT'
def question(r):
    return 'SPEAK' if '?' in r['current_turn']['text'] else 'SILENT'
def combo(r):
    return 'SPEAK' if name_in_current(r)=='SPEAK' or spoke_before(r)=='SPEAK' else 'SILENT'
for c in ['ami','friends','spgi']:
    rows=load(c)
    cat=collections.Counter(r['category'] for r in rows)
    nsp=collections.Counter(len(r['all_speakers']) for r in rows)
    print(c, len(rows), dict(cat), 'speakers', dict(nsp), 'ctx', sum(r['num_context_turns'] for r in rows)/len(rows))
    for f in [name_in_current, spoke_before, two_party, question, combo]:
        print(f'   {f.__name__:16s} {balacc(rows,f):.2f}')
