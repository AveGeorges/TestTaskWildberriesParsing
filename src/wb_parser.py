"""Парсер WB через HTTP запросы."""

import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

from src.cache import get_cache_key, get_cached, set_cached
from src.config import (
    DELAY_BETWEEN_PAGES,
    DELAY_BETWEEN_PRODUCTS,
    DELAY_ON_ERROR,
    MAX_PAGES,
    PRODUCT_URL,
    REQUEST_TIMEOUT,
    RETRY_COUNT,
    RETRY_DELAY,
    SEARCH_URL,
    SELLER_URL,
    get_headers,
)
from src.models import Product

logger = logging.getLogger(__name__)


class WildberriesParser:
    """HTTP парсер WB - работает без браузера, но может блокироваться."""
    
    def __init__(self, use_cache=True, max_workers=5, proxy=None):
        self.use_cache = use_cache
        self.max_workers = max_workers
        self.proxy = proxy
        self._client = None
        self._req_count = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _get_client(self):
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                headers=get_headers(),
                timeout=REQUEST_TIMEOUT,
                follow_redirects=True,
                proxy=self.proxy,
            )
        return self._client

    def _refresh_client(self):
        if self._client and not self._client.is_closed:
            self._client.close()
        self._client = httpx.Client(
            headers=get_headers(),
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            proxy=self.proxy,
        )

    def close(self):
        if self._client and not self._client.is_closed:
            self._client.close()

    def _sleep(self, sec):
        time.sleep(sec + random.uniform(-0.2, 0.3))

    def _request(self, url, params=None, cache_prefix=None):
        """Запрос с ретраями и кэшем."""
        cache_key = None
        if self.use_cache and cache_prefix:
            cache_key = get_cache_key(cache_prefix, url, str(sorted(params.items()) if params else ""))
            cached = get_cached(cache_key)
            if cached:
                return cached
        
        last_err = None
        for attempt in range(RETRY_COUNT):
            try:
                self._req_count += 1
                client = self._get_client()
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                
                if cache_key and data:
                    set_cached(cache_key, data)
                return data
                
            except httpx.HTTPStatusError as e:
                last_err = e
                code = e.response.status_code
                
                if code == 429:
                    wait = DELAY_ON_ERROR * (attempt + 1) * 2
                    logger.warning(f"429 Too Many Requests, ждём {wait}с...")
                    self._refresh_client()
                    time.sleep(wait)
                elif code == 404:
                    return None
                elif code >= 500:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    logger.error(f"HTTP {code}: {url[:50]}...")
                    return None
                    
            except httpx.TimeoutException:
                last_err = "timeout"
                time.sleep(RETRY_DELAY * (attempt + 1))
            except httpx.RequestError as e:
                last_err = e
                time.sleep(RETRY_DELAY * (attempt + 1))
        
        logger.error(f"Все попытки провалились: {last_err}")
        return None

    def _get_basket(self, vol):
        # определяем номер basket по vol (скопировал из другого парсера)
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
        return "17"  # по умолчанию

    def _get_images(self, article, count=10):
        vol = article // 100000
        part = article // 1000
        basket = self._get_basket(vol)
        base = f"https://basket-{basket}.wbbasket.ru/vol{vol}/part{part}/{article}/images/big"
        return [f"{base}/{i}.webp" for i in range(1, count + 1)]

    def _parse_sizes(self, sizes_data):
        # парсим размеры и считаем остатки
        total = 0
        names = []
        for size_item in sizes_data:
            # может быть origName или name
            size_name = size_item.get("origName") or size_item.get("name", "")
            if size_name and size_name not in names:
                names.append(size_name)
            # остатки по складам
            stocks_list = size_item.get("stocks", [])
            for stock_item in stocks_list:
                qty = stock_item.get("qty", 0)
                total = total + qty  # просто суммируем
        return names, total

    def _product_from_item(self, item):
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

    def search(self, query, max_pages=None):
        """Поиск товаров."""
        pages = max_pages or MAX_PAGES
        products = []
        
        # небольшая задержка перед началом (чтобы не палиться)
        delay = random.uniform(1.0, 2.0)
        time.sleep(delay)
        
        for page in range(1, pages + 1):
            logger.info(f"Страница {page}/{pages}...")
            
            params = {
                "ab_testing": "false",
                "appType": "1",
                "curr": "rub",
                "dest": "-1257786",
                "page": page,
                "query": query,
                "resultset": "catalog",
                "sort": "popular",
                "spp": "30",
            }
            
            data = self._request(SEARCH_URL, params, cache_prefix=f"search_{query}")
            if not data:
                logger.warning(f"Страница {page} не загружена")
                break
            
            items = data.get("data", {}).get("products", [])
            if not items:
                logger.info("Пусто, конец")
                break
            
            logger.info(f"Найдено: {len(items)}")
            for item in items:
                products.append(self._product_from_item(item))
            
            if page < pages:
                self._sleep(DELAY_BETWEEN_PAGES)
        
        return products

    def get_card(self, article):
        """Карточка товара."""
        vol = article // 100000
        part = article // 1000
        basket = self._get_basket(vol)
        url = f"https://basket-{basket}.wbbasket.ru/vol{vol}/part{part}/{article}/info/ru/card.json"
        return self._request(url, cache_prefix=f"card_{article}") or {}

    def enrich(self, product):
        """Обогащаем данные."""
        card = self.get_card(product.article)
        if card:
            product.description = card.get("description", "")
            
            for opt in card.get("options", []):
                name = opt.get("name", "")
                value = opt.get("value", "")
                if name and value:
                    product.characteristics[name] = value
                    if "страна" in name.lower():
                        product.country = value
            
            comps = card.get("compositions", [])
            if comps:
                comp_str = "; ".join(f"{c['name']}: {c['value']}" for c in comps if c.get("name"))
                if comp_str:
                    product.characteristics["Состав"] = comp_str
        
        return product

    def _enrich_worker(self, product):
        self._sleep(DELAY_BETWEEN_PRODUCTS)
        return self.enrich(product)

    def parse_all(self, query, max_pages=None, enrich=True, parallel=True):
        """Полный парсинг."""
        products = self.search(query, max_pages)
        logger.info(f"Найдено: {len(products)}")
        
        if not enrich or not products:
            return products
        
        logger.info("Обогащение...")
        
        if parallel and self.max_workers > 1:
            enriched = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(self._enrich_worker, p): i for i, p in enumerate(products)}
                
                for i, future in enumerate(as_completed(futures), 1):
                    try:
                        p = future.result()
                        enriched.append((futures[future], p))
                    except Exception as e:
                        idx = futures[future]
                        logger.error(f"Ошибка {idx}: {e}")
                        enriched.append((idx, products[idx]))
                    
                    if i % 20 == 0:
                        logger.info(f"Обогащено {i}/{len(products)}")
            
            enriched.sort(key=lambda x: x[0])
            products = [p for _, p in enriched]
        else:
            for i, p in enumerate(products, 1):
                self.enrich(p)
                self._sleep(DELAY_BETWEEN_PRODUCTS)
                if i % 20 == 0:
                    logger.info(f"Обогащено {i}/{len(products)}")
        
        logger.info(f"Готово: {len(products)}")
        return products
