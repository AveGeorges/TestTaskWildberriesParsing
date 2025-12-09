"""Модели данных."""

import re
from dataclasses import dataclass, field


@dataclass
class Product:
    """Товар WB."""
    
    url: str
    article: int
    name: str
    price: int
    description: str = ""
    images: list[str] = field(default_factory=list)
    characteristics: dict = field(default_factory=dict)
    seller_name: str = ""
    seller_url: str = ""
    sizes: list[str] = field(default_factory=list)
    stock: int = 0
    rating: float = 0.0
    feedbacks_count: int = 0
    brand: str = ""
    country: str = ""
    
    @property
    def price_rub(self):
        return self.price / 100
    
    @property
    def images_str(self):
        return ", ".join(self.images)
    
    @property
    def sizes_str(self):
        return ", ".join(self.sizes)
    
    @property
    def characteristics_str(self):
        return "\n".join(f"{k}: {v}" for k, v in self.characteristics.items())
    
    @property
    def description_clean(self):
        """Убираем HTML теги из описания."""
        if not self.description:
            return ""
        # удаляем все теги
        text = re.sub(r'<[^>]+>', ' ', self.description)
        # заменяем HTML-сущности
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        # убираем лишние пробелы
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def matches_filter(self, min_rating=4.5, max_price=10000, country="Россия"):
        """Проверка фильтра."""
        # если страна не указана - не подходит
        if not self.country:
            return False
        
        # проверяем рейтинг
        if self.rating < min_rating:
            return False
        
        # проверяем цену
        if self.price_rub > max_price:
            return False
        
        # проверяем страну (регистронезависимо)
        country_match = country.lower() in self.country.lower()
        if not country_match:
            return False
        
        return True
