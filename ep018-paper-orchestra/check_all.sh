#!/bin/sh
# run every check on one PaperOrchestra run dir: check_all.sh runs/po_N
d=$1; w=$d/content_refinement_workdir
python3 check_cites.py $w/final_refined_paper.tex $w/references.bib > $d/cites.json
.venv/bin/python -I check_refs.py $w/references.bib $d/refs_check.jsonl
.venv/bin/python -I check_numbers.py $w/final_refined_paper.tex $d/nums_check.jsonl > $d/nums.log 2>&1
.venv/bin/python -I check_rubric.py $w/final_refined_paper.tex $d/rubric.json
