import os
from pathlib import Path
import anthropic
os.environ.setdefault("ANTHROPIC_API_KEY", Path("~/.config/anthropic/key").expanduser().read_text().strip())
client = anthropic.Anthropic(max_retries=6, timeout=900)
MODELS = {"opus": "claude-opus-5-5", "sonnet": "claude-sonnet-5-5", "haiku": "claude-haiku-5-5"}
# $ per 1M tokens: input, output, cache read; cache write = 1.25 x input
PRICE = {"opus": (4.0, 20.0, 0.20), "sonnet": (2.0, 10.0, 0.10), "haiku": (0.10, 0.50, 0.01)}
def cost(model, u):
    i, o, cr = PRICE[model]
    cw = getattr(u, "cache_creation_input_tokens", 0) or 0
    crd = getattr(u, "cache_read_input_tokens", 0) or 0
    return (u.input_tokens * i + cw * i * 1.25 + crd * cr + u.output_tokens * o) / 1e6
