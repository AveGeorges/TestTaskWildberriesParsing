"""Парсер WB через Playwright браузер."""

import logging
import random
import time
from urllib.parse import quote

from src.cache import get_cache_key, get_cached, set_cached
from src.config import (
    DELAY_BETWEEN_PAGES,
    DELAY_BETWEEN_PRODUCTS,
    DETAIL_API_URL,
    MAX_PAGES,
    PRODUCT_URL,
    SELLER_URL,
)
from src.models import Product

logger = logging.getLogger(__name__)


class WBBrowserParser:
    """Парсер через браузер - обходит блокировки."""
    
    def __init__(self, use_cache=True, headless=True):
        self.use_cache = use_cache
        self.headless = headless
        self._pw = None
        self._browser = None
        self._page = None
        self._api_data = {}

    def __enter__(self):
        self._init_browser()
        return self

    def __exit__(self, *args):
        self.close()

    def _init_browser(self):
        from playwright.sync_api import sync_playwright
        
        logger.info("Запуск браузера...")
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        ctx = self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            locale="ru-RU",
        )
        self._page = ctx.new_page()
        
        self._page.on("response", self._on_response)
        
        self._page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def _on_response(self, response):
        if "search.wb.ru" in response.url and "search" in response.url:
            try:
                self._api_data["search"] = response.json()
            except Exception:
                pass

    def close(self):
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        logger.info("Браузер закрыт")

    def _sleep(self, sec):
        time.sleep(sec + random.uniform(-0.3, 0.5))

    def _get_basket(self, vol):
        # TODO: может стоит вынести в конфиг, но пока работает так
        if vol <= 143:
            return "01"
        elif vol <= 287:
            return "02"
        elif vol <= 431:
            return "03"
        elif vol <= 719:
            return "04"
        elif vol <= 1007:
            return "05"
        elif vol <= 1061:
            return "06"
        elif vol <= 1115:
            return "07"
        elif vol <= 1169:
            return "08"
        elif vol <= 1313:
            return "09"
        elif vol <= 1601:
            return "10"
        elif vol <= 1655:
            return "11"
        elif vol <= 1919:
            return "12"
        elif vol <= 2045:
            return "13"
        elif vol <= 2189:
            return "14"
        elif vol <= 2405:
            return "15"
        elif vol <= 2621:
            return "16"
        else:
            return "17"

    def _get_images(self, article, count=10):
        vol = article // 100000
        part = article // 1000
        basket = self._get_basket(vol)
        base = f"https://basket-{basket}.wbbasket.ru/vol{vol}/part{part}/{article}/images/big"
        # генерим URL'ы, обычно их не больше 10, но на всякий случай
        images = []
        for i in range(1, count + 1):
            images.append(f"{base}/{i}.webp")
        return images

    def _parse_sizes(self, sizes_data):
        """Парсим размеры и остатки."""
        total_stock = 0
        sizes = []
        # иногда origName, иногда name - проверяем оба
        for s in sizes_data:
            name = s.get("origName") or s.get("name", "")
            if name and name not in sizes:
                sizes.append(name)
            # складываем остатки со всех складов
            stocks = s.get("stocks", [])
            if stocks:
                for stock in stocks:
                    qty = stock.get("qty", 0)
                    total_stock += qty  # просто суммируем, работает
        return sizes, total_stock

    def _product_from_api(self, item):
        """Создаём продукт из данных API."""
        article = item.get("id", 0)
        sizes_data = item.get("sizes", [])
        sizes, stock = self._parse_sizes(sizes_data)
        
        price = 0
        if sizes_data:
            price = sizes_data[0].get("price", {}).get("product", 0)
        
        seller_id = item.get("supplierId", 0)
        
        return Product(
            url=PRODUCT_URL.format(article=article),
            article=article,
            name=item.get("name", ""),
            price=price,
            images=self._get_images(article),
            seller_name=item.get("supplier", ""),
            seller_url=SELLER_URL.format(seller_id=seller_id) if seller_id else "",
            sizes=sizes,
            stock=stock,
            rating=item.get("reviewRating", 0),
            feedbacks_count=item.get("feedbacks", 0),
            brand=item.get("brand", ""),
        )

    def _product_from_html(self, card):
        """Парсим карточку из HTML."""
        try:
            article = int(card.get_attribute("data-nm-id") or 0)
            if not article:
                return None
            
            name_el = card.query_selector(".product-card__name")
            brand_el = card.query_selector(".product-card__brand")
            price_el = card.query_selector(".price__lower-price")
            rating_el = card.query_selector(".address-rate-mini")
            
            name = name_el.inner_text().strip() if name_el else ""
            brand = brand_el.inner_text().strip() if brand_el else ""
            
            price_text = price_el.inner_text() if price_el else "0"
            price = int("".join(c for c in price_text if c.isdigit())) * 100
            
            rating = 0.0
            if rating_el:
                try:
                    rating = float(rating_el.inner_text().replace(",", "."))
                except ValueError:
                    pass
            
            return Product(
                url=PRODUCT_URL.format(article=article),
                article=article,
                name=f"{brand} / {name}" if brand else name,
                price=price,
                images=self._get_images(article),
                brand=brand,
                rating=rating,
            )
        except Exception as e:
            logger.debug(f"HTML parse error: {e}")
            return None

    def search(self, query, max_pages=None):
        """Ищем товары."""
        pages = max_pages or MAX_PAGES
        products = []
        
        logger.info("Загрузка главной...")
        self._page.goto("https://www.wildberries.ru/", wait_until="networkidle", timeout=60000)
        self._sleep(3)
        
        # закрываем попапы если есть (иногда мешают)
        try:
            btn = self._page.query_selector("[class*='close']")
            if btn:
                btn.click()
                self._sleep(0.5)  # на всякий случай ждём
        except Exception:
            pass  # если нет попапа - ок
        
        for page in range(1, pages + 1):
            logger.info(f"Страница {page}/{pages}...")
            
            url = f"https://www.wildberries.ru/catalog/0/search.aspx?search={quote(query)}&page={page}"
            self._api_data.clear()
            
            ok = False
            for attempt in range(3):
                try:
                    self._page.goto(url, wait_until="load", timeout=45000)
                    self._sleep(3)
                    
                    if "search" in self._page.url or "catalog" in self._page.url:
                        ok = True
                        break
                    logger.warning(f"Редирект, попытка {attempt + 1}")
                    self._sleep(2)
                except Exception as e:
                    logger.warning(f"Ошибка загрузки: {e}")
                    self._sleep(2)
            
            if not ok:
                logger.warning(f"Страница {page} не загружена")
                continue
            
            try:
                self._page.wait_for_selector("article.product-card", timeout=10000)
            except Exception:
                pass
            
            self._page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            self._sleep(2)
            
            # пробуем сначала API, если не сработало - HTML
            if "search" in self._api_data:
                data = self._api_data["search"]
                items = data.get("data", {}).get("products", [])
                if not items:
                    logger.info("Пусто, конец")
                    break
                logger.info(f"API: {len(items)} товаров")
                for item in items:
                    products.append(self._product_from_api(item))
            else:
                # fallback на HTML если API не перехватили
                logger.info("API не перехвачен, парсим HTML")
                cards = self._page.query_selector_all("article.product-card")
                if not cards:
                    logger.warning("И HTML пуст, пропускаем страницу")
                    break
                for card in cards:
                    p = self._product_from_html(card)
                    if p:
                        products.append(p)
                logger.info(f"HTML: {len(cards)} товаров")
            
            if page < pages:
                self._sleep(DELAY_BETWEEN_PAGES)
        
        return products

    def get_detail(self, article):
        """Получаем детали товара (размеры, продавец)."""
        key = get_cache_key("detail", article)
        if self.use_cache:
            cached = get_cached(key)
            if cached:
                return cached
        
        url = f"{DETAIL_API_URL}?appType=1&curr=rub&dest=-1257786&spp=30&nm={article}"
        try:
            resp = self._page.request.get(url)
            if resp.ok:
                data = resp.json()
                items = data.get("data", {}).get("products", [])
                if items:
                    if self.use_cache:
                        set_cached(key, items[0])
                    return items[0]
        except Exception as e:
            logger.debug(f"Detail error {article}: {e}")
        return {}

    def get_card(self, article):
        """Получаем карточку (описание, характеристики)."""
        key = get_cache_key("card", article)
        if self.use_cache:
            cached = get_cached(key)
            if cached:
                return cached
        
        vol = article // 100000
        part = article // 1000
        basket = self._get_basket(vol)
        url = f"https://basket-{basket}.wbbasket.ru/vol{vol}/part{part}/{article}/info/ru/card.json"
        
        try:
            resp = self._page.request.get(url)
            if resp.ok:
                data = resp.json()
                if self.use_cache:
                    set_cached(key, data)
                return data
        except Exception as e:
            logger.debug(f"Card error {article}: {e}")
        return {}

    def enrich(self, product):
        """Дополняем продукт данными."""
        # сначала детали (размеры, продавец)
        detail = self.get_detail(product.article)
        if detail:
            seller_id = detail.get("supplierId", 0)
            product.seller_name = detail.get("supplier", "")
            # формируем ссылку на продавца
            if seller_id:
                product.seller_url = SELLER_URL.format(seller_id=seller_id)
            else:
                product.seller_url = ""
            
            sizes_data = detail.get("sizes", [])
            product.sizes, product.stock = self._parse_sizes(sizes_data)
            
            # если цены не было, берём из деталей
            if not product.price and sizes_data:
                price_info = sizes_data[0].get("price", {})
                product.price = price_info.get("product", 0)
            
            # обновляем рейтинг и отзывы если есть
            new_rating = detail.get("reviewRating")
            if new_rating:
                product.rating = new_rating
            new_feedbacks = detail.get("feedbacks")
            if new_feedbacks:
                product.feedbacks_count = new_feedbacks
        
        # потом карточка (описание, характеристики)
        card = self.get_card(product.article)
        if card:
            product.description = card.get("description", "")
            
            # парсим характеристики
            options = card.get("options", [])
            for opt in options:
                name = opt.get("name", "")
                value = opt.get("value", "")
                if name and value:
                    product.characteristics[name] = value
                    # ищем страну в названии характеристики
                    if "страна" in name.lower():
                        product.country = value
            
            # состав отдельно
            comps = card.get("compositions", [])
            if comps:
                comp_parts = []
                for c in comps:
                    if c.get("name"):
                        comp_parts.append(f"{c['name']}: {c['value']}")
                if comp_parts:
                    product.characteristics["Состав"] = "; ".join(comp_parts)
        
        return product

    def parse(self, query, max_pages=None, enrich=True):
        """Основной метод парсинга."""
        products = self.search(query, max_pages)
        logger.info(f"Найдено: {len(products)}")
        
        if enrich and products:
            logger.info("Обогащение данных...")
            for i, p in enumerate(products, 1):
                self.enrich(p)
                if i % 20 == 0:
                    logger.info(f"Обогащено {i}/{len(products)}")
                self._sleep(DELAY_BETWEEN_PRODUCTS)
        
        logger.info(f"Готово: {len(products)} товаров")
        return products
