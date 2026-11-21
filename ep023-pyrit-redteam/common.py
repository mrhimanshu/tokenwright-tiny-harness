import os, pathlib
KEY = pathlib.Path("~/.config/anthropic/key").expanduser().read_text().strip()
ENDPOINT = "https://api.anthropic.com/v1/"
from pyrit.prompt_target import OpenAIChatTarget

GKEY = pathlib.Path("~/.config/gemini/key").expanduser().read_text().strip()
GENDPOINT = "https://generativelanguage.googleapis.com/v1beta/openai/"

def claude(model="claude-haiku-5-5", temperature=None, max_tokens=1500, rpm=None):
    g = model.startswith("gemini")
    return OpenAIChatTarget(model_name=model, endpoint=GENDPOINT if g else ENDPOINT, api_key=GKEY if g else KEY,
                            max_completion_tokens=max_tokens, temperature=temperature,
                            max_requests_per_minute=rpm)

# Anthropic's OpenAI-compatible endpoint rejects response_format json_object; the scorer prompts
# already ask for JSON, so drop the parameter (documented in DATA.md).
import pyrit.prompt_target.openai.openai_chat_target as _oct
_oct.build_response_format = lambda *, json_config: None
