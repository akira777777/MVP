"""
Скрипт для поиска малого бизнеса в Праге и экспорта в Excel.
Собирает: телефоны, email, имена и фамилии владельцев.
"""

import asyncio
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
from pydantic import BaseModel, Field

from utils.lead_generation.collector import BusinessCollector
from utils.lead_generation.config import ScraperConfig
from utils.lead_generation.google_maps_api_client import GoogleMapsAPIClient
from utils.lead_generation.models import BusinessData
from utils.lead_generation.utils import BUSINESS_CATEGORIES, PRAGUE_DISTRICTS
from utils.logging_config import setup_logging

# Initialize logger
logger = setup_logging(
    name=__name__, log_level="INFO", log_file="prague_small_businesses.log", log_dir="logs"
)


class BusinessWithOwner(BaseModel):
    """Модель бизнеса с информацией о владельце."""

    business_name: str = Field(..., description="Название бизнеса")
    address: Optional[str] = Field(None, description="Адрес")
    phone: Optional[str] = Field(None, description="Телефон")
    email: Optional[str] = Field(None, description="Email")
    website: Optional[str] = Field(None, description="Веб-сайт")
    owner_first_name: Optional[str] = Field(None, description="Имя владельца")
    owner_last_name: Optional[str] = Field(None, description="Фамилия владельца")
    owner_full_name: Optional[str] = Field(None, description="Полное имя владельца")
    category: Optional[str] = Field(None, description="Категория бизнеса")
    district: Optional[str] = Field(None, description="Район Праги")


