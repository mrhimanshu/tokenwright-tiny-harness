from .money import to_money, apply_discount
from .inventory import Inventory


class Cart:
    def __init__(self, inventory: Inventory):
        self.inventory = inventory
        self.items = {}
        self.coupon = None

    def add(self, sku, qty=1):
        if qty <= 0:
            raise ValueError("qty must be positive")
        if not self.inventory.has(sku, self.items.get(sku, 0) + qty):
            raise ValueError("not enough stock")
        self.items[sku] = self.items.get(sku, 0) + qty

    def remove(self, sku, qty=1):
        left = self.items.get(sku, 0) - qty
        if left <= 0:
            self.items.pop(sku, None)
        else:
            self.items[sku] = left

    def apply_coupon(self, code):
        self.coupon = code

    def subtotal(self):
        return to_money(sum(self.inventory.price(s) * q for s, q in self.items.items()))

    def total(self):
        sub = self.subtotal()
        if self.coupon == "SAVE10":
            sub = apply_discount(sub, 10)
        if self.coupon == "BULK" and sum(self.items.values()) >= 10:
            sub = apply_discount(sub, 15)
        shipping = 0 if sub > 50 else 4.99
        return to_money(sub + shipping)
