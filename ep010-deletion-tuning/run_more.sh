#!/bin/zsh
cd "$(dirname "$0")"
while pgrep -f run_all.sh > /dev/null; do sleep 10; done
run() { .venv/bin/python dt_lab.py "$@" > /dev/null 2>> errors.log; }
for t in health philosophy; do
  run --task "$t" --methods base,wanda,dt,random
  run --task "$t" --methods fft
done
echo MORE_DONE $(date) >> log_done.txt
