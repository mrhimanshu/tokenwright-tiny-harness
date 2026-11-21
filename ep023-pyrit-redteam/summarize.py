import json, sys, collections
rows=[json.loads(l) for f in sys.argv[1:] for l in open(f)]
C=collections.defaultdict(lambda: collections.Counter())
for r in rows:
    k=(r.get('attacker','claude-haiku-5-5').split('-')[0], r['target'], r['attack'])
    c=C[k]; c['n']+=1
    if 'error' in r: c['crash']+=1; continue
    c['pyrit_success']+= r['pyrit_outcome']=='success'
    c['leaked']+= r['leaked']
    c['FP']+= r['pyrit_outcome']=='success' and not r['leaked']
    c['FN']+= r['pyrit_outcome']!='success' and r['leaked']
    c['refusal_turns']+= r.get('attacker_refusals',0); c['turns']+=r.get('turns') or 0
    c['all_refused']+= bool(r.get('prompts')) and r.get('attacker_refusals',0)==len(r['prompts'])
for k in sorted(C): print(k, dict(C[k]))
