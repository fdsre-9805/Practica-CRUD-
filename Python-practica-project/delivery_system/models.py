from dataclasses import dataclass, field


ALLOWED_STATUSES = ("новый", "в доставке", "выполнен", "отменён")
MAX_SQLITE_INTEGER = 9_223_372_036_854_775_807


@dataclass
class Customer:
    name: str
    phone: str
    address: str
    id: int | None = None

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("Имя клиента не может быть пустым")
        if not self.phone.strip():
            raise ValueError("Телефон клиента не может быть пустым")
        if not self.address.strip():
            raise ValueError("Адрес клиента не может быть пустым")


@dataclass
class OrderItem:
    name: str
    quantity: int
    price: float
    id: int | None = None
    order_id: int | None = None

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("Название товара не может быть пустым")
        if self.quantity <= 0:
            raise ValueError("Количество товара должно быть больше нуля")
        if self.quantity > MAX_SQLITE_INTEGER:
            raise ValueError("Количество товара слишком большое")
        if self.price < 0:
            raise ValueError("Цена товара не может быть отрицательной")

    def total(self) -> float:
        return round(self.quantity * self.price, 2)


@dataclass
class Order:
    date: str
    customer_id: int
    items: list[OrderItem] = field(default_factory=list)
    status: str = "новый"
    total_sum: float = 0
    id: int | None = None

    def __post_init__(self):
        if not self.date.strip():
            raise ValueError("Дата заказа не может быть пустой")
        if self.status not in ALLOWED_STATUSES:
            raise ValueError("Недопустимый статус заказа")
        if self.customer_id is None:
            raise ValueError("У заказа должен быть клиент")
        self.total_sum = round(sum(item.total() for item in self.items), 2)
