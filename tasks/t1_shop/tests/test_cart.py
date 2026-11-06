
from shop.cart import Cart
from shop.inventory import Inventory

CAT = {"A": {"name": "A", "price": 20.0, "stock": 5}, "B": {"name": "B", "price": 5.0, "stock": 50}}


def cart():
    return Cart(Inventory(CAT))


def test_can_buy_exact_stock():
    c = cart()
    c.add("A", 5)          # exactly the 5 in stock should be allowed
    assert c.items["A"] == 5


def test_save10():
    c = cart(); c.add("A", 3); c.apply_coupon("SAVE10")
    assert str(c.total()) == "54.00"


def test_free_shipping_boundary():
    c = cart(); c.add("B", 10)   # exactly 50.00 should ship free
    assert str(c.total()) == "50.00"


def test_bulk():
    c = cart(); c.add("B", 12); c.apply_coupon("BULK")
    assert str(c.total()) == "51.00"
