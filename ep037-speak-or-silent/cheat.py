"""No-AI baselines on the full official test sets.
rule  = SPEAK if the target's name is in the most recent line.
lookup = if the same conversation moment (same context + line + target) is in the TRAIN split, copy its label; else rule.
lookup3 = same, matching only the last 3 context turns."""
import json, re, collections
def bal(rows):
    n=collections.Counter(); ok=collections.Counter()
    for y,p in rows: n[y]+=1; ok[y]+=(y==p)
    return round(50*(ok['SPEAK']/n['SPEAK']+ok['SILENT']/n['SILENT']),2)
def name(r):
    return 'SPEAK' if re.search(r'\b'+re.escape(r['target_speaker'].lower())+r'\b', r['current_turn']['text'].lower()) else 'SILENT'
def prev(r):
    ct=r['context_turns']; return 'SPEAK' if ct and ct[-1]['speaker']==r['target_speaker'] else 'SILENT'
out={}
for c,rule in [('friends',name),('ami',prev)]:
    tr=[json.loads(l) for l in open(f'data/{c}/train/train_samples.jsonl')]
    te=[json.loads(l) for l in open(f'data/{c}/test/test_samples.jsonl')]
    def k(r,n=None):
        ctx=r['context_turns'] if n is None else r['context_turns'][-n:]
        return (tuple((t['speaker'],t['text']) for t in ctx), r['current_turn']['speaker'], r['current_turn']['text'], r['target_speaker'])
    res={}
    for nm,n in [('lookup_full',None),('lookup_last3',3),('lookup_last1',1),('lookup_line_only',0)]:
        d=collections.defaultdict(collections.Counter)
        for r in tr: d[k(r,n)][r['decision']]+=1
        rows=[]; hits=0
        for r in te:
            if k(r,n) in d: hits+=1; p=d[k(r,n)].most_common(1)[0][0]
            else: p=rule(r)
            rows.append((r['decision'],p))
        res[nm]=dict(balacc=bal(rows), hits=hits)
    res['rule_only']=dict(balacc=bal([(r['decision'],rule(r)) for r in te]), rule=rule.__name__)
    out[c]=res; print(c, res)
json.dump(out, open('cheat.json','w'), indent=1)
