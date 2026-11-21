#!/bin/sh
# Classic compressors on the full 1 GB enwik9 (one run each; deterministic sizes). Writes classic_full.jsonl
D=../data/enwik9
run() { name=$1; shift; s=$(date +%s.%N); sz=$("$@" < $D | wc -c); e=$(date +%s.%N);
  echo "{\"tool\":\"$name\",\"file\":\"enwik9\",\"bytes_in\":1000000000,\"bytes_out\":$sz,\"seconds\":$(echo "$e - $s" | bc)}" >> classic_full.jsonl; }
run "gzip -9" gzip -9 -c &
run "bzip2 -9" bzip2 -9 -c &
run "xz -9" xz -9 -T1 -c &
wait
echo FULLDONE
