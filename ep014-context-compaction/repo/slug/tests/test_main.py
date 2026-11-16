from textkit.slug import slugify

def test_basic(): assert slugify("Hello World") == "hello-world"
def test_punctuation(): assert slugify("What's new, in AI?") == "whats-new-in-ai"
def test_collapse(): assert slugify("a  --  b") == "a-b"
def test_strip_edges(): assert slugify("  -Trim me-  ") == "trim-me"
def test_accents(): assert slugify("Café Déjà Vu") == "cafe-deja-vu"
def test_numbers(): assert slugify("GPT 6 vs Claude 5.5") == "gpt-6-vs-claude-5-5"
def test_empty(): assert slugify("!!!") == ""
