#!/usr/bin/env python3
"""
Скрипт для поиска малого бизнеса во Франции и экспорта в Excel.

Использует Google Maps API для поиска бизнеса и пытается найти информацию
о владельцах через веб-скрапинг.

Использование:
    python scripts/france_business_scraper.py --categories "restaurant" "salon" --location "Paris, France" --max-results 50
"""

import asyncio
import argparse
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
import pandas as pd

from utils.lead_generation.google_maps import GoogleMapsClient
from scripts.browser_scraper import BrowserScraper
from utils.logging_config import setup_logging
from config import settings

logger = setup_logging(
    name=__name__, log_level="INFO", log_file="france_business_scraper.log", log_dir="logs"
)


class OwnerInfo(BaseModel):
    """Информация о владельце бизнеса."""
    first_name: Optional[str] = Field(None, description="Имя")
    last_name: Optional[str] = Field(None, description="Фамилия")
    full_name: Optional[str] = Field(None, description="Полное имя")
    role: Optional[str] = Field(None, description="Роль (directeur, gérant, etc.)")


class FrenchBusiness(BaseModel):
    """Информация о французском бизнесе."""
    business_name: str = Field(..., description="Название бизнеса")
    address: Optional[str] = Field(None, description="Адрес")
    phone: Optional[str] = Field(None, description="Телефон")
    email: Optional[str] = Field(None, description="Email")
    website: Optional[str] = Field(None, description="Веб-сайт")
    category: Optional[str] = Field(None, description="Категория бизнеса")
    google_maps_url: Optional[str] = Field(None, description="URL Google Maps")
    owner: Optional[OwnerInfo] = Field(None, description="Информация о владельце")
    siret: Optional[str] = Field(None, description="SIRET номер (если найден)")


