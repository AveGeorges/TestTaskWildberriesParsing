DETAIL_API_URL = "https://card.wb.ru/cards/v2/detail"
SELLER_URL = "https://www.wildberries.ru/seller/{seller_id}"
PRODUCT_URL = "https://www.wildberries.ru/catalog/{article}/detail.aspx"

MAX_PAGES = 50

DELAY_BETWEEN_PAGES = 2.0
DELAY_BETWEEN_PRODUCTS = 1.5

DEFAULT_FILTER = {
    "min_rating": 4.5,
    "max_price": 10000,
    "country": "Россия",
}
