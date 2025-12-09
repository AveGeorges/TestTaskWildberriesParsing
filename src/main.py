"""Парсер каталога Wildberries."""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from src.cache import clear_cache
from src.config import DEFAULT_FILTER
from src.excel_writer import save_xlsx, save_filtered


def setup_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Парсер WB")
    
    parser.add_argument("-q", "--query", default="пальто из натуральной шерсти",
                        help="Поисковый запрос")
    parser.add_argument("-p", "--pages", type=int, default=10,
                        help="Кол-во страниц")
    parser.add_argument("-o", "--output", default="output",
                        help="Папка для результатов")
    parser.add_argument("-w", "--workers", type=int, default=5,
                        help="Потоки (для httpx режима)")
    
    parser.add_argument("--no-enrich", action="store_true",
                        help="Без обогащения данных")
    parser.add_argument("--no-parallel", action="store_true",
                        help="Без многопоточности")
    parser.add_argument("--no-cache", action="store_true",
                        help="Без кэша")
    parser.add_argument("--clear-cache", action="store_true",
                        help="Очистить кэш")
    
    parser.add_argument("--browser", action="store_true",
                        help="Режим браузера (Playwright)")
    parser.add_argument("--show-browser", action="store_true",
                        help="Показать окно браузера")
    parser.add_argument("--proxy", help="Прокси (http://...)")
    
    parser.add_argument("-v", "--verbose", action="store_true")
    
    parser.add_argument("--min-rating", type=float, default=DEFAULT_FILTER["min_rating"])
    parser.add_argument("--max-price", type=int, default=DEFAULT_FILTER["max_price"])
    parser.add_argument("--country", default=DEFAULT_FILTER["country"])
    
    return parser.parse_args()


def main():
    args = parse_args()
    setup_logging(args.verbose)
    
    logger = logging.getLogger(__name__)
    
    if args.clear_cache:
        logger.info("Очистка кэша...")
        clear_cache()
    
    logger.info("=" * 60)
    logger.info("ПАРСЕР WILDBERRIES")
    logger.info("=" * 60)
    logger.info(f"Запрос: '{args.query}'")
    logger.info(f"Страниц: {args.pages}")
    logger.info(f"Кэш: {'нет' if args.no_cache else 'да'}")
    logger.info(f"Обогащение: {'нет' if args.no_enrich else 'да'}")
    
    if args.browser:
        logger.info(f"Режим: браузер")
        logger.info(f"Headless: {'нет' if args.show_browser else 'да'}")
    else:
        logger.info(f"Режим: HTTP")
        if args.proxy:
            logger.info(f"Прокси: {args.proxy[:30]}...")
    logger.info("=" * 60)
    
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_path = out_dir / f"catalog_full_{ts}.xlsx"
    filtered_path = out_dir / f"catalog_filtered_{ts}.xlsx"
    
    try:
        # выбираем парсер в зависимости от режима
        if args.browser:
            from src.wb_browser import WBBrowserParser
            parser = WBBrowserParser(
                use_cache=not args.no_cache,
                headless=not args.show_browser,
            )
        else:
            # HTTP режим (может блокироваться)
            from src.wb_parser import WildberriesParser
            parser = WildberriesParser(
                use_cache=not args.no_cache,
                max_workers=args.workers,
                proxy=args.proxy,
            )
        
        with parser:
            logger.info("Парсинг...")
            start = datetime.now()
            
            if args.browser:
                products = parser.parse(
                    args.query,
                    max_pages=args.pages,
                    enrich=not args.no_enrich,
                )
            else:
                products = parser.parse_all(
                    args.query,
                    max_pages=args.pages,
                    enrich=not args.no_enrich,
                    parallel=not args.no_parallel,
                )
            
            elapsed = datetime.now() - start
            logger.info(f"Время: {elapsed}")
            
            if not products:
                logger.warning("Ничего не найдено")
                return 1
            
            logger.info(f"Найдено: {len(products)}")
            
            save_xlsx(products, full_path)
            logger.info(f"Полный каталог: {full_path}")
            
            def check_filter(p):
                return p.matches_filter(
                    min_rating=args.min_rating,
                    max_price=args.max_price,
                    country=args.country,
                )
            
            filtered_count = save_filtered(products, filtered_path, check_filter)
            logger.info(f"Отфильтровано: {filtered_path} ({filtered_count} шт.)")
            
            logger.info("=" * 60)
            logger.info("ИТОГО")
            logger.info(f"  Всего: {len(products)}")
            logger.info(f"  Фильтр: {filtered_count}")
            logger.info(f"  Время: {elapsed}")
            logger.info(f"  Фильтр: рейтинг>={args.min_rating}, цена<={args.max_price}, страна={args.country}")
            logger.info("=" * 60)
            
    except KeyboardInterrupt:
        logger.info("Прервано (Ctrl+C)")
        return 130
    except Exception as e:
        logger.exception(f"Ошибка: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
