#!/bin/zsh
cd "$(dirname "$0")"
run() { .venv/bin/python dt_lab.py "$@" > /dev/null 2>> errors.log; }
run --task biology --methods fft
for t in psychology economics; do
  run --task "$t" --methods base,wanda,dt,random
  run --task "$t" --methods fft
done
echo ALL_DONE $(date) >> log_done.txt
