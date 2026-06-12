import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models import Customer, Order, OrderItem


def test_customer_creation():
    customer = Customer("Иван", "+79990000000", "Москва")
    assert customer.name == "Иван"


def test_order_item_total():
    item = OrderItem("Пицца", 2, 350)
    assert item.total() == 700


def test_order_total_sum():
    order = Order(
        "2026-06-09",
        1,
        [OrderItem("Пицца", 2, 350), OrderItem("Сок", 1, 100)],
    )
    assert order.total_sum == 800


def test_wrong_status():
    with pytest.raises(ValueError):
        Order("2026-06-09", 1, [], "ошибка")


def test_order_item_rejects_too_large_quantity():
    with pytest.raises(ValueError, match="Количество товара слишком большое"):
        OrderItem("Пицца", 10**30, 350)