class FrenchBusinessScraper:
    """Скрапер для поиска французского бизнеса и информации о владельцах."""

    def __init__(
        self,
        google_maps_api_key: Optional[str] = None,
        use_browser_scraper: bool = True,
    ):
        """
        Инициализация скрапера.

        Args:
            google_maps_api_key: Google Maps API ключ (по умолчанию из settings)
            use_browser_scraper: Использовать браузерный скрапер для поиска владельцев
        """
        self.google_maps = GoogleMapsClient(
            api_key=google_maps_api_key or settings.google_maps_api_key,
            browser_scraper=None,  # Инициализируем позже если нужно
        )
        self.browser_scraper = None
        if use_browser_scraper:
            try:
                self.browser_scraper = BrowserScraper(use_mcp_puppeteer=True)
                logger.info("Browser scraper initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize browser scraper: {e}")
        
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )

    async def close(self):
        """Закрыть все клиенты."""
        await self.google_maps.close()
        await self.http_client.aclose()
        if self.browser_scraper:
            await self.browser_scraper.close()

    async def search_businesses(
        self,
        categories: List[str],
        location: str = "Paris, France",
        max_results: int = 50,
    ) -> List[FrenchBusiness]:
        """
        Поиск бизнеса через Google Maps.

        Args:
            categories: Список категорий для поиска
            location: Локация для поиска
            max_results: Максимальное количество результатов на категорию

        Returns:
            Список найденных бизнесов
        """
        all_businesses = []

        for category in categories:
            logger.info(f"Поиск '{category}' в {location}...")

            try:
                # Поиск через Google Maps
                places = await self.google_maps.search_businesses(
                    query=category,
                    location=location,
                    max_results=max_results,
                )

                logger.info(f"Найдено {len(places)} мест для '{category}'")

                # Обработка каждого места
                for place_data in places:
                    try:
                        business = await self._process_place(place_data, category)
                        if business:
                            all_businesses.append(business)
                            logger.info(
                                f"✓ Обработан: {business.business_name} "
                                f"(телефон: {business.phone or 'N/A'}, "
                                f"владелец: {business.owner.full_name if business.owner else 'N/A'})"
                            )

                        # Rate limiting
                        await asyncio.sleep(1)

                    except Exception as e:
                        logger.error(f"Ошибка обработки места: {e}", exc_info=True)
                        continue

            except Exception as e:
                logger.error(f"Ошибка поиска категории '{category}': {e}", exc_info=True)
                continue

        return all_businesses

    async def _process_place(
        self, place_data: Dict[str, Any], category: str
    ) -> Optional[FrenchBusiness]:
        """
        Обработать данные места из Google Maps.

        Args:
            place_data: Данные места из Google Maps API
            category: Категория бизнеса

        Returns:
            FrenchBusiness объект или None
        """
        # Парсинг данных Google Maps
        parsed = self.google_maps.parse_place_data(place_data)

        # Создание базового объекта бизнеса
        business = FrenchBusiness(
            business_name=parsed.get("business_name", ""),
            address=parsed.get("google_address"),
            phone=parsed.get("google_phone"),
            website=parsed.get("google_website"),
            category=category,
            google_maps_url=parsed.get("google_maps_url"),
        )

        # Попытка найти информацию о владельце
        owner = await self._find_owner(business)
        if owner:
            business.owner = owner

        # Попытка найти email адрес
        if not business.email and business.website:
            email = await self._find_email(business.website)
            if email:
                business.email = email

        return business

    async def _find_owner(self, business: FrenchBusiness) -> Optional[OwnerInfo]:
        """
        Попытка найти информацию о владельце бизнеса.

        Использует несколько методов:
        1. Поиск на сайте компании
        2. Поиск в французских бизнес-реестрах (Infogreffe, Pappers)
        3. Поиск по SIRET номеру

        Args:
            business: Информация о бизнесе

        Returns:
            OwnerInfo или None
        """
        # Метод 1: Поиск на сайте компании
        if business.website:
            try:
                owner = await self._scrape_owner_from_website(business.website)
                if owner:
                    logger.debug(f"Найден владелец на сайте {business.website}: {owner.full_name}")
                    return owner
            except Exception as e:
                logger.debug(f"Не удалось найти владельца на сайте {business.website}: {e}")

        # Метод 2: Поиск по названию компании в реестрах
        if business.business_name:
            try:
                owner = await self._search_owner_in_registries(business.business_name, business.address)
                if owner:
                    logger.debug(f"Найден владелец в реестрах: {owner.full_name}")
                    return owner
            except Exception as e:
                logger.debug(f"Не удалось найти владельца в реестрах: {e}")

        return None

    async def _scrape_owner_from_website(self, website_url: str) -> Optional[OwnerInfo]:
        """
        Поиск информации о владельце на сайте компании.

        Args:
            website_url: URL сайта компании

        Returns:
            OwnerInfo или None
        """
        try:
            # Нормализация URL
            if not website_url.startswith(("http://", "https://")):
                website_url = f"https://{website_url}"

            # Получение страницы
            response = await self.http_client.get(website_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Поиск ключевых слов, указывающих на владельца
            owner_keywords = [
                "directeur",
                "gérant",
                "fondateur",
                "propriétaire",
                "owner",
                "founder",
                "director",
                "manager",
            ]

            # Поиск в тексте страницы
            text = soup.get_text().lower()

            # Поиск имен рядом с ключевыми словами
            for keyword in owner_keywords:
                pattern = rf"{keyword}[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    full_name = matches[0].strip()
                    # Разделение на имя и фамилию
                    name_parts = full_name.split()
                    if len(name_parts) >= 2:
                        return OwnerInfo(
                            first_name=name_parts[0],
                            last_name=" ".join(name_parts[1:]),
                            full_name=full_name,
                            role=keyword,
                        )
                    elif len(name_parts) == 1:
                        return OwnerInfo(
                            full_name=full_name,
                            role=keyword,
                        )

            # Поиск в мета-тегах
            meta_tags = soup.find_all("meta", {"name": re.compile(r"author|owner|director", re.I)})
            for meta in meta_tags:
                content = meta.get("content", "")
                if content and len(content.split()) >= 2:
                    name_parts = content.split()
                    return OwnerInfo(
                        first_name=name_parts[0],
                        last_name=" ".join(name_parts[1:]),
                        full_name=content,
                    )

        except Exception as e:
            logger.debug(f"Ошибка скрапинга сайта {website_url}: {e}")

        return None

    async def _search_owner_in_registries(
        self, business_name: str, address: Optional[str] = None
    ) -> Optional[OwnerInfo]:
        """
        Поиск владельца в французских бизнес-реестрах.

        Примечание: Infogreffe и Pappers требуют платную подписку для API доступа.
        Здесь используется базовый веб-скрапинг, который может быть ограничен.

        Args:
            business_name: Название компании
            address: Адрес компании (опционально)

        Returns:
            OwnerInfo или None
        """
        # Попытка поиска через Infogreffe (базовый скрапинг)
        # Внимание: это может нарушать ToS некоторых сайтов
        # В продакшене рекомендуется использовать официальные API

        try:
            # Поиск через Pappers (если доступен)
            # URL: https://www.pappers.fr/recherche?q={business_name}
            search_url = f"https://www.pappers.fr/recherche?q={business_name.replace(' ', '+')}"
            
            response = await self.http_client.get(search_url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Поиск информации о директоре/владельце
                # Структура может меняться, поэтому это базовый пример
                director_elements = soup.find_all(text=re.compile(r"gérant|directeur", re.I))
                for elem in director_elements:
                    parent = elem.parent
                    if parent:
                        text = parent.get_text()
                        # Попытка извлечь имя
                        name_match = re.search(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", text)
                        if name_match:
                            full_name = name_match.group(1)
                            name_parts = full_name.split()
                            if len(name_parts) >= 2:
                                return OwnerInfo(
                                    first_name=name_parts[0],
                                    last_name=" ".join(name_parts[1:]),
                                    full_name=full_name,
                                    role="gérant",
                                )

        except Exception as e:
            logger.debug(f"Ошибка поиска в реестрах: {e}")

        return None

    async def _find_email(self, website_url: str) -> Optional[str]:
        """
        Поиск email адреса на сайте компании.

        Args:
            website_url: URL сайта компании

        Returns:
            Email адрес или None
        """
        try:
            # Нормализация URL
            if not website_url.startswith(("http://", "https://")):
                website_url = f"https://{website_url}"

            # Получение страницы
            response = await self.http_client.get(website_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Поиск email в тексте страницы
            text = response.text
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, text)

            # Фильтрация общих email адресов
            excluded_domains = [
                'example.com', 'test.com', 'domain.com', 'email.com',
                'sentry.io', 'google.com', 'facebook.com', 'twitter.com',
                'linkedin.com', 'instagram.com', 'youtube.com'
            ]

            for email in emails:
                email_lower = email.lower()
                # Проверка, что это не общий email
                if not any(domain in email_lower for domain in excluded_domains):
                    # Проверка, что это не изображение или другой медиа файл
                    if not email_lower.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
                        return email

            # Поиск в ссылках mailto:
            mailto_links = soup.find_all('a', href=re.compile(r'^mailto:'))
            for link in mailto_links:
                email = link.get('href', '').replace('mailto:', '').strip()
                if email and '@' in email:
                    return email.split('?')[0]  # Убрать параметры после ?

        except Exception as e:
            logger.debug(f"Ошибка поиска email на сайте {website_url}: {e}")

        return None

    def export_to_excel(
        self,
        businesses: List[FrenchBusiness],
        output_path: Path,
    ) -> Path:
        """
        Экспорт бизнесов в Excel файл.

        Args:
            businesses: Список бизнесов для экспорта
            output_path: Путь к выходному Excel файлу

        Returns:
            Путь к созданному файлу
        """
        # Подготовка данных для DataFrame
        data = []
        for business in businesses:
            owner = business.owner
            data.append({
                "Название бизнеса": business.business_name,
                "Адрес": business.address or "",
                "Телефон": business.phone or "",
                "Email": business.email or "",
                "Веб-сайт": business.website or "",
                "Категория": business.category or "",
                "Имя владельца": owner.first_name if owner else "",
                "Фамилия владельца": owner.last_name if owner else "",
                "Полное имя владельца": owner.full_name if owner else "",
                "Роль владельца": owner.role if owner else "",
                "SIRET": business.siret or "",
                "Google Maps URL": business.google_maps_url or "",
            })

        # Создание DataFrame
        df = pd.DataFrame(data)

        # Создание директории если не существует
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Экспорт в Excel
        df.to_excel(output_path, index=False, engine="openpyxl")

        logger.info(f"Экспортировано {len(businesses)} бизнесов в {output_path}")
        return output_path


async def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(
        description="Поиск малого бизнеса во Франции и экспорт в Excel"
    )
    parser.add_argument(
        "--categories",
        nargs="+",
        default=["restaurant", "salon de beauté", "coiffeur"],
        help="Категории бизнеса для поиска",
    )
    parser.add_argument(
        "--location",
        default="Paris, France",
        help="Локация для поиска",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=50,
        help="Максимальное количество результатов на категорию",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Путь к выходному Excel файлу (по умолчанию: data/france_businesses_YYYYMMDD_HHMMSS.xlsx)",
    )

    args = parser.parse_args()

    # Определение пути к выходному файлу
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = Path("data") / f"france_businesses_{timestamp}.xlsx"

    scraper = FrenchBusinessScraper()

    try:
        logger.info(f"Начало поиска бизнеса во Франции...")
        logger.info(f"Категории: {args.categories}")
        logger.info(f"Локация: {args.location}")
        logger.info(f"Максимум результатов на категорию: {args.max_results}")

        # Поиск бизнеса
        businesses = await scraper.search_businesses(
            categories=args.categories,
            location=args.location,
            max_results=args.max_results,
        )

        logger.info(f"Найдено {len(businesses)} бизнесов")

        # Экспорт в Excel
        output_file = scraper.export_to_excel(businesses, args.output)

        print(f"\n✓ Готово!")
        print(f"✓ Найдено бизнесов: {len(businesses)}")
        print(f"✓ Файл сохранен: {output_file}")
        
        # Статистика
        businesses_with_owner = sum(1 for b in businesses if b.owner)
        businesses_with_phone = sum(1 for b in businesses if b.phone)
        businesses_with_email = sum(1 for b in businesses if b.email)
        
        print(f"\nСтатистика:")
        print(f"  - С информацией о владельце: {businesses_with_owner}")
        print(f"  - С телефоном: {businesses_with_phone}")
        print(f"  - С email: {businesses_with_email}")

    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