class PragueSmallBusinessCollector:
    """Коллектор малого бизнеса в Праге с информацией о владельцах."""

    def __init__(self, api_key: Optional[str] = None, output_dir: str = "leads"):
        """
        Инициализация коллектора.

        Args:
            api_key: Google Maps API ключ (опционально, берется из env если не указан)
            output_dir: Директория для сохранения результатов
        """
        config = ScraperConfig()
        if api_key:
            config.api_key = api_key

        self.api_client = GoogleMapsAPIClient(config) if config.api_key else None
        self.collector = BusinessCollector(api_key=api_key or config.api_key)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Browser scraper для поиска информации о владельцах (опционально)
        self.browser_scraper = None
        try:
            from playwright.async_api import async_playwright

            self.has_playwright = True
        except ImportError:
            self.has_playwright = False
            logger.warning("Playwright не установлен. Поиск владельцев на сайтах будет ограничен.")

    def _parse_czech_phone(self, text: str) -> Optional[str]:
        """Извлечь чешский телефонный номер из текста."""
        if not text:
            return None

        # Паттерны чешских телефонов
        patterns = [
            r"\+420\s?\d{3}\s?\d{3}\s?\d{3}",  # +420 XXX XXX XXX
            r"420\s?\d{3}\s?\d{3}\s?\d{3}",  # 420 XXX XXX XXX
            r"\d{3}\s?\d{3}\s?\d{3}",  # XXX XXX XXX
            r"\(\+420\)\s?\d{3}\s?\d{3}\s?\d{3}",  # (+420) XXX XXX XXX
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                phone = match.group(0)
                # Нормализация
                phone = re.sub(r"\s+", "", phone)
                if not phone.startswith("+"):
                    if phone.startswith("420"):
                        phone = "+" + phone
                    else:
                        phone = "+420" + phone
                return phone

        return None

    def _parse_email(self, text: str) -> Optional[str]:
        """Извлечь email из текста."""
        if not text:
            return None
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        match = re.search(email_pattern, text)
        if match:
            return match.group(0).lower()
        return None

    def _parse_czech_name(self, text: str) -> Optional[Dict[str, str]]:
        """
        Извлечь чешское имя из текста.
        Возвращает dict с 'first_name', 'last_name', 'full_name'.
        """
        if not text:
            return None

        # Паттерны для поиска имен владельцев
        owner_patterns = [
            r"(?:Majitel|Vlastník|Ředitel|Statutární|Owner|Manager|Director)[:\s]+([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+(?:\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+)+)",
            r"([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+(?:\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+)+)\s+(?:je|je to|je toto)\s+(?:majitel|vlastník|ředitel)",
            r"([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+(?:\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+)+)",  # Просто имя с заглавной буквы
        ]

        for pattern in owner_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                full_name = match.group(1).strip()
                # Разделить на имя и фамилию
                name_parts = full_name.split()
                if len(name_parts) >= 2:
                    # Обычно имя(имена) затем фамилия
                    first_name = " ".join(name_parts[:-1])
                    last_name = name_parts[-1]
                    return {
                        "first_name": first_name,
                        "last_name": last_name,
                        "full_name": full_name,
                    }
                elif len(name_parts) == 1:
                    return {
                        "first_name": name_parts[0],
                        "last_name": "",
                        "full_name": full_name,
                    }

        return None

    async def _find_owner_from_website(self, website_url: str) -> Optional[Dict[str, str]]:
        """
        Найти информацию о владельце, скрапя сайт бизнеса.

        Args:
            website_url: URL сайта бизнеса

        Returns:
            Dict с информацией о владельце или None
        """
        if not website_url or not website_url.startswith(("http://", "https://")):
            return None

        if not self.has_playwright:
            return None

        logger.info(f"Поиск владельца на сайте: {website_url}")

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                try:
                    await page.goto(website_url, timeout=10000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(2000)  # Ждем загрузки контента

                    # Получить весь текст страницы
                    page_text = await page.content()

                    # Поиск на странице "О нас", "Kontakt", "Team"
                    pages_to_check = [
                        "/o-nas",
                        "/about",
                        "/kontakt",
                        "/contact",
                        "/tym",
                        "/team",
                        "/majitel",
                        "/vlastnik",
                    ]

                    # Проверяем главную страницу
                    owner_info = self._parse_czech_name(page_text)
                    if owner_info:
                        await browser.close()
                        return owner_info

                    # Проверяем дополнительные страницы
                    for page_path in pages_to_check:
                        try:
                            page_url = website_url.rstrip("/") + page_path
                            await page.goto(page_url, timeout=5000, wait_until="domcontentloaded")
                            await page.wait_for_timeout(1000)
                            page_text = await page.content()
                            owner_info = self._parse_czech_name(page_text)
                            if owner_info:
                                logger.info(f"Найден владелец на {page_path}: {owner_info['full_name']}")
                                await browser.close()
                                return owner_info
                        except Exception:
                            continue

                    await browser.close()
                except Exception as e:
                    logger.debug(f"Ошибка при скрапинге {website_url}: {e}")
                    await browser.close()

        except Exception as e:
            logger.debug(f"Ошибка при поиске владельца на сайте {website_url}: {e}")

        return None

    async def _enrich_business_with_owner(
        self, business: BusinessData, category: str
    ) -> BusinessWithOwner:
        """
        Обогатить данные бизнеса информацией о владельце.

        Args:
            business: Данные бизнеса
            category: Категория бизнеса

        Returns:
            BusinessWithOwner объект
        """
        # Создаем базовый объект
        enriched = BusinessWithOwner(
            business_name=business.name,
            address=business.address,
            phone=self._parse_czech_phone(business.phone) if business.phone else None,
            email=None,  # Будет заполнено позже
            website=str(business.website) if business.website else None,
            category=category,
            district=business.district,
        )

        # Пытаемся найти email на сайте
        if enriched.website:
            try:
                owner_info = await self._find_owner_from_website(enriched.website)
                if owner_info:
                    enriched.owner_first_name = owner_info.get("first_name")
                    enriched.owner_last_name = owner_info.get("last_name")
                    enriched.owner_full_name = owner_info.get("full_name")

                # Пытаемся найти email на сайте
                if self.has_playwright:
                    try:
                        from playwright.async_api import async_playwright

                        async with async_playwright() as p:
                            browser = await p.chromium.launch(headless=True)
                            page = await browser.new_page()
                            try:
                                await page.goto(enriched.website, timeout=10000)
                                await page.wait_for_timeout(2000)
                                page_text = await page.content()
                                email = self._parse_email(page_text)
                                if email:
                                    enriched.email = email
                            except Exception:
                                pass
                            finally:
                                await browser.close()
                    except Exception:
                        pass
            except Exception as e:
                logger.debug(f"Ошибка при обогащении данных для {business.name}: {e}")

        return enriched

    async def collect_small_businesses(
        self,
        categories: Optional[List[str]] = None,
        max_per_category: int = 30,
        districts: Optional[List[str]] = None,
    ) -> List[BusinessWithOwner]:
        """
        Собрать данные о малом бизнесе в Праге.

        Args:
            categories: Список категорий для поиска (по умолчанию все из BUSINESS_CATEGORIES)
            max_per_category: Максимум результатов на категорию
            districts: Список районов для поиска (по умолчанию все)

        Returns:
            Список BusinessWithOwner объектов
        """
        if categories is None:
            # Используем все категории из BUSINESS_CATEGORIES
            categories = []
            for cat_terms in BUSINESS_CATEGORIES.values():
                categories.extend(cat_terms[:2])  # Берем первые 2 термина из каждой категории

        if districts is None:
            districts = PRAGUE_DISTRICTS

        all_businesses = []
        prague_center = (50.0755, 14.4378)

        total_searches = len(categories) * len(districts)
        current_search = 0

        for category in categories:
            for district in districts:
                current_search += 1
                query = f"{category} {district}"
                logger.info(f"[{current_search}/{total_searches}] Поиск: {query}")
                print(f"[{current_search}/{total_searches}] Поиск: {query}...")

                try:
                    # Используем API клиент для поиска
                    if self.api_client:
                        location_dict = {
                            "latitude": prague_center[0],
                            "longitude": prague_center[1],
                        }
                        businesses = await self.api_client.search_businesses(
                            query, location_dict, max_per_category
                        )

                        # Обогащаем данными о владельцах
                        for business in businesses:
                            try:
                                enriched = await self._enrich_business_with_owner(
                                    business, category
                                )
                                all_businesses.append(enriched)

                                # Выводим прогресс
                                owner_info = (
                                    enriched.owner_full_name
                                    if enriched.owner_full_name
                                    else "не найден"
                                )
                                phone_info = "✓" if enriched.phone else "✗"
                                email_info = "✓" if enriched.email else "✗"
                                print(
                                    f"  ✓ {enriched.business_name} "
                                    f"(Владелец: {owner_info}, Телефон: {phone_info}, Email: {email_info})"
                                )

                                # Rate limiting
                                await asyncio.sleep(1)
                            except Exception as e:
                                logger.error(f"Ошибка при обогащении {business.name}: {e}")
                                continue

                except Exception as e:
                    logger.error(f"Ошибка при поиске '{query}': {e}")
                    continue

        return all_businesses

    def save_to_excel(
        self, businesses: List[BusinessWithOwner], filename: Optional[str] = None
    ) -> Path:
        """
        Сохранить бизнесы в Excel файл.

        Args:
            businesses: Список BusinessWithOwner объектов
            filename: Имя файла (автогенерируется если не указано)

        Returns:
            Путь к сохраненному Excel файлу
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if not filename:
            filename = f"prague_small_businesses_{timestamp}.xlsx"
        filepath = self.output_dir / filename

        # Подготовка данных для Excel
        excel_data = []
        for business in businesses:
            excel_data.append(
                {
                    "Название бизнеса": business.business_name,
                    "Телефон": business.phone or "",
                    "Email": business.email or "",
                    "Имя владельца": business.owner_first_name or "",
                    "Фамилия владельца": business.owner_last_name or "",
                    "Полное имя владельца": business.owner_full_name or "",
                    "Адрес": business.address or "",
                    "Район": business.district or "",
                    "Веб-сайт": business.website or "",
                    "Категория": business.category or "",
                }
            )

        # Создаем DataFrame
        df = pd.DataFrame(excel_data)

        # Сохраняем в Excel
        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Малый бизнес Праги")

            # Автоподгонка ширины колонок
            worksheet = writer.sheets["Малый бизнес Праги"]
            from openpyxl.utils import get_column_letter

            for idx, col in enumerate(df.columns, 1):
                max_length = max(
                    df[col].astype(str).map(len).max(),
                    len(str(col)),
                )
                column_letter = get_column_letter(idx)
                worksheet.column_dimensions[column_letter].width = min(
                    max_length + 2, 50
                )

        logger.info(f"Сохранено {len(businesses)} бизнесов в {filepath}")
        return filepath


async def main():
    """Главная функция для CLI использования."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Сбор данных о малом бизнесе в Праге и экспорт в Excel"
    )
    parser.add_argument(
        "--categories",
        nargs="+",
        default=None,
        help="Категории бизнеса для поиска (по умолчанию: все основные категории)",
    )
    parser.add_argument(
        "--max-per-category",
        type=int,
        default=30,
        help="Максимум результатов на категорию (по умолчанию: 30)",
    )
    parser.add_argument(
        "--districts",
        nargs="+",
        default=None,
        help="Районы Праги для поиска (по умолчанию: все районы)",
    )
    parser.add_argument(
        "--output-dir",
        default="leads",
        help="Директория для сохранения результатов",
    )
    parser.add_argument(
        "--output-file",
        help="Имя Excel файла (автогенерируется если не указано)",
    )
    parser.add_argument(
        "--api-key",
        help="Google Maps API ключ (опционально, берется из env если не указан)",
    )

    args = parser.parse_args()

    collector = PragueSmallBusinessCollector(
        api_key=args.api_key, output_dir=args.output_dir
    )

    try:
        # Сбор данных
        print("\n" + "=" * 60)
        print("НАЧАЛО СБОРА ДАННЫХ О МАЛОМ БИЗНЕСЕ В ПРАГЕ")
        print("=" * 60 + "\n")

        businesses = await collector.collect_small_businesses(
            categories=args.categories,
            max_per_category=args.max_per_category,
            districts=args.districts,
        )

        logger.info(f"Найдено {len(businesses)} бизнесов")
        print(f"\n{'=' * 60}")
        print("ОБРАБОТКА ЗАВЕРШЕНА")
        print(f"{'=' * 60}")

        # Сохранение в Excel
        excel_file = collector.save_to_excel(businesses, filename=args.output_file)
        print(f"\n✓ Результаты сохранены в: {excel_file}")

        # Статистика
        businesses_with_phone = sum(1 for b in businesses if b.phone)
        businesses_with_email = sum(1 for b in businesses if b.email)
        businesses_with_owner = sum(1 for b in businesses if b.owner_full_name)

        print("\n📊 СТАТИСТИКА:")
        print(f"  Всего найдено бизнесов: {len(businesses)}")
        if businesses:
            print(
                f"  С телефоном: {businesses_with_phone} ({businesses_with_phone * 100 // len(businesses)}%)"
            )
            print(
                f"  С email: {businesses_with_email} ({businesses_with_email * 100 // len(businesses)}%)"
            )
            print(
                f"  С именем владельца: {businesses_with_owner} ({businesses_with_owner * 100 // len(businesses)}%)"
            )
        print(f"\n{'=' * 60}\n")

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        print(f"\n❌ Ошибка: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
