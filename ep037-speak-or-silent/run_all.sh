#!/bin/sh
cd "$(dirname "$0")"
P=/data/projects/Tokenwright/.venv/bin/python
for r in 1 2 3; do $P run.py claude-haiku-5-5 paper $r; $P run.py claude-haiku-5-5 predict $r; done
$P run.py claude-sonnet-5-5 paper 1
$P run.py claude-sonnet-5-5 predict 1
$P run.py claude-opus-5-5 paper 1
$P run.py claude-opus-5-5 predict 1
echo ALLDONE
