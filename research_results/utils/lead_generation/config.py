"""
Configuration settings for Google Maps scraper.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


def load_api_key() -> Optional[str]:
    """
    Load Google Maps API key from various sources.

    Checks in order:
    1. Environment variable GOOGLE_MAPS_API_KEY
    2. .env file in project root
    3. config.json in project root

    Returns:
        API key or None if not found
    """
    # 1. Check environment variable
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if api_key:
        return api_key

    # 2. Check .env file
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GOOGLE_MAPS_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if api_key:
                            return api_key
        except Exception:
            pass

    # 3. Check config.json
    config_file = project_root / "config.json"
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                api_key = config.get("google_maps_api_key") or config.get(
                    "GOOGLE_MAPS_API_KEY"
                )
                if api_key:
                    return api_key
        except Exception:
            pass

    return None


def load_here_api_key() -> Optional[str]:
    """
    Load HERE API key from various sources.

    Checks in order:
    1. Environment variable HERE_API_KEY
    2. .env file in project root
    3. config.json in project root

    Returns:
        API key or None if not found
    """
    # 1. Check environment variable
    api_key = os.getenv("HERE_API_KEY")
    if api_key:
        return api_key

    # 2. Check .env file
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("HERE_API_KEY="):
                        api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if api_key:
                            return api_key
        except Exception:
            pass

    # 3. Check config.json
    config_file = project_root / "config.json"
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                api_key = config.get("here_api_key") or config.get("HERE_API_KEY")
                if api_key:
                    return api_key
        except Exception:
            pass

    return None


@dataclass
class ScraperConfig:
    """Конфигурация для операций скрапинга Google Maps."""

    # API ключи
    api_key: Optional[str] = field(
        default_factory=load_api_key
    )  # Google Maps API ключ (автоматически загружается из env)
    here_api_key: Optional[str] = field(
        default_factory=load_here_api_key
    )  # HERE API ключ (альтернатива Google Maps, автоматически загружается из env)

    # Задержки между запросами
    min_delay_seconds: float = 2.0  # Минимальная задержка между запросами
    max_delay_seconds: float = 5.0  # Максимальная задержка между запросами

    # Таймауты
    page_load_timeout: int = 30  # Таймаут загрузки страницы (секунды)
    element_wait_timeout: int = 10  # Таймаут ожидания элемента (секунды)

    # Ограничение частоты запросов
    max_requests_per_hour: int = 100  # Максимум запросов в час
    requests_per_batch: int = 10  # Запросов в батче

    # Настройки браузера
    headless: bool = True  # Запуск браузера в headless режиме
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )  # User-Agent для запросов
    use_stealth: bool = True  # Stealth mode для обхода антибот-защиты
    extract_contacts_from_website: bool = True  # Извлечение контактов с веб-сайтов

    # Параметры поиска
    default_radius_meters: int = 5000  # Радиус поиска по умолчанию (5 км)
    max_results_per_query: int = 20  # Максимум результатов на запрос

    # Настройки повторных попыток
    max_retries: int = 3  # Максимум повторных попыток при ошибке
    retry_delay_base: float = 2.0  # Базовая задержка для экспоненциального backoff

    # Районы Праги для систематического поиска
    prague_districts: List[str] = None

    # Категории бизнесов для поиска
    business_categories: List[str] = None

    def __post_init__(self):
        """Initialize default values if not provided."""
        if self.prague_districts is None:
            self.prague_districts = [
                "Praha 1",
                "Praha 2",
                "Praha 3",
                "Praha 4",
                "Praha 5",
                "Praha 6",
                "Praha 7",
                "Praha 8",
                "Praha 9",
                "Praha 10",
            ]

        if self.business_categories is None:
            self.business_categories = [
                "kavárna",  # café
                "restaurace",  # restaurant
                "kadeřnictví",  # hair salon
                "kosmetika",  # beauty salon
                "obchod",  # shop
                "opravna",  # repair shop
                "úklid",  # cleaning service
                "lékař",  # doctor
                "fitness",  # fitness
                "sport",  # sports
            ]
