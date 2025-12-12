# WB Parser

Парсер каталога Wildberries по поисковому запросу.

## Что делает

- Ищет товары по запросу
- Собирает данные: артикул, название, цена, описание, характеристики, продавец, размеры, остатки, рейтинг
- Сохраняет в Excel
- Фильтрует по рейтингу, цене и стране

## Установка

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r req.txt

playwright install chromium

cp .env.example .env
```

Настройте переменные в файле `.env` при необходимости (по умолчанию используются значения из `.env.example`).

## Переменные окружения

Все настройки можно изменить через файл `.env`:

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `DETAIL_API_URL` | URL API для деталей товара | `https://card.wb.ru/cards/v2/detail` |
| `SELLER_URL` | Шаблон URL продавца | `https://www.wildberries.ru/seller/{seller_id}` |
| `PRODUCT_URL` | Шаблон URL товара | `https://www.wildberries.ru/catalog/{article}/detail.aspx` |
| `MAX_PAGES` | Максимальное количество страниц | `50` |
| `DELAY_BETWEEN_PAGES` | Задержка между страницами (сек) | `2.0` |
| `DELAY_BETWEEN_PRODUCTS` | Задержка между товарами (сек) | `1.5` |
| `DEFAULT_MIN_RATING` | Минимальный рейтинг для фильтра | `4.5` |
| `DEFAULT_MAX_PRICE` | Максимальная цена для фильтра | `10000` |
| `DEFAULT_COUNTRY` | Страна для фильтра | `Россия` |

## Использование

```bash
# Базовый пример: 10 страниц, запрос "пальто из натуральной шерсти"
python -m src.main -q "пальто из натуральной шерсти" -p 10

# Показать окно браузера
python -m src.main -q "пальто" -p 5 --show-browser

# Без обогащения данных (только поиск)
python -m src.main -q "пальто" -p 3 --no-enrich
```

## Параметры

| Флаг | Описание |
|------|----------|
| `-q` | Поисковый запрос |
| `-p` | Кол-во страниц |
| `-o` | Папка вывода (default: output) |
| `--show-browser` | Показать окно браузера |
| `--no-enrich` | Без описаний/характеристик |
| `--no-cache` | Без кэша |
| `--clear-cache` | Очистить кэш |
| `--min-rating` | Мин. рейтинг для фильтра (4.5) |
| `--max-price` | Макс. цена (10000) |
| `--country` | Страна (Россия) |

## Результат

- `catalog_full_*.xlsx` — все товары
- `catalog_filtered_*.xlsx` — отфильтрованные (рейтинг >= 4.5, цена <= 10000, Россия)

## Структура

```
src/
├── main.py         — точка входа, CLI
├── wb_browser.py   — парсер через Playwright  
├── excel_writer.py — экспорт в xlsx
├── models.py       — модель Product
├── config.py       — настройки
└── cache.py        — файловый кэш
```
