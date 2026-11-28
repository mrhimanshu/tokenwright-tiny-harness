import json, collections
res={}
for c in ['friends','ami']:
    tr=[json.loads(l) for l in open(f'data/{c}/train/train_samples.jsonl')]
    te=[json.loads(l) for l in open(f'data/{c}/test/test_samples.jsonl')]
    seqs=set(r['sequence_id'] for r in tr)
    def mom(r): return (r['sequence_id'], r['turn_index'])
    moments=collections.defaultdict(list)
    for r in tr: moments[mom(r)].append(r)
    def txt(r): return (tuple((t['speaker'],t['text']) for t in r['context_turns']), r['current_turn']['speaker'], r['current_turn']['text'])
    texts=collections.defaultdict(list)
    for r in tr: texts[txt(r)].append(r)
    same_seq=sum(r['sequence_id'] in seqs for r in te)
    same_moment=sum(mom(r) in moments for r in te)
    same_text=sum(txt(r) in texts for r in te)
    # same text AND same target in train
    same_text_target=sum(any(x['target_speaker']==r['target_speaker'] for x in texts.get(txt(r),[])) for r in te)
    # same moment different target: label of other speaker leaks the answer? if another target in train is SPEAK at the same moment, then this target must be SILENT
    leak_answer=0; tot_mom=0
    for r in te:
        others=moments.get(mom(r),[])+texts.get(txt(r),[])
        if others:
            tot_mom+=1
            if any(o['decision']=='SPEAK' and o['target_speaker']!=r['target_speaker'] for o in others) and r['decision']=='SILENT': leak_answer+=1
    seqid_prefix=collections.Counter(r['sequence_id'].split('_')[0] for r in te)
    res[c]=dict(test=len(te), same_sequence_in_train=same_seq, same_moment_in_train=same_moment, identical_text_in_train=same_text,
                identical_text_same_target_in_train=same_text_target, test_ids_prefix=dict(seqid_prefix), silent_answer_implied=leak_answer, with_sibling=tot_mom)
    print(c, res[c])
json.dump(res, open('leak.json','w'), indent=1)

# label agreement on exact duplicates (same text + same target) between train and test, and inside test itself
for c in ['friends','ami']:
    tr=[json.loads(l) for l in open(f'data/{c}/train/train_samples.jsonl')]
    te=[json.loads(l) for l in open(f'data/{c}/test/test_samples.jsonl')]
    def k(r): return (tuple((t['speaker'],t['text']) for t in r['context_turns']), r['current_turn']['speaker'], r['current_turn']['text'], r['target_speaker'])
    def k3(r): return (tuple((t['speaker'],t['text']) for t in r['context_turns'][-3:]), r['current_turn']['speaker'], r['current_turn']['text'], r['target_speaker'])
    for name,f in [('full',k),('last3ctx',k3)]:
        d=collections.defaultdict(set)
        for r in tr: d[f(r)].add(r['decision'])
        hit=[r for r in te if f(r) in d]
        agree=sum(d[f(r)]=={r['decision']} for r in hit); conflict=sum(len(d[f(r)])>1 or r['decision'] not in d[f(r)] for r in hit)
        print(c, name, 'test items with a train twin', len(hit), 'same label', agree, 'conflict', conflict)
        res[c][f'twin_{name}']=dict(n=len(hit), same_label=agree, conflict=conflict)
json.dump(res, open('leak.json','w'), indent=1)
