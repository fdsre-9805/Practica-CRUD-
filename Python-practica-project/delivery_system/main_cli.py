import argparse
from pathlib import Path

from data_export import export_orders, import_orders
from database import (
    close_database,
    count_orders_by_status,
    init_database,
    revenue_for_period,
    top_3_customers_by_sum,
)


def print_report(database, period):
    print("Количество заказов по статусам:")
    for status, count in count_orders_by_status(database).items():
        print(f"{status}: {count}")

    print("\nТоп-3 клиента по сумме заказов:")
    for customer, total in top_3_customers_by_sum(database):
        print(f"{customer.name}: {total}")

    print(f"\nВыручка за период {period}: {revenue_for_period(database, period)}")


def main():
    parser = argparse.ArgumentParser(description="Система учёта доставки заказов")
    parser.add_argument(
        "--db",
        choices=["sqlite", "tinydb"],
        default="sqlite",
        help="Тип базы данных",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    report_parser = subparsers.add_parser("report")
    report_parser.add_argument("--period", choices=["day", "week", "month"], required=True)

    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("--file", required=True)

    import_parser = subparsers.add_parser("import")
    import_parser.add_argument("--file", required=True)

    args = parser.parse_args()
    database = init_database(args.db)

    try:
        if args.command == "report":
            print_report(database, args.period)
        elif args.command == "export":
            export_orders(database, Path(args.file))
            print("Экспорт выполнен")
        elif args.command == "import":
            result = import_orders(database, Path(args.file))
            print(
                f"Импорт выполнен. Создано: {result['created']}, "
                f"пропущено дублей: {result['skipped']}"
            )
    finally:
        close_database(database)


if __name__ == "__main__":
    main()
