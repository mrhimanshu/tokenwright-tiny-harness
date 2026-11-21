# A REAL LLM compressor: SmolLM2-135M + range coding (constriction). Encode a Wikipedia piece to bytes,
# decode it back from those bytes alone (plus the model), check it is byte-identical. Encoder and decoder run the
# same one-token-at-a-time path so their probabilities match exactly.
import sys, time, json, struct, hashlib, numpy as np, torch, constriction
from transformers import AutoTokenizer, AutoModelForCausalLM
from common import read_slice, log
torch.set_num_threads(4)
P = json.load(open("models.json"))["HuggingFaceTB/SmolLM2-135M"]["path"]
tok = AutoTokenizer.from_pretrained(P); m = AutoModelForCausalLM.from_pretrained(P, dtype=torch.float32).eval()
MODEL = constriction.stream.model.Categorical(perfect=False)
def stepper():
    past = None
    def step(t):
        nonlocal past
        with torch.no_grad():
            o = m(torch.tensor([[t]]), past_key_values=past, use_cache=True)
        past = o.past_key_values
        return torch.softmax(o.logits[0, -1].double(), -1).numpy()
    return step
N = int(sys.argv[1]) if len(sys.argv) > 1 else 4096; OFF = 10_000_000
src = read_slice(OFF, N); ids = tok(src.decode(), add_special_tokens=False)["input_ids"]
# encode
t0 = time.time(); step = stepper(); p = step(tok.eos_token_id); enc = constriction.stream.queue.RangeEncoder()
for t in ids:
    enc.encode(np.array([t], dtype=np.int32), MODEL, p[None, :]); p = step(t)
words = enc.get_compressed(); blob = struct.pack("<I", len(ids)) + words.tobytes(); t_enc = time.time() - t0
open("roundtrip.bin", "wb").write(blob)
# decode from the file only
t0 = time.time(); blob2 = open("roundtrip.bin", "rb").read(); n = struct.unpack("<I", blob2[:4])[0]
dec = constriction.stream.queue.RangeDecoder(np.frombuffer(blob2[4:], dtype=np.uint32).copy())
step = stepper(); p = step(tok.eos_token_id); out = []
for _ in range(n):
    t = int(dec.decode(MODEL, p[None, :])[0]); out.append(t); p = step(t)
back = tok.decode(out).encode(); t_dec = time.time() - t0
rec = dict(method="roundtrip_llm", model="HuggingFaceTB/SmolLM2-135M", offset=OFF, bytes=len(src), tokens=len(ids),
           bytes_out=len(blob), bpb=8 * len(blob) / len(src), identical=back == src,
           sha_in=hashlib.sha256(src).hexdigest(), sha_out=hashlib.sha256(back).hexdigest(),
           enc_seconds=t_enc, dec_seconds=t_dec, enc_bytes_per_s=len(src) / t_enc, dec_bytes_per_s=len(src) / t_dec)
log("results.jsonl", rec); print(json.dumps(rec))
