---
name: book-to-skill
description: "Конвертирует PDF или EPUB книгу в отдельный Hermes Agent skill: извлекает текст, выделяет главы, ключевые понятия, фреймворки, паттерны, анти-паттерны и создает папку с SKILL.md, chapter-файлами, glossary.md, patterns.md и cheatsheet.md."
version: 1.1.0
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [documents, books, pdf, epub, skills, knowledge-base, conversion]
---

# Book-to-Skill для Hermes Agent

## Когда использовать

Используй этот скилл, когда пользователь хочет превратить книгу, статью, руководство, PDF или EPUB в переиспользуемый скилл Hermes Agent. Типовые формулировки: «сделай скилл из книги», «конвертируй PDF в skill», «создай skill из EPUB», «извлеки фреймворки из книги», «хочу использовать эту книгу как базу знаний агента».

## Назначение

Скилл превращает одну книгу в компактный прикладной набор инструкций для агента. Цель — не пересказать книгу, а извлечь из нее рабочие модели: фреймворки, принципы, методы, определения, таблицы решений, анти-паттерны и указатель тем.

Результат создается как отдельный Hermes skill в каталоге:

```bash
~/.hermes/skills/<skill-name>/
```

Структура результата:

```text
<skill-name>/
├── SKILL.md
├── chapters/
│   ├── ch01-*.md
│   ├── ch02-*.md
│   └── ...
├── glossary.md
├── patterns.md
└── cheatsheet.md
```

## Входные данные

Пользователь должен дать путь к файлу PDF или EPUB и, при желании, короткое имя будущего скилла.

Примеры:

```bash
/book-to-skill /home/immor/books/designing-data-intensive-applications.pdf
/book-to-skill /home/immor/books/clean-code.epub clean-code
/book-to-skill /mnt/c/Users/immor/Downloads/book.pdf my-book-skill
```

Если путь не указан или файл не является PDF/EPUB, остановись и объясни правильный формат команды.

## Подготовка зависимостей

Для обычных текстовых PDF предпочтителен `pdftotext` из `poppler-utils`. Для EPUB полезны `ebooklib` и `beautifulsoup4`. Для сложных технических PDF с таблицами и кодом можно использовать `docling`, но он работает медленнее.

Проверка и установка в Ubuntu/WSL:

```bash
sudo apt update
sudo apt install -y poppler-utils python3-pip
# Python 3.11+ (Debian/Ubuntu 24+) требует --break-system-packages
python3 -m pip install --break-system-packages PyPDF2 pdfminer.six ebooklib beautifulsoup4
```

> **Pitfall (Python 3.11+/Ubuntu 24.04+)**: без `--break-system-packages` pip отказывается ставить в user site из-за PEP 668. Ошибка: `notice: consider using --break-system-packages`. Всегда используй этот флаг на современных системах.

Опционально для сложных технических PDF:

```bash
python3 -m pip install --user docling
```

## Процедура

### 1. Проверить аргументы

Проверь, что файл существует:

```bash
test -f "<book_path>" && echo FILE_OK || echo FILE_NOT_FOUND
```

Проверь расширение или сигнатуру файла. Поддерживаются только PDF и EPUB.

### 2. Определить режим извлечения

Спроси пользователя, если режим не очевиден:

1. `technical` — книга с кодом, таблицами, формулами, схемами; лучше использовать Docling.
2. `text` — в основном обычный текст; лучше использовать быстрый `pdftotext` с запасными вариантами.

Если пользователь не уверен, выбери `text` и предупреди, что для сложной верстки качество может быть ниже.

### 3. Извлечь текст

Запусти помощник:

```bash
python3 ~/.hermes/skills/book-to-skill/scripts/extract.py "<book_path>" --mode <technical|text>
```

После успешного выполнения будут созданы:

```text
/tmp/book_skill_work/full_text.txt
/tmp/book_skill_work/metadata.json
```

Прочитай `metadata.json` и оцени объем: страницы, слова, примерное число токенов, обнаруженные главы, наличие оглавления. **Определи язык книги**: поле `"language"` — `"ru"` или `"en"`.

### 4. Предварительно сообщить пользователю объем работы

Перед полной генерацией сообщи:

```text
Книга: <filename>
Формат: <pdf|epub>
Язык: <ru|en>
Страниц/разделов: ~<N>
Слов: ~<N>
Примерный объем исходного текста: ~<N>K токенов
```

Будут созданы: SKILL.md, chapters/, glossary.md, patterns.md, cheatsheet.md

Если книга очень большая, предложи режим `analyze only` — только анализ структуры без записи итогового скилла.

### 5. Проанализировать структуру книги

Прочитай начало `/tmp/book_skill_work/full_text.txt`, оглавление и заголовки глав. Определи:

