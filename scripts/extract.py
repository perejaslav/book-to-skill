#!/usr/bin/env python3
"""Extract text from a PDF or EPUB file for Hermes book-to-skill processing."""

from __future__ import annotations

import html
import html.parser
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

OUTPUT_DIR = Path('/tmp/book_skill_work')
OUTPUT_TEXT = OUTPUT_DIR / 'full_text.txt'
OUTPUT_META = OUTPUT_DIR / 'metadata.json'
WORDS_PER_TOKEN = 0.75


def estimate_tokens(text: str) -> int:
    return int(len(text.split()) / WORDS_PER_TOKEN)


def detect_language(text: str) -> str:
    """Return 'ru' or 'en' based on character distribution in first 50K chars."""
    sample = text[:50000]
    cyrillic = sum(1 for c in sample if '\u0400' <= c <= '\u04FF')
    latin = sum(1 for c in sample if 'a' <= c <= 'z' or 'A' <= c <= 'Z')
    total = cyrillic + latin
    if total == 0:
        return 'en'
    return 'ru' if cyrillic / total >= 0.3 else 'en'


def extract_with_pdftotext(pdf_path: str) -> str | None:
    if not shutil.which('pdftotext'):
        return None
    try:
        result = subprocess.run(['pdftotext', '-layout', pdf_path, '-'], capture_output=True, text=True, timeout=180)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except Exception:
        return None
    return None


def extract_with_pypdf2(pdf_path: str) -> str | None:
    try:
        import PyPDF2
        parts: list[str] = []
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                try:
                    parts.append(page.extract_text() or '')
                except Exception:
                    parts.append('')
        text = '\n'.join(parts)
        return text if text.strip() else None
    except Exception:
        return None


def extract_with_pdfminer(pdf_path: str) -> str | None:
    try:
        from pdfminer.high_level import extract_text
        text = extract_text(pdf_path)
        return text if text and text.strip() else None
    except Exception:
        return None


