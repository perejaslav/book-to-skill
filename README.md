# book-to-skill

Конвертирует PDF или EPUB книгу в Hermes Agent skill: извлекает текст, выделяет главы, ключевые понятия, фреймворки, паттерны, анти-паттерны и создаёт структурированную базу знаний агента.

**Поддерживает русский и английский языки** — все генерируемые файлы создаются на языке оригинала книги.

---

## ¿Por qué?

Вы читаете книгу. Через три месяца забываете, что в ней было. PDF не помогает — это поиск страниц, не ответов. Конспект не открываете. **book-to-skill превращает книгу в рабочую память агента.**

Запустили `/book-to-skill путь/к/книге.pdf` → получили структуру → спросили агента о конкретной теме → он прочитал нужную главу и ответил по существу. Без галлюцинаций. Без поиска по PDF.

---

## Что генерируется

После запуска создаётся каталог `~/.hermes/skills/<slug>/`:

| Файл | Назначение | Лимит |
|------|-----------|-------|
| `SKILL.md` | Основные фреймворки + указатель глав | ~4K токенов |
| `chapters/ch01-*.md` … | Один файл на главу, загружается по запросу | ~800-1200 токенов |
| `glossary.md` | Все термины в алфавитном порядке со ссылками на главы | 1500 токенов |
| `patterns.md` | Техники, алгоритмы, дизайн-паттерны | 2000 токенов |
| `cheatsheet.md` | Таблицы решений, быстрые правила | 1000 токенов |

Главы загружаются **по запросу** — не занимают память, пока не понадобятся.

---

## Использование

```bash
/book-to-skill <путь-к-pdf-или-epub> [имя-скилла]
```

Примеры:

```bash
/book-to-skill ~/books/designing-data-intensive-applications.pdf
/book-to-skill ~/books/clean-code.epub clean-code
/book-to-skill /mnt/c/Users/immor/Downloads/book.pdf my-book-skill
```

После установки:

```bash
/designing-data-intensive-apps              # загрузить основные фреймворки
/designing-data-intensive-apps replication    # найти и объяснить тему
/designing-data-intensive-apps ch05           # погрузиться в главу 5
```

---

## Требования

**Для PDF:**

| Тип книги | Инструмент | Установка |
|-----------|-----------|-----------|
| Текстовая (проза) | `pdftotext` (poppler) | `sudo apt install poppler-utils` |
| Текстовая fallback | `PyPDF2` | `pip3 install PyPDF2` |
| Текстовая fallback | `pdfminer.six` | `pip3 install pdfminer.six` |
| **Техническая (код, таблицы, формулы)** | **`docling`** | `pip3 install docling` |

**Для EPUB:**

| Инструмент | Установка | Качество |
|-----------|-----------|---------|
| `ebooklib` + `beautifulsoup4` | `pip3 install ebooklib beautifulsoup4` | ⭐⭐⭐ Лучшее |
| stdlib `zipfile` | встроен — не требует установки | ⭐⭐ Всегда доступен |

Перед извлечением скилл спрашивает — **техническая** или **текстовая** книга — и выбирает подходящий инструмент.

---

## Как работает

```
PDF или EPUB
     │
     ▼
Определение языка (кириллица ≥30% → русский)
     │
     ▼
scripts/extract.py --mode <technical|text>
  PDF → pdftotext → PyPDF2 → pdfminer → Docling
  EPUB → ebooklib → stdlib zipfile
     │
     ├── /tmp/book_skill_work/full_text.txt
     └── /tmp/book_skill_work/metadata.json
               │
               ▼
          Агент анализирует структуру
          (название, автор, главы, оглавление, язык)
               │
               ▼
          Генерирует файлы глав (800-1200 токенов каждая)
          technical → включает секции "Примеры кода" + "Справочные таблицы"
          Генерирует glossary, patterns, cheatsheet
          Генерирует главный SKILL.md
               │
               ▼
          ~/.hermes/skills/<slug>/  ✅ записано
          /tmp/book_skill_work/     🗑️ очищено
```

**Языковая логика:**

- `metadata.json` → `"language": "ru"` или `"en"`
- Все файлы результата создаются на языке оригинала книги
- Русская книга → `glossary.md` с заголовком `# Глоссарий`, файл главы с `# Глава N:`
- Английская книга → `glossary.md` с заголовком `# Glossary`, файл главы с `# Chapter N:`
- Отчёт пользователю — всегда на русском

---

## Установка

```bash
# Клонировать репозиторий
git clone https://github.com/perejaslav/book-to-skill.git ~/.hermes/skills/book-to-skill

# Или вручную:
mkdir -p ~/.hermes/skills/book-to-skill/scripts

# Скопировать файлы
cp book-to-skill/SKILL.md ~/.hermes/skills/book-to-skill/
cp book-to-skill/scripts/extract.py ~/.hermes/skills/book-to-skill/scripts/
chmod +x ~/.hermes/skills/book-to-skill/scripts/extract.py
```

**Зависимости:**

```bash
# Ubuntu/WSL
sudo apt update && sudo apt install -y poppler-utils python3-pip
python3 -m pip install --break-system-packages PyPDF2 pdfminer.six ebooklib beautifulsoup4

# Опционально для технических PDF
python3 -m pip install --user docling
```

---

## Структура репозитория

```
book-to-skill/
├── SKILL.md              # Определение скилла + пошаговые инструкции
├── scripts/
│   └── extract.py        # Извлечение текста из PDF/EPUB
│                          # (pdftotext / PyPDF2 / pdfminer / ebooklib / zipfile)
├── install.sh             # Скрипт установки
└── README.md              # Этот файл
```

---

## License

MIT