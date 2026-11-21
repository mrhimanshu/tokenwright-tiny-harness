# Pretrained small LM as a compressor: ideal arithmetic-code length = sum of -log2 p(token) over the slice.
# Sliding windows of 1024 tokens, stride 512 (every scored token sees >= 512 tokens of context).
import sys, time, math, json, torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from common import OFFSETS, read_slice, log
torch.set_num_threads(4)
models = json.load(open("models.json"))
N = int(sys.argv[1]) if len(sys.argv) > 1 else 65536
for repo in sys.argv[2:] or list(models):
    p = models[repo]["path"]
    tok = AutoTokenizer.from_pretrained(p); m = AutoModelForCausalLM.from_pretrained(p, torch_dtype=torch.float32).eval()
    params = sum(x.numel() for x in m.parameters())
    for off in OFFSETS:
        b = read_slice(off, N); text = b.decode("utf-8")
        ids = tok(text, add_special_tokens=False)["input_ids"]
        rt = tok.decode(ids) == text
        bos = tok.bos_token_id if tok.bos_token_id is not None else tok.eos_token_id
        ids = torch.tensor([bos] + ids)
        W, S = 1024, 512; bits = 0.0; scored = 1; t0 = time.time()
        with torch.no_grad():
            start = 0
            while scored < len(ids):
                end = min(start + W, len(ids)); x = ids[start:end].unsqueeze(0)
                lp = torch.log_softmax(m(x).logits[0].float(), -1)
                first = scored - start  # positions in window to score: predict token at idx>=scored
                tgt = ids[start + first:end]
                bits += -lp[first - 1:end - start - 1].gather(1, tgt.unsqueeze(1)).sum().item() / math.log(2)
                scored = end; start = end - S if end < len(ids) else end
        dt = time.time() - t0
        rec = dict(method="pretrained_llm", model=repo, params=params, offset=off, bytes=len(b), tokens=len(ids) - 1,
                   bits=bits, bpb=bits / len(b), seconds=dt, bytes_per_s=len(b) / dt, roundtrip_text=rt,
                   weights_bytes_bf16=params * 2)
        log("results.jsonl", rec); print(json.dumps(rec), flush=True)
