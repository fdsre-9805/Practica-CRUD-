import sqlite3
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from logger_config import logger
from models import Customer, Order, OrderItem


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SQLITE_PATH = DATA_DIR / "delivery.db"
TINYDB_PATH = DATA_DIR / "tinydb.json"


def init_database(db_type="sqlite", sqlite_path=None, tinydb_path=None):
    DATA_DIR.mkdir(exist_ok=True)
    if db_type == "sqlite":
        path = sqlite_path or SQLITE_PATH
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        create_sqlite_tables(connection)
        return {"type": "sqlite", "connection": connection}

    if db_type == "tinydb":
        try:
            from tinydb import TinyDB
        except ImportError as error:
            raise ImportError("Для режима TinyDB установите пакет tinydb") from error

        path = tinydb_path or TINYDB_PATH
        db = TinyDB(path, ensure_ascii=False, indent=2)
        return {"type": "tinydb", "db": db}

    raise ValueError("Неизвестный тип базы данных")


def close_database(database):
    if database["type"] == "sqlite":
        database["connection"].close()
    else:
        database["db"].close()


def rollback_database(database):
    if database["type"] == "sqlite":
        database["connection"].rollback()


def create_sqlite_tables(connection):
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            customer_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            total_sum REAL NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    """)
    connection.commit()


def _next_id(table):
    all_rows = table.all()
    if not all_rows:
        return 1
    return max(row["id"] for row in all_rows) + 1


def add_customer(database, customer):
    try:
        if database["type"] == "sqlite":
            cursor = database["connection"].cursor()
            cursor.execute(
                "INSERT INTO customers (name, phone, address) VALUES (?, ?, ?)",
                (customer.name, customer.phone, customer.address),
            )
            database["connection"].commit()
            customer.id = cursor.lastrowid
        else:
            table = database["db"].table("customers")
            customer.id = _next_id(table)
            table.insert(customer.__dict__)

        logger.info("Создан клиент: %s", customer.name)
        return customer.id
    except Exception as error:
        rollback_database(database)
        logger.error("Ошибка создания клиента: %s", error)
        raise


def get_customer(database, customer_id):
    if database["type"] == "sqlite":
        row = database["connection"].execute(
            "SELECT * FROM customers WHERE id = ?", (customer_id,)
        ).fetchone()
        if row:
            return Customer(row["name"], row["phone"], row["address"], row["id"])
        return None

    from tinydb import Query

    row = database["db"].table("customers").get(Query().id == customer_id)
    if row:
        return Customer(row["name"], row["phone"], row["address"], row["id"])
    return None


def get_all_customers(database):
    if database["type"] == "sqlite":
        rows = database["connection"].execute("SELECT * FROM customers").fetchall()
        return [Customer(row["name"], row["phone"], row["address"], row["id"]) for row in rows]

    rows = database["db"].table("customers").all()
    return [Customer(row["name"], row["phone"], row["address"], row["id"]) for row in rows]


def update_customer(database, customer):
    try:
        if database["type"] == "sqlite":
            database["connection"].execute(
                "UPDATE customers SET name = ?, phone = ?, address = ? WHERE id = ?",
                (customer.name, customer.phone, customer.address, customer.id),
            )
            database["connection"].commit()
        else:
            from tinydb import Query

            database["db"].table("customers").update(
                customer.__dict__, Query().id == customer.id
            )

        logger.info("Изменён клиент: %s", customer.id)
    except Exception as error:
        rollback_database(database)
        logger.error("Ошибка изменения клиента: %s", error)
        raise


def delete_customer(database, customer_id):
    try:
        if get_orders_by_customer(database, customer_id):
            raise ValueError("Нельзя удалить клиента, у которого есть заказы")

        if database["type"] == "sqlite":
            database["connection"].execute(
                "DELETE FROM customers WHERE id = ?", (customer_id,)
            )
            database["connection"].commit()
        else:
            from tinydb import Query

            database["db"].table("customers").remove(Query().id == customer_id)

        logger.info("Удалён клиент: %s", customer_id)
    except Exception as error:
        rollback_database(database)
        logger.error("Ошибка удаления клиента: %s", error)
        raise


def add_order(database, order):
    try:
        if database["type"] == "sqlite":
            cursor = database["connection"].cursor()
            cursor.execute(
                "INSERT INTO orders (date, customer_id, status, total_sum) VALUES (?, ?, ?, ?)",
                (order.date, order.customer_id, order.status, order.total_sum),
            )
            order.id = cursor.lastrowid
            for item in order.items:
                cursor.execute(
                    "INSERT INTO order_items (order_id, name, quantity, price) VALUES (?, ?, ?, ?)",
                    (order.id, item.name, item.quantity, item.price),
                )
                item.id = cursor.lastrowid
                item.order_id = order.id
            database["connection"].commit()
        else:
            orders = database["db"].table("orders")
            items = database["db"].table("order_items")
            order.id = _next_id(orders)
            orders.insert({
                "id": order.id,
                "date": order.date,
                "customer_id": order.customer_id,
                "status": order.status,
                "total_sum": order.total_sum,
            })
            for item in order.items:
                item.id = _next_id(items)
                item.order_id = order.id
                items.insert(item.__dict__)

        logger.info("Создан заказ: %s", order.id)
        return order.id
    except Exception as error:
        rollback_database(database)
        logger.error("Ошибка создания заказа: %s", error)
        raise


def _get_order_items(database, order_id):
    if database["type"] == "sqlite":
        rows = database["connection"].execute(
            "SELECT * FROM order_items WHERE order_id = ?", (order_id,)
        ).fetchall()
        return [
            OrderItem(row["name"], row["quantity"], row["price"], row["id"], row["order_id"])
            for row in rows
        ]

    from tinydb import Query

    rows = database["db"].table("order_items").search(Query().order_id == order_id)
    return [
        OrderItem(row["name"], row["quantity"], row["price"], row["id"], row["order_id"])
        for row in rows
    ]


def _order_from_row(database, row):
    items = _get_order_items(database, row["id"])
    return Order(
        date=row["date"],
        customer_id=row["customer_id"],
        items=items,
        status=row["status"],
        id=row["id"],
    )


def get_order(database, order_id):
    if database["type"] == "sqlite":
        row = database["connection"].execute(
            "SELECT * FROM orders WHERE id = ?", (order_id,)
        ).fetchone()
        if row:
            return _order_from_row(database, row)
        return None

    from tinydb import Query

    row = database["db"].table("orders").get(Query().id == order_id)
    if row:
        return _order_from_row(database, row)
    return None


def get_all_orders(database):
    if database["type"] == "sqlite":
        rows = database["connection"].execute("SELECT * FROM orders").fetchall()
    else:
        rows = database["db"].table("orders").all()
    return [_order_from_row(database, row) for row in rows]


def get_orders_by_customer(database, customer_id):
    return [order for order in get_all_orders(database) if order.customer_id == customer_id]


def delete_orders_without_items(database):
    try:
        if database["type"] == "sqlite":
            cursor = database["connection"].execute(
                """
                DELETE FROM orders
                WHERE id NOT IN (SELECT DISTINCT order_id FROM order_items)
                """
            )
            database["connection"].commit()
            deleted_count = cursor.rowcount
        else:
            from tinydb import Query

            items = database["db"].table("order_items").all()
            valid_order_ids = {item["order_id"] for item in items}
            orders = database["db"].table("orders")
            deleted_count = len(
                orders.remove(~Query().id.one_of(valid_order_ids))
            )

        if deleted_count:
            logger.info("Удалены пустые заказы без товаров: %s", deleted_count)
        return deleted_count
    except Exception as error:
        rollback_database(database)
        logger.error("Ошибка удаления пустых заказов: %s", error)
        raise


def update_order(database, order):
    try:
        order.total_sum = round(sum(item.total() for item in order.items), 2)
        if database["type"] == "sqlite":
            cursor = database["connection"].cursor()
            cursor.execute(
                "UPDATE orders SET date = ?, customer_id = ?, status = ?, total_sum = ? WHERE id = ?",
                (order.date, order.customer_id, order.status, order.total_sum, order.id),
            )
            cursor.execute("DELETE FROM order_items WHERE order_id = ?", (order.id,))
            for item in order.items:
                cursor.execute(
                    "INSERT INTO order_items (order_id, name, quantity, price) VALUES (?, ?, ?, ?)",
                    (order.id, item.name, item.quantity, item.price),
                )
            database["connection"].commit()
        else:
            from tinydb import Query

            database["db"].table("orders").update({
                "date": order.date,
                "customer_id": order.customer_id,
                "status": order.status,
                "total_sum": order.total_sum,
            }, Query().id == order.id)
            database["db"].table("order_items").remove(Query().order_id == order.id)
            items = database["db"].table("order_items")
            for item in order.items:
                item.id = _next_id(items)
                item.order_id = order.id
                items.insert(item.__dict__)

        logger.info("Изменён заказ: %s", order.id)
    except Exception as error:
        rollback_database(database)
        logger.error("Ошибка изменения заказа: %s", error)
        raise


def delete_order(database, order_id):
    try:
        if database["type"] == "sqlite":
            database["connection"].execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
            database["connection"].execute("DELETE FROM orders WHERE id = ?", (order_id,))
            database["connection"].commit()
        else:
            from tinydb import Query

            database["db"].table("order_items").remove(Query().order_id == order_id)
            database["db"].table("orders").remove(Query().id == order_id)

        logger.info("Удалён заказ: %s", order_id)
    except Exception as error:
        rollback_database(database)
        logger.error("Ошибка удаления заказа: %s", error)
        raise


def filter_orders(database, status=None, order_date=None):
    orders = get_all_orders(database)
    if status:
        orders = [order for order in orders if order.status == status]
    if order_date:
        orders = [order for order in orders if order.date == order_date]
    return orders


def count_orders_by_status(database):
    return dict(Counter(order.status for order in get_all_orders(database)))


def top_3_customers_by_sum(database):
    totals = defaultdict(float)
    for order in get_all_orders(database):
        totals[order.customer_id] += order.total_sum

    result = []
    for customer_id, total in sorted(totals.items(), key=lambda item: item[1], reverse=True)[:3]:
        customer = get_customer(database, customer_id)
        if customer:
            result.append((customer, round(total, 2)))
    return result


def revenue_for_period(database, period, base_date=None):
    base = base_date or date.today()
    if isinstance(base, str):
        base = datetime.strptime(base, "%Y-%m-%d").date()

    if period == "day":
        start = end = base
    elif period == "week":
        start = base - timedelta(days=base.weekday())
        end = start + timedelta(days=6)
    elif period == "month":
        start = base.replace(day=1)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
    else:
        raise ValueError("Период должен быть day, week или month")

    total = 0
    for order in get_all_orders(database):
        order_date = datetime.strptime(order.date, "%Y-%m-%d").date()
        if start <= order_date <= end and order.status != "отменён":
            total += order.total_sum
    return round(total, 2)
