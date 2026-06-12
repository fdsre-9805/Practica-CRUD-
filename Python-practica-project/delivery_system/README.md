 Система учёта доставки заказов , CRUD (сделано на ОС GNU linux ubuntu) , Язык установки и запуcка Bash


## Установка данного круда 

```bash
cd /home/antisuffer/Python-practica-project
python3 -m pip install -r delivery_system/requirements.txt
```

## Запуск CLI

```bash
cd /home/antisuffer/Python-practica-project/delivery_system
python3 main_cli.py report --period day
python3 main_cli.py report --period week
python3 main_cli.py report --period month

python3 main_cli.py export --file orders.json
python3 main_cli.py export --file orders.xml

python3 main_cli.py import --file orders.json
python3 main_cli.py import --file orders.xml
```

Для работы с TinyDB  добавить :

```bash
python3 main_cli.py --db tinydb report --period day
```

## Запуск GUI

```bash
cd /home/antisuffer/Python-practica-project/delivery_system
python3 main_gui.py
```

## Запуск тестов

```bash
cd /home/antisuffer/Python-practica-project
pytest delivery_system/tests
```

## Структура проекта

```text
delivery_system/
├── main_cli.py            # CLI-точка входа (argparse)
├── main_gui.py            # GUI-точка входа (Tkinter)
├── database.py            # Работа с БД (SQLite или TinyDB)
├── models.py              # Классы Customer, Order
├── data_export.py         # Экспорт/импорт XML/JSON
├── logger_config.py       # Настройка логирования
├── tests/
│   ├── test_database.py
│   ├── test_models.py
│   └── test_export.py
├── logs/                  # Папка для логов
├── data/
│   ├── delivery.db        # SQLite-файл (если выбран SQLite)
│   └── tinydb.json        # TinyDB-файл (если выбран TinyDB)
├── requirements.txt       # pytest, tinydb; остальное — встроенное
└── README.md              # Инструкция по установке и запуску
```