- название книги;
- автора или авторов;
- структуру глав;
- основные темы;
- ключевые фреймворки;
- термины;
- методы;
- анти-паттерны;
- возможное имя скилла;
- **язык книги** (из `metadata.json` → `"language"`: `"ru"` или `"en"`).

Если имя не задано пользователем, выбери короткий slug в нижнем регистре через дефисы. Предпочтительный формат: `<author-or-topic>-<core-concept>`.

### 6. Создать каталог результата

```bash
mkdir -p ~/.hermes/skills/<skill_name>/chapters
```

Если каталог уже существует, не перезаписывай молча. Спроси пользователя или создай вариант с суффиксом `-2`.

### 7. Создать файлы глав

Для каждой главы создай файл:

```text
~/.hermes/skills/<skill_name>/chapters/ch<NN>-<slug>.md
```

Структура файла главы — **заголовки секций на языке книги**:

**English:**
```markdown
# Chapter N: <Title>

## Core Idea
<1–2 предложения о главной идее главы.>

## Frameworks Introduced
- **<Framework>**: <что это и когда применять>
  - When to use: <ситуация>
  - How: <шаги или критерии>

## Key Concepts
- **<Term>**: <точное определение> (Ch N)

## Mental Models
- <модель мышления в прикладной формулировке>

## Anti-patterns
- **<что избегать>**: <почему это ошибка>

## Code Examples
<Только для технических книг. Сохраняй синтаксис и отступы. Если кода нет, раздел не добавляй.>

## Reference Tables
<Только если в книге есть важные таблицы, матрицы или сравнения.>

## Key Takeaways
1. <прикладной вывод>
2. <прикладной вывод>
3. <прикладной вывод>

## Connects To
- **Ch N**: <связь>
```

**Русский:**
```markdown
# Глава N: <Название>

## Ключевая идея
<1–2 предложения о главной идее главы.>

## Введенные фреймворки
- **<Фреймворк>**: <что это и когда применять>
  - Когда использовать: <ситуация>
  - Как: <шаги или критерии>

## Ключевые понятия
- **<Термин>**: <точное определение> (Гл N)

## Ментальные модели
- <модель мышления в прикладной формулировке>

## Анти-паттерны
- **<что избегать>**: <почему это ошибка>

## Примеры кода
<Только для технических книг. Сохраняй синтаксис и отступы. Если кода нет, раздел не добавляй.>

## Справочные таблицы
<Только если в книге есть важные таблицы, матрицы или сравнения.>

## Ключевые выводы
1. <прикладной вывод>
2. <прикладной вывод>
3. <прикладной вывод>

## Связано с
- **Гл N**: <связь>
```

Ориентир: 800–1200 токенов на главу. Пиши плотно, без длинного пересказа.

### 8. Создать supporting files

Создай `glossary.md` — заголовки на языке книги:

**English:**
```markdown
# Glossary

**Term** — definition (Ch N)
```

**Русский:**
```markdown
# Глоссарий

**Термин** — определение (Гл N)
```

Создай `patterns.md` — заголовки на языке книги:

**English:**
```markdown
# Patterns and Methods

## Pattern Name
**When to use**: ...
**How**: ...
**Trade-offs**: ...
```

**Русский:**
```markdown
# Паттерны и методы

## Название паттерна
**Когда использовать**: ...
**Как**: ...
**Компромиссы**: ...
```

Создай `cheatsheet.md` — заголовки на языке книги:

**English:**
```markdown
# Cheatsheet

Краткие правила, таблицы решений, сравнения, контрольные списки.
```

**Русский:**
```markdown
# Шпаргалка

Краткие правила, таблицы решений, сравнения, контрольные списки.
```

Ограничения:

- `glossary.md`: до 1500 токенов;
- `patterns.md`: до 2000 токенов;
- `cheatsheet.md`: до 1000 токенов.

### 9. Создать главный SKILL.md результата

Главный файл должен быть совместим с Hermes Agent: YAML-frontmatter, затем Markdown-инструкции.

Шаблон на языке книги:

