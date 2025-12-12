import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

DETAIL_API_URL = os.getenv("DETAIL_API_URL", "https://card.wb.ru/cards/v2/detail")
SELLER_URL = os.getenv("SELLER_URL", "https://www.wildberries.ru/seller/{seller_id}")
PRODUCT_URL = os.getenv("PRODUCT_URL", "https://www.wildberries.ru/catalog/{article}/detail.aspx")

MAX_PAGES = int(os.getenv("MAX_PAGES", "50"))

DELAY_BETWEEN_PAGES = float(os.getenv("DELAY_BETWEEN_PAGES", "2.0"))
DELAY_BETWEEN_PRODUCTS = float(os.getenv("DELAY_BETWEEN_PRODUCTS", "1.5"))

DEFAULT_FILTER = {
    "min_rating": float(os.getenv("DEFAULT_MIN_RATING", "4.5")),
    "max_price": int(os.getenv("DEFAULT_MAX_PRICE", "10000")),
    "country": os.getenv("DEFAULT_COUNTRY", "Россия"),
}
