import json
import xml.etree.ElementTree as ET
from pathlib import Path

from database import add_customer, add_order, get_all_orders, get_customer
from logger_config import logger
from models import Customer, Order, OrderItem


def order_to_dict(database, order):
    customer = get_customer(database, order.customer_id)
    return {
        "id": order.id,
        "date": order.date,
        "status": order.status,
        "total_sum": order.total_sum,
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "phone": customer.phone,
            "address": customer.address,
        },
        "items": [
            {
                "name": item.name,
                "quantity": item.quantity,
                "price": item.price,
            }
            for item in order.items
        ],
    }


def _order_signature(database, order):
    customer = get_customer(database, order.customer_id)
    customer_signature = None
    if customer:
        customer_signature = (customer.name, customer.phone, customer.address)

    items_signature = tuple(
        sorted((item.name, int(item.quantity), float(item.price)) for item in order.items)
    )
    return (order.date, order.status, customer_signature, items_signature)


def _order_data_signature(order_data):
    customer_data = order_data["customer"]
    customer_signature = (
        customer_data["name"],
        customer_data["phone"],
        customer_data["address"],
    )
    items_signature = tuple(
        sorted(
            (item["name"], int(item["quantity"]), float(item["price"]))
            for item in order_data["items"]
        )
    )
    return (order_data["date"], order_data["status"], customer_signature, items_signature)


def _existing_order_signatures(database):
    return {_order_signature(database, order) for order in get_all_orders(database)}


def export_orders(database, file_name):
    try:
        path = Path(file_name)
        data = [order_to_dict(database, order) for order in get_all_orders(database)]

        if path.suffix.lower() == ".json":
            with open(path, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)
        elif path.suffix.lower() == ".xml":
            root = ET.Element("orders")
            for order_data in data:
                order_element = ET.SubElement(root, "order")
                order_element.set("date", order_data["date"])
                order_element.set("status", order_data["status"])
                order_element.set("total_sum", str(order_data["total_sum"]))

                customer_element = ET.SubElement(order_element, "customer")
                for key, value in order_data["customer"].items():
                    customer_element.set(key, str(value))

                items_element = ET.SubElement(order_element, "items")
                for item in order_data["items"]:
                    item_element = ET.SubElement(items_element, "item")
                    item_element.set("name", item["name"])
                    item_element.set("quantity", str(item["quantity"]))
                    item_element.set("price", str(item["price"]))

            tree = ET.ElementTree(root)
            tree.write(path, encoding="utf-8", xml_declaration=True)
        else:
            raise ValueError("Поддерживаются только файлы JSON и XML")

        logger.info("Экспорт выполнен: %s", file_name)
    except Exception as error:
        logger.error("Ошибка экспорта: %s", error)
        raise


def import_orders(database, file_name):
    try:
        path = Path(file_name)
        if path.suffix.lower() == ".json":
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
        elif path.suffix.lower() == ".xml":
            data = _read_xml(path)
        else:
            raise ValueError("Поддерживаются только файлы JSON и XML")

        existing_signatures = _existing_order_signatures(database)
        created_count = 0
        skipped_count = 0

        for order_data in data:
            order_signature = _order_data_signature(order_data)
            if order_signature in existing_signatures:
                skipped_count += 1
                continue

            customer_data = order_data["customer"]
            customer = Customer(
                customer_data["name"],
                customer_data["phone"],
                customer_data["address"],
            )
            customer_id = add_customer(database, customer)
            items = [
                OrderItem(item["name"], int(item["quantity"]), float(item["price"]))
                for item in order_data["items"]
            ]
            order = Order(
                date=order_data["date"],
                customer_id=customer_id,
                items=items,
                status=order_data["status"],
            )
            add_order(database, order)
            existing_signatures.add(order_signature)
            created_count += 1

        logger.info(
            "Импорт выполнен: %s, создано: %s, пропущено дублей: %s",
            file_name,
            created_count,
            skipped_count,
        )
        return {"created": created_count, "skipped": skipped_count}
    except Exception as error:
        logger.error("Ошибка импорта: %s", error)
        raise


def _read_xml(path):
    tree = ET.parse(path)
    root = tree.getroot()
    data = []

    for order_element in root.findall("order"):
        customer_element = order_element.find("customer")
        items_element = order_element.find("items")
        data.append({
            "date": order_element.get("date"),
            "status": order_element.get("status"),
            "total_sum": float(order_element.get("total_sum")),
            "customer": {
                "name": customer_element.get("name"),
                "phone": customer_element.get("phone"),
                "address": customer_element.get("address"),
            },
            "items": [
                {
                    "name": item.get("name"),
                    "quantity": int(item.get("quantity")),
                    "price": float(item.get("price")),
                }
                for item in items_element.findall("item")
            ],
        })
    return data
