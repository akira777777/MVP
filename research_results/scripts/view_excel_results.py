"""Просмотр результатов поиска бизнеса в Праге из Excel файлов."""

import sys
import os
from pathlib import Path

# Устанавливаем UTF-8 кодировку для вывода
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    import pandas as pd
except ImportError:
    print("Устанавливаю pandas...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "openpyxl"])
    import pandas as pd

def view_excel_files():
    """Показать все Excel файлы с результатами."""
    leads_dir = project_root / "leads"
    
    if not leads_dir.exists():
        print(f"❌ Директория {leads_dir} не найдена!")
        return
    
    excel_files = list(leads_dir.glob("*.xlsx"))
    
    if not excel_files:
        print(f"❌ Excel файлы не найдены в {leads_dir}")
        return
    
    print(f"\n{'=' * 70}")
    print("РЕЗУЛЬТАТЫ ПОИСКА БИЗНЕСА В ПРАГЕ")
    print(f"{'=' * 70}\n")
    
    # Сортируем по дате создания (новые первыми)
    excel_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    for i, file_path in enumerate(excel_files, 1):
        print(f"\nФайл {i}: {file_path.name}")
        print(f"   Полный путь: {file_path}")
        print(f"   Размер: {file_path.stat().st_size / 1024:.2f} KB")
        
        try:
            df = pd.read_excel(file_path)
            print(f"   Всего строк: {len(df)}")
            print(f"   Колонки: {', '.join(df.columns.tolist())}")
            
            # Показываем статистику
            if len(df) > 0:
                print(f"\n   Статистика:")
                if 'Телефон' in df.columns:
                    with_phone = df['Телефон'].notna().sum()
                    print(f"      С телефоном: {with_phone} ({with_phone*100//len(df)}%)")
                if 'Email' in df.columns:
                    with_email = df['Email'].notna().sum()
                    print(f"      С email: {with_email} ({with_email*100//len(df)}%)")
                if 'Полное имя владельца' in df.columns:
                    with_owner = df['Полное имя владельца'].notna().sum()
                    print(f"      С именем владельца: {with_owner} ({with_owner*100//len(df)}%)")
                
                # Показываем первые 3 строки
                print(f"\n   Первые 3 записи:")
                for idx, row in df.head(3).iterrows():
                    name = row.get('Название бизнеса', 'N/A')
                    phone = row.get('Телефон', 'N/A')
                    email = row.get('Email', 'N/A')
                    print(f"      {idx+1}. {name} | Телефон: {phone} | Email: {email}")
        
        except Exception as e:
            print(f"   ❌ Ошибка чтения файла: {e}")
    
    print(f"\n{'=' * 70}")
    print(f"Все файлы находятся в: {leads_dir}")
    print(f"{'=' * 70}\n")

if __name__ == "__main__":
    view_excel_files()
