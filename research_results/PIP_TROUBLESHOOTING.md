# Решение проблем с pip на Windows

## Быстрая диагностика

### 1. Проверьте установку Python

```bash
# Попробуйте эти команды по очереди:
python --version
python3 --version
py --version
```

**Если ни одна не работает:**

- Python не установлен → [Скачайте Python](https://www.python.org/downloads/)
- При установке **ОБЯЗАТЕЛЬНО** отметьте "Add Python to PATH"

### 2. Проверьте установку pip

```bash
# Попробуйте эти команды:
pip --version
python -m pip --version
python3 -m pip --version
py -m pip --version
```

**Если `pip` не работает, но `python -m pip` работает:**

- pip не добавлен в PATH → используйте `python -m pip` вместо `pip`

### 3. Установите/переустановите pip

```bash
# Если Python установлен, но pip нет:
python -m ensurepip --upgrade

# Или скачайте get-pip.py:
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python get-pip.py
```

## Частые проблемы и решения

### Проблема 1: "pip is not recognized as an internal or external command"

**Решение:**

1. Используйте `python -m pip` вместо `pip`
2. Или добавьте Python в PATH:
   - **📖 Подробная инструкция**: См. [ADD_PYTHON_TO_PATH.md](./ADD_PYTHON_TO_PATH.md)
   - **🚀 Быстрый способ**: Запустите `scripts\add_python_to_path.bat` от имени администратора
   - **Вручную**: Найдите папку Python (обычно `C:\Python3x\` или `C:\Users\ВашеИмя\AppData\Local\Programs\Python\Python3x\`) и добавьте в PATH:
     - `C:\Python3x\`
     - `C:\Python3x\Scripts\`

### Проблема 2: "Permission denied" или "Access denied"

**Решение:**

1. Запустите командную строку от имени администратора
2. Или используйте флаг `--user`:

   ```bash
   python -m pip install --user package_name
   ```

### Проблема 3: Несколько версий Python

**Решение:**
Используйте Python Launcher (`py`):

```bash
# Установка пакета в конкретную версию Python
py -3.11 -m pip install package_name
py -3.12 -m pip install package_name

# Проверка версии
py -0  # Покажет все установленные версии Python
```

### Проблема 4: pip устарел

**Решение:**

```bash
python -m pip install --upgrade pip
```

### Проблема 5: SSL ошибки при установке

**Решение:**

```bash
python -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org package_name
```

## Рекомендуемый рабочий процесс

### Для этого проекта

1. **Всегда используйте `python -m pip` вместо `pip`:**

   ```bash
   python -m pip install -r requirements.txt
   ```

2. **Используйте виртуальное окружение:**

   ```bash
   # Создать виртуальное окружение
   python -m venv venv

   # Активировать (Windows)
   venv\Scripts\activate

   # Установить зависимости
   python -m pip install -r requirements.txt
   ```

3. **Проверьте установку:**

   ```bash
   python -m pip list
   python -m pip show package_name
   ```

## Альтернативные методы установки

### Если pip совсем не работает

1. **Используйте conda/miniconda:**

   ```bash
   conda install package_name
   ```

2. **Скачайте wheel файлы вручную:**
   - Зайдите на [PyPI](https://pypi.org/)
   - Скачайте `.whl` файл
   - Установите: `python -m pip install downloaded_file.whl`

3. **Используйте pip через get-pip.py:**

   ```bash
   curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
   python get-pip.py
   ```

## Проверка окружения

Выполните эти команды для диагностики:

```bash
# Версия Python
python --version

# Расположение Python
python -c "import sys; print(sys.executable)"

# Расположение pip
python -m pip --version

# Список установленных пакетов
python -m pip list

# Информация о pip
python -m pip show pip
```

## Дополнительные ресурсы

- [ADD_PYTHON_TO_PATH.md](./ADD_PYTHON_TO_PATH.md) - Подробная инструкция по добавлению Python в PATH
- [scripts/add_python_to_path.bat](./scripts/add_python_to_path.bat) - Автоматический скрипт для добавления Python в PATH

## Контакты и дополнительная помощь

Если проблема не решена:

1. Проверьте [официальную документацию pip](https://pip.pypa.io/en/stable/)
2. Проверьте [Python на Windows FAQ](https://docs.python.org/3/faq/windows.html)
3. Убедитесь, что используете последнюю версию Python
4. См. [ADD_PYTHON_TO_PATH.md](./ADD_PYTHON_TO_PATH.md) для решения проблем с PATH
