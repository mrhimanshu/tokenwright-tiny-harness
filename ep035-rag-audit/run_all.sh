#!/bin/bash
cd "$(dirname "$0")"
P=.venv/bin/python
for r in 0 1 2; do for c in k50 k20 k5 gold; do $P run_qa.py claude-haiku-5-5 $c $r; done; done
$P run_qa.py claude-haiku-5-5 k50cot 0
$P run_qa.py claude-sonnet-5-5 k50 0 80
$P run_qa.py claude-sonnet-5-5 gold 0 80
echo ALLDONE
