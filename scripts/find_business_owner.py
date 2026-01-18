#!/usr/bin/env python3
"""
Скрипт для поиска владельцев бизнеса в Чехии через ARES и торговый реестр.

Использование:
    python scripts/find_business_owner.py --name "Название компании" --address "Адрес"
    python scripts/find_business_owner.py --ico "12345678"
    python scripts/find_business_owner.py --phone "+420123456789"
"""

import asyncio
import argparse
import json
from typing import Optional, Dict, Any

import httpx
from pydantic import BaseModel, Field


class BusinessInfo(BaseModel):
    """Модель информации о бизнесе."""
    name: Optional[str] = None
    ico: Optional[str] = Field(None, alias="IČO")
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    director: Optional[str] = Field(None, alias="statutární_orgán")
    owners: Optional[list[str]] = Field(None, alias="společníci")
    source: Optional[str] = None  # "ARES" или "obchodní_rejstřík"


class ARESClient:
    """Клиент для работы с ARES API."""
    
    BASE_URL = "https://ares.gov.cz"
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
    
    async def search_by_name(self, name: str) -> list[BusinessInfo]:
        """
        Поиск компании по названию через ARES.
        
        Примечание: ARES не предоставляет публичный REST API, поэтому
        этот метод требует веб-скрапинга или использования официального
        SOAP API (если доступен).
        """
        # TODO: Реализовать поиск через веб-интерфейс ARES или SOAP API
        # Пока возвращаем пустой список
        print(f"⚠️  Поиск по названию '{name}' через ARES требует реализации веб-скрапинга")
        return []
    
    async def search_by_ico(self, ico: str) -> Optional[BusinessInfo]:
        """
        Поиск компании по IČO через ARES.
        
        IČO можно проверить через публичный endpoint:
        https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/{ico}
        """
        try:
            url = f"{self.BASE_URL}/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/{ico}"
            response = await self.client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                return BusinessInfo(
                    name=data.get("obchodniJmeno"),
                    ico=ico,
                    address=self._format_address(data),
                    source="ARES"
                )
            elif response.status_code == 404:
                print(f"❌ Компания с IČO {ico} не найдена в ARES")
                return None
            else:
                print(f"⚠️  Ошибка при запросе к ARES: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Ошибка при поиске по IČO: {e}")
            return None
    
    def _format_address(self, data: Dict[str, Any]) -> str:
        """Форматирует адрес из данных ARES."""
        parts = []
        if street := data.get("sidlo", {}).get("nazevUlice"):
            parts.append(street)
        if house_number := data.get("sidlo", {}).get("cisloDomovni"):
            parts.append(house_number)
        if city := data.get("sidlo", {}).get("nazevObce"):
            parts.append(city)
        if psc := data.get("sidlo", {}).get("psc"):
            parts.append(psc)
        return ", ".join(parts) if parts else None
    
    async def close(self):
        """Закрывает HTTP-клиент."""
        await self.client.aclose()


class ObchodniRejstrikClient:
    """Клиент для работы с торговым реестром."""
    
    BASE_URL = "https://or.justice.cz"
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
    
    async def search_by_ico(self, ico: str) -> Optional[BusinessInfo]:
        """
        Поиск компании по IČO в торговом реестре.
        
        Торговый реестр предоставляет веб-интерфейс, но не публичный API.
        Для автоматизации требуется веб-скрапинг или использование
        официального API (если доступен).
        """
        # TODO: Реализовать поиск через веб-интерфейс торгового реестра
        print(f"⚠️  Поиск по IČO '{ico}' в торговом реестре требует реализации веб-скрапинга")
        return None
    
    async def close(self):
        """Закрывает HTTP-клиент."""
        await self.client.aclose()


async def search_business(
    name: Optional[str] = None,
    ico: Optional[str] = None,
    address: Optional[str] = None,
    phone: Optional[str] = None
) -> list[BusinessInfo]:
    """
    Ищет информацию о бизнесе через все доступные источники.
    
    Args:
        name: Название компании
        ico: IČO (идентификационный номер компании)
        address: Адрес компании
        phone: Телефон компании
    
    Returns:
        Список найденной информации о бизнесе
    """
    results = []
    
    ares_client = ARESClient()
    rejstrik_client = ObchodniRejstrikClient()
    
    try:
        # Поиск по IČO (самый надёжный способ)
        if ico:
            print(f"🔍 Поиск по IČO: {ico}")
            ares_result = await ares_client.search_by_ico(ico)
            if ares_result:
                results.append(ares_result)
            
            rejstrik_result = await rejstrik_client.search_by_ico(ico)
            if rejstrik_result:
                results.append(rejstrik_result)
        
        # Поиск по названию
        if name:
            print(f"🔍 Поиск по названию: {name}")
            ares_results = await ares_client.search_by_name(name)
            results.extend(ares_results)
        
        # Поиск по телефону (менее надёжный)
        if phone:
            print(f"⚠️  Поиск по телефону '{phone}' пока не реализован")
        
    finally:
        await ares_client.close()
        await rejstrik_client.close()
    
    return results


def print_results(results: list[BusinessInfo]):
    """Выводит результаты поиска в читаемом формате."""
    if not results:
        print("\n❌ Информация о компании не найдена")
        print("\n💡 Рекомендации:")
        print("   1. Проверьте правильность введённых данных")
        print("   2. Попробуйте поиск вручную через:")
        print("      - ARES: https://ares.gov.cz")
        print("      - Торговый реестр: https://or.justice.cz")
        return
    
    print(f"\n✅ Найдено записей: {len(results)}\n")
    
    for i, info in enumerate(results, 1):
        print(f"{'='*60}")
        print(f"Запись #{i} (Источник: {info.source or 'неизвестно'})")
        print(f"{'='*60}")
        
        if info.name:
            print(f"Название: {info.name}")
        if info.ico:
            print(f"IČO: {info.ico}")
        if info.address:
            print(f"Адрес: {info.address}")
        if info.phone:
            print(f"Телефон: {info.phone}")
        if info.website:
            print(f"Сайт: {info.website}")
        if info.director:
            print(f"Директор: {info.director}")
        if info.owners:
            print(f"Владельцы: {', '.join(info.owners)}")
        
        print()


async def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(
        description="Поиск владельцев бизнеса в Чехии через ARES и торговый реестр"
    )
    parser.add_argument("--name", help="Название компании")
    parser.add_argument("--ico", help="IČO (идентификационный номер компании)")
    parser.add_argument("--address", help="Адрес компании")
    parser.add_argument("--phone", help="Телефон компании")
    parser.add_argument("--json", action="store_true", help="Вывести результат в JSON формате")
    
    args = parser.parse_args()
    
    if not any([args.name, args.ico, args.address, args.phone]):
        parser.print_help()
        return
    
    print("🔎 Поиск информации о компании...\n")
    
    results = await search_business(
        name=args.name,
        ico=args.ico,
        address=args.address,
        phone=args.phone
    )
    
    if args.json:
        print(json.dumps([r.model_dump(exclude_none=True, by_alias=True) for r in results], 
                         indent=2, ensure_ascii=False))
    else:
        print_results(results)


if __name__ == "__main__":
    asyncio.run(main())
