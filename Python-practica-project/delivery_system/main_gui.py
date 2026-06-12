import tkinter as tk
from tkinter import messagebox, ttk

from database import (
    add_customer,
    add_order,
    close_database,
    count_orders_by_status,
    delete_order,
    delete_orders_without_items,
    filter_orders,
    get_all_customers,
    get_all_orders,
    get_order,
    init_database,
    revenue_for_period,
    top_3_customers_by_sum,
    update_order,
)
from models import ALLOWED_STATUSES, Customer, Order, OrderItem


database = init_database("sqlite")
delete_orders_without_items(database)
root = tk.Tk()
root.title("Система доставки")
root.geometry("1250x560")
root.minsize(1200, 520)

ALL_STATUSES_FILTER = "Все"
status_filter = tk.StringVar(value=ALL_STATUSES_FILTER)


def ensure_demo_customer():
    customers = get_all_customers(database)
    if customers:
        return customers[0].id
    customer = Customer("Тестовый клиент", "+70000000000", "Адрес клиента")
    return add_customer(database, customer)


def refresh_orders(select_order_id=None):
    for row in orders_tree.get_children():
        orders_tree.delete(row)

    status = status_filter.get()
    if status == ALL_STATUSES_FILTER:
        status = None
    orders = filter_orders(database, status=status)
    for order in orders:
        row_id = orders_tree.insert(
            "",
            "end",
            values=(order.id, order.date, order.customer_id, order.status, order.total_sum),
        )
        if order.id == select_order_id:
            orders_tree.selection_set(row_id)
            orders_tree.focus(row_id)


def selected_order_id():
    selected = orders_tree.selection()
    if not selected:
        messagebox.showwarning("Внимание", "Выберите заказ")
        return None
    return int(orders_tree.item(selected[0])["values"][0])


def open_order_window(order=None):
    window = tk.Toplevel(root)
    window.title("Заказ")
    window.geometry("420x380")
    window.minsize(380, 340)

    tk.Label(window, text="Дата (ГГГГ-ММ-ДД)").pack(anchor="w", padx=10, pady=3)
    date_entry = tk.Entry(window)
    date_entry.pack(fill="x", padx=10)

    tk.Label(window, text="Статус").pack(anchor="w", padx=10, pady=3)
    status_box = ttk.Combobox(window, values=ALLOWED_STATUSES, state="readonly")
    status_box.pack(fill="x", padx=10)

    tk.Label(window, text="Товар").pack(anchor="w", padx=10, pady=3)
    item_name_entry = tk.Entry(window)
    item_name_entry.pack(fill="x", padx=10)

    tk.Label(window, text="Количество").pack(anchor="w", padx=10, pady=3)
    quantity_entry = tk.Entry(window)
    quantity_entry.pack(fill="x", padx=10)

    tk.Label(window, text="Цена").pack(anchor="w", padx=10, pady=3)
    price_entry = tk.Entry(window)
    price_entry.pack(fill="x", padx=10)

    if order:
        date_entry.insert(0, order.date)
        status_box.set(order.status)
        if order.items:
            item_name_entry.insert(0, order.items[0].name)
            quantity_entry.insert(0, str(order.items[0].quantity))
            price_entry.insert(0, str(order.items[0].price))
    else:
        status_box.set("новый")

    def save_order():
        try:
            item = OrderItem(
                item_name_entry.get(),
                int(quantity_entry.get()),
                float(price_entry.get()),
            )
            if order:
                updated_order = get_order(database, order.id)
                if updated_order is None:
                    raise ValueError("Заказ не найден")
                updated_order.date = date_entry.get()
                updated_order.status = status_box.get()
                updated_order.items = [item]
                update_order(database, updated_order)
                status_filter.set(ALL_STATUSES_FILTER)
                saved_order_id = updated_order.id
            else:
                new_order = Order(
                    date=date_entry.get(),
                    customer_id=ensure_demo_customer(),
                    items=[item],
                    status=status_box.get(),
                )
                add_order(database, new_order)
                saved_order_id = new_order.id
            window.destroy()
            refresh_orders(saved_order_id)
        except Exception as error:
            messagebox.showerror("Ошибка", str(error))

    tk.Button(window, text="Сохранить", command=save_order).pack(pady=12)


def add_order_click():
    open_order_window()


def edit_order_click():
    order_id = selected_order_id()
    if order_id is None:
        return
    order = get_order(database, order_id)
    if order is None:
        messagebox.showerror("Ошибка", "Заказ не найден")
        refresh_orders()
        return
    open_order_window(order)


def delete_order_click():
    order_id = selected_order_id()
    if order_id is None:
        return
    delete_order(database, order_id)
    refresh_orders()


def show_report():
    statuses = count_orders_by_status(database)
    top_clients = top_3_customers_by_sum(database)
    text = "Количество заказов по статусам:\n"
    for status, count in statuses.items():
        text += f"{status}: {count}\n"
    text += "\nТоп-3 клиента:\n"
    for customer, total in top_clients:
        text += f"{customer.name}: {total}\n"
    text += f"\nВыручка за день: {revenue_for_period(database, 'day')}"
    text += f"\nВыручка за неделю: {revenue_for_period(database, 'week')}"
    text += f"\nВыручка за месяц: {revenue_for_period(database, 'month')}"
    messagebox.showinfo("Отчёт", text)


top_frame = tk.Frame(root)
top_frame.pack(fill="x", padx=10, pady=8)

tk.Button(top_frame, text="Добавить", command=add_order_click, height=2).pack(side="left", padx=4)
tk.Button(top_frame, text="Редактировать", command=edit_order_click).pack(side="left", padx=4)
tk.Button(top_frame, text="Удалить", command=delete_order_click).pack(side="left", padx=4)
tk.Label(top_frame, text="Фильтр по статусу").pack(side="left", padx=10)
status_box = ttk.Combobox(
    top_frame,
    values=(ALL_STATUSES_FILTER,) + ALLOWED_STATUSES,
    textvariable=status_filter,
)
status_box.pack(side="left", padx=4)
tk.Button(top_frame, text="Применить", command=refresh_orders).pack(side="left", padx=4)
tk.Button(top_frame, text="Показать отчёт", command=show_report).pack(side="left", padx=4)

columns = ("id", "date", "customer_id", "status", "total_sum")
orders_tree = ttk.Treeview(root, columns=columns, show="headings")
orders_tree.heading("id", text="ID")
orders_tree.heading("date", text="Дата")
orders_tree.heading("customer_id", text="Клиент")
orders_tree.heading("status", text="Статус")
orders_tree.heading("total_sum", text="Сумма")
orders_tree.pack(fill="both", expand=True, padx=10, pady=8)


def on_close():
    close_database(database)
    root.destroy()


root.protocol("WM_DELETE_WINDOW", on_close)
refresh_orders()
root.mainloop()
