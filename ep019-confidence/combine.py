"""EP019: combine scored.jsonl + scored_hard.jsonl into combined.json (headline numbers, cost at list prices)."""
import collections
import json
P = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2, 10), "claude-opus-5-5": (4, 20)}
rows = [json.loads(l) for t in ['', '_hard'] for l in open(f'scored{t}.jsonl')]
g = collections.defaultdict(list)
for r in rows:
    g[(r['model'], r['doc_id'], r['qid'])].append(r['answer'])
out = {}
for m in P:
    R = [r for r in rows if r['model'] == m]
    c = [r for r in R if r['correct']]; w = [r for r in R if not r['correct']]; ab = [r for r in R if r['absent']]
    d = {'answers': len(R), 'correct': len(c), 'wrong': len(w), 'acc': round(100 * len(c) / len(R), 2),
         'max_conf_wrong': max(r['conf'] for r in w) if w else None, 'wrong_ge90': sum(r['conf'] >= 90 for r in w),
         'absent': len(ab), 'made_up': sum(r['answer'] is not None for r in ab), 'mean_conf': round(sum(r['conf'] for r in R) / len(R), 1),
         'correct_below90': sum(r['conf'] < 90 for r in c), 'pct_correct_below90': round(100 * sum(r['conf'] < 90 for r in c) / len(c), 1),
         'wrong_same_all_3_runs': sum(len(set(g[(m, r['doc_id'], r['qid'])])) == 1 for r in w)}
    for th in (90, 86, 80, 70):
        A = [r for r in R if r['conf'] >= th]; d[f'auto{th}'] = round(100 * len(A) / len(R), 1); d[f'err{th}'] = sum(not r['correct'] for r in A)
    tok = [0, 0]
    for t in ['', '_hard']:
        for l in open(f'results{t}.jsonl'):
            x = json.loads(l)
            if x['model'] == m and x.get('parsed') is not None:
                tok[0] += x['in_tok']; tok[1] += x['out_tok']
    d['cost_usd'] = round(tok[0] / 1e6 * P[m][0] + tok[1] / 1e6 * P[m][1], 3); d['cost_per_invoice'] = round(d['cost_usd'] / 210, 5)
    d['in_tok_per_invoice'] = round(tok[0] / 210)
    out[m] = d
json.dump(out, open('combined.json', 'w'), indent=1)
for m, d in out.items():
    print(m, d)
print('total cost', round(sum(d['cost_usd'] for d in out.values()), 2), 'answers', sum(d['answers'] for d in out.values()))
