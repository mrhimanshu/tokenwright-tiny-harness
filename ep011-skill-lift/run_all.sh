#!/bin/zsh
# Full run: 7 conditions x 6 tasks x 3 reps on Haiku 5.5, 5 conditions on Sonnet 5.5. One process per condition, own output file.
cd "${0:A:h}"
mkdir -p runs
PY=../../.venv/bin/python
for c in none A_plain P_polished C_outdated D_sloppy B_bloated E_vague; do
  OUT=runs/haiku_$c.jsonl $PY run.py claude-haiku-5-5 $c 3 > runs/haiku_$c.log 2>&1 &
done
for c in none P_polished C_outdated E_vague B_bloated; do
  OUT=runs/sonnet_$c.jsonl $PY run.py claude-sonnet-5-5 $c 3 > runs/sonnet_$c.log 2>&1 &
done
wait
cat runs/*.jsonl > results.jsonl
echo DONE $(wc -l < results.jsonl) > runs/done.txt
