import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data_export import export_orders, import_orders
from database import add_customer, add_order, close_database, get_all_orders, init_database
from models import Customer, Order, OrderItem


def make_database_with_order(path):
    database = init_database("sqlite", sqlite_path=path)
    customer_id = add_customer(database, Customer("Иван", "+79990000000", "Москва"))
    add_order(database, Order("2026-06-09", customer_id, [OrderItem("Пицца", 2, 300)]))
    return database


def test_json_export_import(tmp_path):
    source = make_database_with_order(tmp_path / "source.db")
    file_name = tmp_path / "orders.json"
    export_orders(source, file_name)
    close_database(source)

    target = init_database("sqlite", sqlite_path=tmp_path / "target.db")
    result = import_orders(target, file_name)
    assert result == {"created": 1, "skipped": 0}

    second_result = import_orders(target, file_name)
    assert second_result == {"created": 0, "skipped": 1}
    assert len(get_all_orders(target)) == 1
    assert get_all_orders(target)[0].total_sum == 600
    close_database(target)


def test_xml_export_import(tmp_path):
    source = make_database_with_order(tmp_path / "source_xml.db")
    file_name = tmp_path / "orders.xml"
    export_orders(source, file_name)
    close_database(source)

    target = init_database("sqlite", sqlite_path=tmp_path / "target_xml.db")
    result = import_orders(target, file_name)
    assert result == {"created": 1, "skipped": 0}

    second_result = import_orders(target, file_name)
    assert second_result == {"created": 0, "skipped": 1}
    assert len(get_all_orders(target)) == 1
    assert get_all_orders(target)[0].items[0].name == "Пицца"
    close_database(target)
