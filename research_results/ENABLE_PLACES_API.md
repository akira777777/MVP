# Включение Places API для Google Maps

## Проблема

API ключ работает, но Places API не включен в проекте Google Cloud.

## Решение

1. **Перейдите по ссылке:**
   <https://console.developers.google.com/apis/api/places.googleapis.com/overview?project=285342268663>

2. **Нажмите кнопку "ENABLE" (Включить)**

3. **Также включите Legacy Places API:**
   <https://console.developers.google.com/apis/api/places-backend.googleapis.com/overview?project=285342268663>

4. **Подождите 2-3 минуты** для распространения изменений

5. **Запустите скрипт снова:**

   ```powershell
   cd c:\Users\-\Desktop\MVP\research_results
   C:\Python312\python.exe scripts\prague_business_leads.py --categories kadeřnictví kosmetika restaurace --max-per-category 15
   ```

## Альтернатива: Браузерный скрапер

Если не хотите включать API, можно использовать браузерный скрапер (работает без API ключа, но медленнее):

```powershell
C:\Python312\python.exe scripts\collect_prague_businesses.py
```