class _HTMLTextExtractor(html.parser.HTMLParser):
    SKIP_TAGS = {'script', 'style', 'head'}

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
        if tag in ('p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'div'):
            self._parts.append('\n')

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._parts.append(data)

    def get_text(self) -> str:
        return html.unescape(''.join(self._parts))


def extract_with_ebooklib(epub_path: str) -> str | None:
    try:
        import ebooklib
        from ebooklib import epub
        from bs4 import BeautifulSoup

        book = epub.read_epub(epub_path)
        parts: list[str] = []
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            parts.append(soup.get_text(separator='\n'))
        text = '\n\n'.join(parts)
        return text if text.strip() else None
    except Exception:
        return None


def extract_with_zipfile(epub_path: str) -> str | None:
    try:
        with zipfile.ZipFile(epub_path) as zf:
            names = zf.namelist()
            html_files = sorted(n for n in names if n.endswith(('.html', '.xhtml')))
            if not html_files:
                return None
            parts: list[str] = []
            for name in html_files:
                try:
                    raw = zf.read(name).decode('utf-8', errors='replace')
                    parser = _HTMLTextExtractor()
                    parser.feed(raw)
                    parts.append(parser.get_text())
                except Exception:
                    continue
            text = '\n\n'.join(parts)
            return text if text.strip() else None
    except Exception:
        return None


def extract_epub(epub_path: str) -> tuple[str, str]:
    print('Trying ebooklib + BeautifulSoup4...', end=' ', flush=True)
    text = extract_with_ebooklib(epub_path)
    if text:
        print('OK')
        return text, 'ebooklib'
    print('not available')

    print('Trying stdlib zipfile parser...', end=' ', flush=True)
    text = extract_with_zipfile(epub_path)
    if text:
        print('OK')
        return text, 'zipfile'
    print('FAILED')
    raise RuntimeError('Could not extract text from EPUB. Install: pip3 install ebooklib beautifulsoup4')


def count_epub_chapters(epub_path: str) -> int:
    try:
        with zipfile.ZipFile(epub_path) as zf:
            opf_files = [n for n in zf.namelist() if n.endswith('.opf')]
            if not opf_files:
                return 0
            opf_text = zf.read(opf_files[0]).decode('utf-8', errors='replace')
            return len(re.findall(r'<itemref\b', opf_text))
    except Exception:
        return 0


def count_pages(pdf_path: str) -> int:
    if shutil.which('pdfinfo'):
        try:
            result = subprocess.run(['pdfinfo', pdf_path], capture_output=True, text=True, timeout=15)
            for line in result.stdout.splitlines():
                if line.startswith('Pages:'):
                    return int(line.split(':', 1)[1].strip())
        except Exception:
            pass
    try:
        import PyPDF2
        with open(pdf_path, 'rb') as f:
            return len(PyPDF2.PdfReader(f).pages)
    except Exception:
        return 0


def detect_structure(text: str) -> dict:
    lines = text[:50000].splitlines()
    chapter_pattern = re.compile(r'^\s*(chapter\s+\d+|глава\s+\d+|part\s+[ivx]+|раздел\s+\d+|\d+\.\s+\S)', re.IGNORECASE)
    chapters_found = [line.strip() for line in lines if chapter_pattern.match(line)]
    toc_keywords = ['table of contents', 'contents', 'оглавление', 'содержание', 'índice', 'sumário']
    has_toc = any(keyword in text[:10000].lower() for keyword in toc_keywords)
    return {
        'chapters_detected': len(chapters_found),
        'chapter_headings_sample': chapters_found[:20],
        'has_toc': has_toc,
    }


def extract_with_docling(pdf_path: str) -> str | None:
    try:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False
        pipeline_options.do_table_structure = True
        converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)})
        result = converter.convert(pdf_path)
        text = result.document.export_to_markdown()
        return text if text and text.strip() else None
    except Exception:
        return None


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: extract.py <book.pdf|book.epub> [--mode technical|text]', file=sys.stderr)
        return 1

    input_path = sys.argv[1]
    extraction_mode = 'text'
    if '--mode' in sys.argv:
        idx = sys.argv.index('--mode')
        if idx + 1 < len(sys.argv):
            extraction_mode = sys.argv[idx + 1].lower()
    if extraction_mode not in ('technical', 'text'):
        extraction_mode = 'text'

    if not os.path.exists(input_path):
        print(f'ERROR: File not found: {input_path}', file=sys.stderr)
        return 1

    ext = Path(input_path).suffix.lower()
    is_epub = ext == '.epub'
    is_pdf = ext == '.pdf'
    if not is_epub and not is_pdf:
        with open(input_path, 'rb') as f:
            header = f.read(8)
        if header[:4] == b'%PDF':
            is_pdf = True
        elif header[:2] == b'PK':
            is_epub = True
        else:
            print(f"ERROR: Unsupported format '{ext}'. Supported: .pdf, .epub", file=sys.stderr)
            return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        if is_epub:
            print(f'Extracting EPUB: {input_path}')
            text, method = extract_epub(input_path)
            pages = count_epub_chapters(input_path)
            pages_label = 'spine_items'
        else:
            print(f'Extracting PDF: {input_path}')
            text = None
            method = ''
            if extraction_mode == 'technical':
                print('Mode: technical — trying Docling...', end=' ', flush=True)
                text = extract_with_docling(input_path)
                if text:
                    method = 'docling'
                    print('OK')
                else:
                    print('not available; falling back to text mode')
                    extraction_mode = 'text'
            if extraction_mode == 'text':
                for label, fn in [('pdftotext', extract_with_pdftotext), ('PyPDF2', extract_with_pypdf2), ('pdfminer', extract_with_pdfminer)]:
                    print(f'Trying {label}...', end=' ', flush=True)
                    text = fn(input_path)
                    if text:
                        method = label
                        print('OK')
                        break
                    print('not available')
            if not text:
                raise RuntimeError('Could not extract text from PDF. Install poppler-utils, PyPDF2, pdfminer.six, or docling.')
            pages = count_pages(input_path)
            pages_label = 'pages'
    except RuntimeError as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1

    OUTPUT_TEXT.write_text(text, encoding='utf-8')
    tokens = estimate_tokens(text)
    structure = detect_structure(text)
    language = detect_language(text)
    metadata = {
        'source_file': str(Path(input_path).resolve()),
        'filename': Path(input_path).name,
        'format': 'epub' if is_epub else 'pdf',
        'extraction_method': method,
        'extraction_mode': extraction_mode,
        'file_size_mb': round(os.path.getsize(input_path) / (1024 * 1024), 2),
        pages_label: pages,
        'chars': len(text),
        'words': len(text.split()),
        'estimated_tokens': tokens,
        'estimated_tokens_human': f'~{tokens // 1000}K',
        'language': language,
        'output_text': str(OUTPUT_TEXT),
        **structure,
    }
    OUTPUT_META.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf-8')

    print('\nExtraction complete:')
    print(f"  Format   : {'EPUB' if is_epub else 'PDF'}")
    print(f'  Method   : {method}')
    print(f"  {'Spine items' if is_epub else 'Pages'} : {pages}")
    print(f"  Words    : {len(text.split()):,}")
    print(f'  Tokens   : ~{tokens // 1000}K')
    print(f"  Language : {'Russian' if language == 'ru' else 'English'}")
    print(f"  Chapters : {structure['chapters_detected']} detected")
    print(f"  ToC      : {'yes' if structure['has_toc'] else 'not detected'}")
    print(f'\nText -> {OUTPUT_TEXT}')
    print(f'Meta -> {OUTPUT_META}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
