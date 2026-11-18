#!/bin/sh
# EP017 lab step 3: run the real UnvibeCode 0.4.0 hosted review on lab/shopfast, 3 times, one after another.
cd "$(dirname "$0")"
for i in 1 2 3; do
  echo "=== run $i start $(date -u +%FT%TZ)"
  s=$(date +%s)
  /tmp/unv_venv_dir/venv/bin/python -I -m unvibecode review --repository shopfast --output unvibe_run$i --no-open-browser > unvibe_run$i.log 2>&1
  echo "=== run $i exit $? secs $(( $(date +%s) - s )) end $(date -u +%FT%TZ)"
done
