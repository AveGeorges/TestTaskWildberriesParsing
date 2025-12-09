"""Конфиг парсера WB."""

import random

SEARCH_URL = "https://search.wb.ru/exactmatch/ru/common/v7/search"
DETAIL_API_URL = "https://card.wb.ru/cards/v2/detail"
SELLER_URL = "https://www.wildberries.ru/seller/{seller_id}"
PRODUCT_URL = "https://www.wildberries.ru/catalog/{article}/detail.aspx"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "*/*",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Origin": "https://www.wildberries.ru",
        "Referer": "https://www.wildberries.ru/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
    }


REQUEST_TIMEOUT = 30
RETRY_COUNT = 5
RETRY_DELAY = 3.0
MAX_PAGES = 50

DELAY_BETWEEN_PAGES = 2.0
DELAY_BETWEEN_PRODUCTS = 1.5
DELAY_ON_ERROR = 5.0

DEFAULT_FILTER = {
    "min_rating": 4.5,
    "max_price": 10000,
    "country": "Россия",
}
