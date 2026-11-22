# sanity: cached generation with cloned layers == uncached generation, at loops 1 and 2
import sys; sys.argv=[sys.argv[0]]
import torch, qwen_loop as Q
from transformers import AutoModelForCausalLM, AutoTokenizer
tok=AutoTokenizer.from_pretrained(Q.MID); m=AutoModelForCausalLM.from_pretrained(Q.MID, dtype=torch.float32).eval(); base=list(m.model.layers)
for k in (1,2):
    Q.set_loops(m, base, k)
    x=tok.apply_chat_template([{"role":"user","content":"What is 23 * 17? Answer with the number only."}], add_generation_prompt=True, return_tensors="pt")
    x = x if torch.is_tensor(x) else x["input_ids"]
    a=m.generate(x,max_new_tokens=8,do_sample=False,use_cache=True); b=m.generate(x,max_new_tokens=8,do_sample=False,use_cache=False)
    print(k, tok.decode(a[0,x.shape[1]:]), '|', tok.decode(b[0,x.shape[1]:]), torch.equal(a,b))