**English:**
```markdown
---
name: <skill_name>
description: Knowledge base from "<Full Title>" by <Author>. Use when applying the book's frameworks for <topics>.
version: 1.0.0
metadata:
  hermes:
    tags: [book, knowledge-base, <topic1>, <topic2>]
---

# <Full Title>

**Author**: <Author>
**Generated**: <YYYY-MM-DD>
**Source**: <filename>
**Chapters**: <N>

## When to Use

Use this skill when the user asks about <major topics>, named frameworks, chapter references, methods, principles, or decisions covered by the book.

## Core Frameworks & Mental Models

<Самые важные фреймворки книги. Писать как прикладной инструмент: "Use X when Y".>

## Chapter Index

| # | Title | Key Frameworks |
|---|-------|----------------|
| [ch01](chapters/ch01-<slug>.md) | <Title> | <frameworks> |

## Topic Index

- **<Term>** → ch<N>
- **<Framework>** → ch<N>, ch<M>

## Supporting Files

- [glossary.md](glossary.md) — definitions and key terms
- [patterns.md](patterns.md) — methods, techniques, patterns
- [cheatsheet.md](cheatsheet.md) — quick reference

## Procedure for the Agent

1. If the user asks a broad question, answer from Core Frameworks first.
2. If the user asks about a specific topic, consult Topic Index and read the relevant chapter file.
3. If the user asks for terminology, read `glossary.md`.
4. If the user asks how to apply a method, read `patterns.md` and the relevant chapter.
5. If the user needs a quick decision, read `cheatsheet.md`.
6. Do not invent chapter claims. If the generated files do not cover the question, say that the book-derived skill does not contain enough information.

## Scope & Limits

This skill is derived from the supplied book. It is a structured working memory, not a replacement for the full source text. Do not provide long verbatim excerpts from copyrighted material.
```

**Русский:**
```markdown
---
name: <skill_name>
description: База знаний по книге "<Полное название>" автора <Автор>. Используй когда применяешь фреймворки книги для <темы>.
version: 1.0.0
metadata:
  hermes:
    tags: [book, knowledge-base, <topic1>, <topic2>]
---

# <Полное название>

**Автор**: <Автор>
**Создано**: <YYYY-MM-DD>
**Источник**: <filename>
**Глав**: <N>

## Когда использовать

Используй этот скилл, когда пользователь спрашивает о <основные темы>, именованных фреймворках, ссылках на главы, методах, принципах или решениях, описанных в книге.

## Ключевые фреймворки и ментальные модели

<Самые важные фреймворки книги. Писать как прикладной инструмент: "Используй X когда Y".>

## Указатель глав

| # | Название | Ключевые фреймворки |
|---|----------|---------------------|
| [гл01](chapters/ch01-<slug>.md) | <Название> | <фреймворки> |

## Указатель тем

- **<Термин>** → гл<N>
- **<Фреймворк>** → гл<N>, гл<M>

## Вспомогательные файлы

- [glossary.md](glossary.md) — определения и ключевые термины
- [patterns.md](patterns.md) — методы, техники, паттерны
- [cheatsheet.md](cheatsheet.md) — быстрая шпаргалка

## Процедура для агента

1. Если пользователь задает общий вопрос — отвечай на основе ключевых фреймворков.
2. Если пользователь спрашивает о конкретной теме — посмотри указатель тем и прочитай соответствующий файл главы.
3. Если пользователь спрашивает о терминологии — прочитай `glossary.md`.
4. Если пользователь спрашивает, как применить метод — прочитай `patterns.md` и соответствующую главу.
5. Если пользователю нужно быстрое решение — прочитай `cheatsheet.md`.
6. Не придумывай утверждения о главах. Если сгенерированные файлы не содержат ответа — скажи, что в базе знаний книги недостаточно информации.

## Область применения и ограничения

Этот скилл создан на основе книги. Это структурированная рабочая память, а не замена полному тексту. Не предоставляй длинные цитаты из защищенного авторским правом материала.
```

### 10. Проверить результат

Проверь наличие файлов:

```bash
find ~/.hermes/skills/<skill_name> -maxdepth 2 -type f | sort
```

Проверь, что главный `SKILL.md` начинается с валидного YAML-frontmatter и содержит `name` и `description`.

### 11. Очистить временные файлы

```bash
rm -rf /tmp/book_skill_work
```

### 12. Финальный отчет

Сообщи пользователю:

```text
Скилл создан: ~/.hermes/skills/<skill_name>/
Файлы: SKILL.md, chapters/<N>, glossary.md, patterns.md, cheatsheet.md
Как использовать: попросите Hermes применить скилл <skill_name> к нужной теме.
```

## Правила качества

1. Извлекай структуру, а не делай обычный пересказ.
2. Сохраняй точные названия авторских фреймворков, методов и терминов.
3. Не копируй длинные фрагменты книги дословно.
4. Пиши прикладным языком: что делать, когда применять, какие ограничения.
5. Главный `SKILL.md` держи компактным; подробности выноси в `chapters/`, `glossary.md`, `patterns.md`, `cheatsheet.md`.
6. Всегда делай Topic Index — это навигационная карта для агента.
7. Если источник плохо извлекся, не имитируй уверенность. Сообщи о проблеме и предложи режим `technical` с Docling.
8. **Языковая консистентность**: все генерируемые файлы (chapter-файлы, glossary.md, patterns.md, cheatsheet.md, главный SKILL.md) должны быть на языке оригинала книги. Определи язык через `metadata.json` → `"language"`. Финальный отчёт пользователю — всегда на русском.
