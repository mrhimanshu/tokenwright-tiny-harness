import pathlib
from store import orders, api, invoice

def test_new_name(): assert orders.order_total([(2.5, 2), (1.0, 3)]) == 8.0
def test_api(): assert api.checkout([(10, 1)]) == {"total": 10, "currency": "GBP"}
def test_invoice(): assert invoice.invoice_text([(1.25, 2)]) == "TOTAL: 2.50 GBP"
def test_old_name_gone():
    src = "".join(p.read_text() for p in pathlib.Path("store").glob("*.py"))
    assert "calc_total" not in src, "rename calc_total to order_total everywhere (no alias)"
