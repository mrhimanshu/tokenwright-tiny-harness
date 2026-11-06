import io, json, contextlib
import report

def run(args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        report.main(args)
    return buf.getvalue()

def test_text_still_works(): assert run(["--top", "1"]).split() == ["tshirt", "340"]
def test_json_flag(): assert json.loads(run(["--json"])) == [{"name": "tshirt", "total": 340}, {"name": "hoodie", "total": 210}, {"name": "mug", "total": 120}, {"name": "sticker", "total": 75}]
def test_json_with_top(): assert json.loads(run(["--json", "--top", "2"])) == [{"name": "tshirt", "total": 340}, {"name": "hoodie", "total": 210}]
