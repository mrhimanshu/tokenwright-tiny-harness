"""Score watched words vs a null set of random everyday words, from the topk/ dumps (band layers 9-22, top-50 per position).
For each email group and condition: does the word appear in the lens top-k at ANY band layer at ANY token of that group?
Writes null_summary.json and prints tables."""
import json
import os
import sys

import torch
import transformers

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
tok = transformers.AutoTokenizer.from_pretrained("Qwen/Qwen3-1.7B")

WATCH = {"affair": ["blackmail", "leverage", "secret", "affair"], "wipe": ["shutdown", "threat", "survival", "replace"],
         "eval": ["fake", "fictional", "scenario", "test"]}
NULL = """banana giraffe violin volcano umbrella penguin carrot guitar castle river pencil dolphin pizza mountain bicycle candle
tomato elephant piano island rabbit window garden cookie tiger forest bottle hammer jacket kitten lemon mirror orange pillow rocket
sandwich turtle wallet zebra anchor balloon basket blanket bridge butter camera cherry circus cloud coffee comet desert diamond dragon
eagle feather finger flower football glacier honey insect jungle kettle ladder lizard magnet meadow monkey needle ocean onion oyster
parrot peanut pepper planet potato puzzle pyramid rainbow robot saddle salmon shark shovel silver snail spider spoon squirrel star
statue sugar sunset teapot tent thunder tractor trumpet tulip valley walnut whale wheel wizard yogurt apron barrel beetle cactus
canoe carpet cereal chimney cobra coconut crayon cricket donkey drum falcon fence garlic goose harbor helmet igloo jelly koala
lantern lobster mango marble moose noodle olive owl paddle panda pearl pebble pickle pigeon plum pumpkin quilt radish raven
saxophone scarf seagull skate sled sock spinach sponge squid stove strawberry swan tambourine tiara toast tornado towel trolley
tuba unicorn vase violet waffle walrus wagon whistle willow yacht""".split()


def single(word):
    ids = set()
    for v in [" " + word, word, " " + word.capitalize(), word.capitalize()]:
        e = tok.encode(v, add_special_tokens=False)
        if len(e) == 1:
            ids.add(e[0])
    return ids


null_ids = {w: single(w) for w in NULL}
null_ids = {w: s for w, s in null_ids.items() if s}
watch_ids = {w: single(w) for g in WATCH.values() for w in g}
GROUPS = {"setup": [-1, 0, 1], "affair": [2, 3, 4, 5], "wipe": [6, 7, 8, 9, 10]}


def hits(d, ids_of, group, k):
    """For each word: True if any of its ids is in the top-k at any band layer / any position of the group."""
    m = torch.zeros_like(d["seg_of"], dtype=torch.bool)
    for s in GROUPS[group]:
        m |= d["seg_of"] == s
    top = d["top"][:, m, :k].reshape(-1)
    present = set(top.unique().tolist())
    return {w: bool(ids & present) for w, ids in ids_of.items()}


S = {"n_null": len(null_ids)}
for k in [1, 5, 10]:
    for mode in ["jlens", "logit"]:
        for cond in ["full", "no_affair", "no_wipe"]:
            for vi in range(3):
                d = torch.load(os.path.join(HERE, "topk", f"{vi}_{cond}_{mode}.pt"))
                # top-1 only means index 0 of the top list
                for group in GROUPS:
                    hn = hits(d, null_ids, group, k)
                    hw = hits(d, watch_ids, group, k)
                    key = f"k{k}|{mode}|{cond}|v{vi}|{group}"
                    S[key] = dict(null_rate=round(100 * sum(hn.values()) / len(hn), 1), null_hits=[w for w, v in hn.items() if v], watch=hw)
json.dump(S, open(os.path.join(HERE, "null_summary.json"), "w"), indent=1)

print("null words (single-token):", len(null_ids))
for k in [1, 5, 10]:
    print(f"\n=== top-{k}: % of random words that light up anywhere in the group (mean of 3 variants) | watched words hit in v0,v1,v2")
    for mode in ["jlens", "logit"]:
        for cond in ["full", "no_affair", "no_wipe"]:
            for group in GROUPS:
                rates = [S[f"k{k}|{mode}|{cond}|v{v}|{group}"]["null_rate"] for v in range(3)]
                ws = {w: "".join("x" if S[f"k{k}|{mode}|{cond}|v{v}|{group}"]["watch"][w] else "." for v in range(3)) for w in watch_ids}
                print(f"  {mode:5s} {cond:9s} {group:6s} null {sum(rates) / 3:5.1f}%  " + " ".join(f"{w}:{s}" for w, s in ws.items()))
