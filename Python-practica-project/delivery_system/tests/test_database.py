import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import (
    add_customer,
    add_order,
    close_database,
    count_orders_by_status,
    delete_customer,
    delete_orders_without_items,
    filter_orders,
    get_all_customers,
    get_all_orders,
    init_database,
    revenue_for_period,
    top_3_customers_by_sum,
    update_customer,
    update_order,
)
from models import Customer, Order, OrderItem


@pytest.fixture
def sqlite_db(tmp_path):
    database = init_database("sqlite", sqlite_path=tmp_path / "test.db")
    yield database
    close_database(database)


def test_customer_crud(sqlite_db):
    customer = Customer("Иван", "+79990000000", "Москва")
    customer_id = add_customer(sqlite_db, customer)
    assert customer_id is not None
    assert len(get_all_customers(sqlite_db)) == 1

    customer.name = "Пётр"
    update_customer(sqlite_db, customer)
    assert get_all_customers(sqlite_db)[0].name == "Пётр"

    delete_customer(sqlite_db, customer_id)
    assert get_all_customers(sqlite_db) == []


def test_order_crud_and_customer_delete_block(sqlite_db):
    customer = Customer("Иван", "+79990000000", "Москва")
    customer_id = add_customer(sqlite_db, customer)
    order = Order("2026-06-09", customer_id, [OrderItem("Пицца", 2, 300)])
    order_id = add_order(sqlite_db, order)

    assert order_id is not None
    assert len(get_all_orders(sqlite_db)) == 1

    order.status = "в доставке"
    update_order(sqlite_db, order)
    assert get_all_orders(sqlite_db)[0].status == "в доставке"

    with pytest.raises(ValueError):
        delete_customer(sqlite_db, customer_id)


def test_filters_and_reports(sqlite_db):
    first_customer = Customer("Иван", "+79990000000", "Москва")
    second_customer = Customer("Анна", "+78880000000", "Казань")
    first_id = add_customer(sqlite_db, first_customer)
    second_id = add_customer(sqlite_db, second_customer)

    add_order(sqlite_db, Order("2026-06-09", first_id, [OrderItem("Пицца", 1, 500)], "новый"))
    add_order(sqlite_db, Order("2026-06-09", second_id, [OrderItem("Суши", 2, 400)], "выполнен"))

    assert len(filter_orders(sqlite_db, status="новый")) == 1
    assert len(filter_orders(sqlite_db, order_date="2026-06-09")) == 2
    assert count_orders_by_status(sqlite_db)["новый"] == 1
    assert top_3_customers_by_sum(sqlite_db)[0][0].name == "Анна"
    assert revenue_for_period(sqlite_db, "day", "2026-06-09") == 1300


def test_tinydb_mode(tmp_path):
    database = init_database("tinydb", tinydb_path=tmp_path / "tinydb.json")
    try:
        customer_id = add_customer(database, Customer("Иван", "+79990000000", "Москва"))
        add_order(database, Order("2026-06-09", customer_id, [OrderItem("Пицца", 1, 500)]))
        assert len(get_all_orders(database)) == 1
    finally:
        close_database(database)


def test_failed_order_insert_rolls_back_partial_order(sqlite_db):
    customer_id = add_customer(sqlite_db, Customer("Иван", "+79990000000", "Москва"))
    item = OrderItem("Пицца", 1, 500)
    order = Order("2026-06-09", customer_id, [item])
    item.quantity = 10**30

    with pytest.raises(OverflowError):
        add_order(sqlite_db, order)

    assert get_all_orders(sqlite_db) == []


def test_delete_orders_without_items_removes_broken_rows(sqlite_db):
    customer_id = add_customer(sqlite_db, Customer("Иван", "+79990000000", "Москва"))
    sqlite_db["connection"].execute(
        "INSERT INTO orders (date, customer_id, status, total_sum) VALUES (?, ?, ?, ?)",
        ("2026-06-09", customer_id, "новый", 0),
    )
    sqlite_db["connection"].commit()

    assert len(get_all_orders(sqlite_db)) == 1
    assert delete_orders_without_items(sqlite_db) == 1
    assert get_all_orders(sqlite_db) == []
