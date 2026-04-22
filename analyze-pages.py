#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ZDKvartira.ru Website Crawler and Analyzer
===========================================
Analyzes HTML pages from zdkvartira.ru website, extracts block structures,
classifies page types, and generates comprehensive documentation.

Output:
- results/pages.txt: Tab-delimited list of all pages
- results/pages.csv: CSV format with quoted fields (UTF-8 BOM)
- results/types.yaml: Complete structured data for all page types
- results/page-types/*.md: Individual Markdown documentation per page type
- results/page-lists/*-pages.txt: Page lists organized by type

Features:
- Automatic page type classification (23 types identified)
- Block structure extraction with CSS selectors
- Text cleaning (removes line breaks and multiple spaces)
- Main page includes header/footer blocks; other pages exclude common blocks
- English dash-case IDs for all page types
"""

import os
import sys
import re
import csv
from pathlib import Path
from bs4 import BeautifulSoup
import yaml

# Configuration
BASE_URL = os.environ.get('ZDKVARTIRA_BASE_URL', 'https://zdkvartira.ru')

# Set stdout encoding to UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def clean_text(text):
    """
    Clean text by removing line breaks and replacing multiple spaces with single space.

    Args:
        text: Input text string

    Returns:
        Cleaned text with no line breaks and normalized whitespace
    """
    if not text:
        return ""
    # Replace all line break characters with space
    text = re.sub(r'[\n\r\t]+', ' ', text)
    # Replace multiple consecutive spaces with single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def page_type_to_id(page_type):
    """
    Convert Russian page type name to English dash-case ID.

    Args:
        page_type: Russian page type name

    Returns:
        English dash-case ID string (e.g., 'home-page', 'news-article')
    """
    translations = {
        'Главная страница': '00-main',
        'Каталог объектов недвижимости': 'property-catalog',
        'Страница новости': 'news-article',
        'Список новостей': 'news-list',
        'Страница услуги': 'service-page',
        'Список услуг': 'service-list',
        'Детальная страница объекта': 'property-detail',
        'Контакты': 'contacts',
        'О компании': 'about',
        'Вакансии': 'vacancies',
        'Список сотрудников': 'staff-list',
        'Профиль сотрудника': 'staff-profile',
        'Список акций': 'promotions-list',
        'Детальная страница акции': 'promotion-detail',
        'Список FAQ': 'faq-list',
        'Детальная страница FAQ': 'faq-detail',
        'Список отзывов': 'reviews-list',
        'Аналитика': 'analytics',
        'Список новостроек': 'new-buildings-list',
        'Детальная страница новостройки': 'new-building-detail',
        'Результаты поиска': 'search-results',
        'Личный кабинет (избранное/сравнение)': 'user-account',
        'Другая страница': 'other-page',
        'Служебная страница': 'system-page',
    }

    return translations.get(page_type, re.sub(r'[^\w\s-]', '', page_type).lower().replace(' ', '-'))


def extract_page_info(html_path, base_url=None, base_dir=None):
    """
    Extract page information: URL, title, and content blocks.

    Args:
        html_path: Path to HTML file
        base_url: Base URL for constructing page URLs (defaults to BASE_URL from environment)
        base_dir: Base directory for calculating relative paths

    Returns:
        Dictionary with url, title, blocks, and rel_path
    """

    # Use global BASE_URL if not provided
    if base_url is None:
        base_url = BASE_URL

    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    soup = BeautifulSoup(content, 'html.parser')

    # Extract page title
    title_tag = soup.find('title')
    title = title_tag.get_text().strip() if title_tag else "Без заголовка"

    # Calculate relative path from base directory
    if base_dir is None:
        # Fallback to script directory if not provided
        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'analyze-sources', 'zdkvartira.ru')

    rel_path = os.path.relpath(html_path, start=base_dir)
    rel_path = rel_path.replace('\\', '/')

    # Construct URL
    if rel_path == 'index.html':
        url = base_url + "/"
    else:
        # Remove index.html from path if present
        path_part = rel_path.replace('/index.html', '')
        url = f"{base_url}/{path_part}/"

    # Extract all blocks in document order
    blocks = []

    # Track all elements with their position in the document
    block_elements = []

    # Search for section elements with id attribute
    for section in soup.find_all('section'):
        block_id = section.get('id')
        if not block_id:
            continue

        # Skip technical ids
        if block_id in ['fav-count', 'slideContainer', 'pinContainer', 'slide-block']:
            continue

        # Determine CSS selector
        selector = f"#{block_id}"

        # Also consider section classes
        classes = section.get('class', [])
        if classes:
            class_selector = '.'.join([c for c in classes if c not in ['container', 'row', 'col', 'col-md', 'col-lg', 'col-sm', 'pb-5', 'pt-5', 'mb-5', 'mt-5', 'py-5', 'my-5']])
            if class_selector:
                selector = f"#{block_id}.{class_selector}" if class_selector else f"#{block_id}"

        # Extract block heading (h1, h2, or .caption)
        heading = ""
        h1 = section.find('h1')
        h2 = section.find('h2')
        caption = section.find(class_='caption')

        if h1:
            heading = h1.get_text().strip()
        elif h2:
            heading = h2.get_text().strip()
        elif caption:
            heading = caption.get_text().strip()

        # Generate detailed block description
        description = describe_block_detailed(section, block_id, heading)

        block_elements.append({
            'element': section,
            'data': {
                'id': block_id,
                'selector': selector,
                'heading': clean_text(heading),
                'description': clean_text(description),
                'tag': 'section'
            }
        })

    # Track processed elements to avoid duplicates
    processed_elements = set()

    # Also search for important blocks without section tag
    # Check divs, uls, navs, and other elements
    for element in soup.find_all(['div', 'ul', 'nav', 'aside']):
        elem_id = element.get('id')
        elem_classes = element.get('class', [])
        elem_name = element.name

        # Skip if already processed
        elem_key = id(element)
        if elem_key in processed_elements:
            continue

        # Skip already processed sections
        if element.parent and element.parent.name == 'section':
            continue

        # Check for mainheader and footer (only in divs)
        if elem_name == 'div' and ('mainheader' in elem_classes or 'footer' in elem_classes):
            block_type = 'mainheader' if 'mainheader' in elem_classes else 'footer'
            desc = describe_header_footer(element, block_type)

            block_elements.append({
                'element': element,
                'data': {
                    'id': block_type,
                    'selector': f".{block_type}",
                    'heading': '',
                    'description': clean_text(desc),
                    'tag': 'div',
                    'is_common': True
                }
            })
            processed_elements.add(elem_key)
            continue

        # Filter form (#filter) - can be any element type
        if elem_id == 'filter':
            block_elements.append({
                'element': element,
                'data': {
                    'id': 'filter',
                    'selector': '#filter',
                    'heading': '',
                    'description': 'Форма фильтрации и поиска. Поля для выбора параметров фильтрации, кнопки применения фильтров; CSS селектор: `#filter`',
                    'tag': elem_name
                }
            })
            processed_elements.add(elem_key)
            continue

        # top-back block (only in divs)
        if elem_name == 'div' and 'top-back' in elem_classes:
            heading_text = ""
            caption = element.find(class_='caption')
            if caption:
                heading_text = caption.get_text().strip()

            block_elements.append({
                'element': element,
                'data': {
                    'id': 'top-back',
                    'selector': '.top-back',
                    'heading': clean_text(heading_text),
                    'description': clean_text(describe_top_back(element, heading_text)),
                    'tag': 'div'
                }
            })
            processed_elements.add(elem_key)
            continue

        # breadcrumbs (any element type)
        if 'breadcrumbs' in elem_classes:
            block_elements.append({
                'element': element,
                'data': {
                    'id': 'breadcrumbs',
                    'selector': '.breadcrumbs',
                    'heading': '',
                    'description': 'Навигационная цепочка (хлебные крошки)',
                    'tag': elem_name
                }
            })
            processed_elements.add(elem_key)
            continue

        # Content container with news/articles list
        # Detect containers that hold lists of content items
        if elem_name == 'div' and 'container' in elem_classes and not elem_id:
            # Check for direct content children (news cards, articles, etc.)
            content_children = element.find_all(['article', 'div'],
                                                 class_=re.compile(r'd-flex|item|card|news|article|post'))
            # Filter out navigation and menu items
            content_items = [c for c in content_children
                           if not c.parent or 'nav' not in str(c.parent.get('class', []))]

            if len(content_items) >= 3:  # At least 3 content items indicates a list
                block_elements.append({
                    'element': element,
                    'data': {
                        'id': 'content-list',
                        'selector': '.container',
                        'heading': '',
                        'description': 'Список материалов (новости, статьи, аналитика). Контейнер с карточками контента; CSS селектор: `.container`',
                        'tag': 'div'
                    }
                })
                processed_elements.add(elem_key)
                continue

        # Pagination navigation (nav element or .pagination)
        if elem_name == 'nav' or 'pagination' in ' '.join(elem_classes):
            # Check if it contains pagination-like content
            has_page_links = bool(element.find_all('a', href=re.compile(r'\?page=|/page/|\?PAGEN')))
            has_numbers = bool(element.find_all(string=re.compile(r'^\d+$')))
            has_next_prev = bool(element.find_all(string=re.compile(r'следующая|предыдущая|next|prev', re.I)))

            if has_page_links or has_numbers or has_next_prev or 'pagination' in ' '.join(elem_classes):
                block_elements.append({
                    'element': element,
                    'data': {
                        'id': 'pagination',
                        'selector': 'nav' if elem_name == 'nav' else f".{'.'.join(elem_classes)}",
                        'heading': '',
                        'description': 'Навигация по страницам (пагинация). Ссылки на предыдущую/следующую страницу, номера страниц; CSS селектор: `nav` или класс пагинации',
                        'tag': elem_name
                    }
                })
                processed_elements.add(elem_key)
                continue

    # Sort blocks by their position in the document
    def get_element_position(elem):
        """Get approximate position of element in document"""
        pos = 0
        parent = elem.parent
        while parent:
            siblings = list(parent.children)
            try:
                idx = siblings.index(elem)
                pos += idx * 1000  # Weight by depth
            except ValueError:
                pass
            elem = parent
            parent = elem.parent if hasattr(elem, 'parent') else None
        return pos

    # Sort by document position
    block_elements.sort(key=lambda x: get_element_position(x['element']))

    # Remove duplicates by block ID (keep first occurrence)
    seen_ids = set()
    unique_blocks = []
    for item in block_elements:
        block_id = item['data']['id']
        if block_id not in seen_ids:
            seen_ids.add(block_id)
            unique_blocks.append(item['data'])

    blocks = unique_blocks

    return {
        'url': url,
        'title': title,
        'blocks': blocks,
        'rel_path': rel_path
    }


def describe_header_footer(element, block_type):
    """
    Describe website header or footer blocks.

    Args:
        element: BeautifulSoup element
        block_type: Either 'mainheader' or 'footer'

    Returns:
        Description string with semicolon-separated parts
    """
    if block_type == 'mainheader':
        parts = [
            "Главное меню и шапка сайта",
            "Содержит: время работы, кнопки 'Избранное' и 'Сравнение', логотип, название 'Офис в Железнодорожном', телефон, главное меню, кнопка подачи заявки, поиск",
            "CSS селектор: `.mainheader`",
            "Общий блок для всех страниц, не учитывается при определении типа страницы"
        ]
        return "; ".join(parts)
    else:
        parts = [
            "Подвал сайта",
            "Содержит: контакты, общая информация, меню навигации",
            "CSS селектор: `.footer`",
            "Общий блок для всех страниц, не учитывается при определении типа страницы"
        ]
        return "; ".join(parts)


def describe_top_back(element, heading):
    """
    Describe Hero block (top-back section).

    Args:
        element: BeautifulSoup element
        heading: Block heading text

    Returns:
        Description string with block details and search fields
    """
    parts = [
        "Hero блок с заголовком раздела"
    ]

    if heading:
        parts[0] += f" (заголовок: \"{heading}\")"

    # Проверяем наличие поиска
    search_box = element.find(class_=re.compile(r'search'))
    if search_box:
        parts.append("Включает форму поиска недвижимости")

        # Анализируем поля поиска
        inputs = search_box.find_all('input')
        fields = []
        for inp in inputs:
            name = inp.get('name', '')
            placeholder = inp.get('placeholder', '')
            if name or placeholder:
                field_desc = placeholder if placeholder else name
                fields.append(f"'{field_desc}'")

        if fields:
            parts.append(f"Поля поиска: {', '.join(fields)}")

    parts.append("CSS селектор: `.top-back`")

    return "; ".join(parts)


def describe_block_detailed(element, block_id, heading):
    """
    Create detailed block description based on its content.

    Args:
        element: BeautifulSoup element
        block_id: Block ID attribute
        heading: Block heading text

    Returns:
        Semicolon-separated description string
    """

    descriptions = []

    # Analysis by block ID - predefined descriptions for known blocks
    block_descriptions = {
        'actions': 'Анонсы акций ("Самое интересное"). Карточки с баннерами для акций: графическая подложка, аудитория, текст предложения, датой проведения',
        'special': 'Секция с объектами недвижимости ("Суперпредложения"). Карточки объектов с превью, кнопками "к сравнению" и "в избранное", адресом, типом объекта и параметрами (площадь, этаж, направление)',
        'services': 'Быстрые ссылки на разделы услуг ("Услуги"). Иконки с названием услуги со ссылками на страницы услуг',
        'news': 'Новости сайта. Карточки новостей с превью, тегом, датой и кратким анонсом',
        'add': 'Переходы к служебным разделам: "Проверено МИЭЛЬ", "Аналитика цен", "Работа в офисе"',
        'word': 'Обращение руководителя. Фото генерального директора, текст обращения',
        'last-video-reviews': 'Видеоотзывы. Видео с Rutube с описанием (имя клиента) и датой. Ссылка перехода в раздел видеоотзывов',
        'form': 'Форма обратной связи ("Не нашли ответ на свой вопрос?"). Поля: имя, телефон, email, кнопка отправки',
        'filter': 'Форма фильтрации и поиска. Поля для выбора параметров фильтрации, кнопки применения фильтров',
        'search-inner': 'Расширенный поиск недвижимости. Фильтры по параметрам: тип сделки, тип объекта, цена, площадь, этаж и другие параметры',
        'news-detail': 'Детальное содержание новости. Заголовок, дата публикации, автор, полный текст новости с изображениями',
        'other-news': 'Навигация по другим новостям. Ссылки на предыдущую и следующую новость, превью связанной новости',
        'office': 'Фотографии офиса. Галерея фотографий офисных помещений с возможностью просмотра в полном размере',
        'team': 'Информация о команде сотрудников. Карточки специалистов с фото, должностью, контактами',
        'reviews': 'Отзывы клиентов. Галерея отзывов с текстом, фото, именем автора и датой',
        'faq-list': 'Список часто задаваемых вопросов. Категории вопросов с раскрывающимися ответами',
        'advantages': 'Преимущества компании. Блок с иконками и описанием ключевых преимуществ работы с компанией',
        'stages': 'Этапы работы. Пошаговое описание процесса оказания услуги с нумерацией',
        'consultation': 'Блок консультации. Информация о специалисте, контакты, кнопка записи на консультацию',
        'contacts-info': 'Контактная информация офиса. Адрес, телефоны, время работы, социальные сети',
        'map': 'Карта проезда. Интерактивная карта Яндекс с отметкой расположения офиса',
        'content-list': 'Список материалов (новости, статьи, аналитика). Контейнер с карточками контента в сетке',
        'pagination': 'Навигация по страницам (пагинация). Ссылки на предыдущую/следующую страницу, номера страниц',
    }

    # First try to find predefined description by ID
    if block_id in block_descriptions:
        descriptions.append(block_descriptions[block_id])
    else:
        # Analyze block content
        text = element.get_text()[:1000].lower()

        # Check for forms
        forms = element.find_all('form')
        has_form = len(forms) > 0

        # Check for images
        images = element.find_all('img')
        has_images = len(images) > 0

        # Check for cards/list items
        cards = element.find_all(class_=re.compile(r'card|item|element'))
        has_cards = len(cards) > 0

        # Determine content type
        if has_form:
            descriptions.append("форма обратной связи или заявки")

        if 'отзыв' in text or 'review' in block_id.lower():
            if 'video' in block_id.lower():
                descriptions.append("видеоотзывы клиентов")
            else:
                descriptions.append("текстовые отзывы клиентов")
        elif 'новост' in text or 'news' in block_id.lower():
            descriptions.append("блок новостей")
        elif 'акци' in text or 'action' in block_id.lower() or 'скидк' in text:
            descriptions.append("акции и специальные предложения")
        elif 'услуг' in text or 'service' in block_id.lower():
            descriptions.append("каталог услуг компании")
        elif 'команд' in text or 'team' in block_id.lower() or 'сотрудник' in text:
            descriptions.append("информация о команде сотрудников")
        elif 'контакт' in text or 'contact' in block_id.lower() or 'адрес' in text:
            descriptions.append("контактная информация")
        elif 'вопрос' in text or 'faq' in block_id.lower():
            descriptions.append("часто задаваемые вопросы и ответы")
        elif 'преимуществ' in text or 'advantage' in block_id.lower():
            descriptions.append("преимущества работы с компанией")
        elif 'этап' in text or 'stage' in block_id.lower() or 'step' in text:
            descriptions.append("этапы оказания услуги")
        elif 'объект' in text or 'flat' in text or 'квартир' in text or 'недвижимост' in text:
            descriptions.append("каталог объектов недвижимости")
        elif 'поиск' in text or 'search' in block_id.lower() or 'фильтр' in text:
            descriptions.append("форма поиска и фильтрации объектов")
        elif has_cards and has_images:
            descriptions.append("галерея карточек с изображениями")
        elif has_images:
            descriptions.append("изображения и фотографии")
        else:
            descriptions.append("текстовый информационный блок")

    # Add heading if present
    if heading:
        descriptions.insert(0, f"Заголовок: \"{heading}\"")

    # Add CSS selector
    descriptions.append(f"CSS селектор: `#{block_id}`")

    return "; ".join(descriptions)


def get_block_signature(blocks):
    """
    Create block signature tuple for grouping pages by type.
    Excludes common blocks (mainheader, footer) from signature.

    Args:
        blocks: List of block dictionaries

    Returns:
        Sorted tuple of content block IDs
    """
    # Exclude common blocks (mainheader, footer) from signature
    content_blocks = [b['id'] for b in blocks if not b.get('is_common')]
    return tuple(sorted(content_blocks))


def classify_page_type(page_info):
    """
    Classify page type based on URL path and structure.

    Args:
        page_info: Dictionary with url, rel_path, and other page data

    Returns:
        Russian page type name string
    """
    url = page_info['url']
    path = page_info['rel_path']

    # Main page
    if path == 'index.html':
        return "Главная страница"

    # News pages
    if 'новости/' in path or 'новости-офиса/' in path:
        if path.endswith('/index.html') and path.count('/') == 1:
            return "Список новостей"
        else:
            return "Страница новости"

    # Promotions pages
    if 'акции-и-скидки/' in path:
        if path.endswith('акции-и-скидки/index.html'):
            return "Список акций"
        else:
            return "Детальная страница акции"

    # Service pages
    if 'услуги/' in path:
        if path.endswith('услуги/index.html'):
            return "Список услуг"
        else:
            return "Страница услуги"

    # Property catalog pages
    if any(x in path for x in ['1k-', '2k-', '3k-', 'студии', 'аренда']):
        return "Каталог объектов недвижимости"

    # Property detail pages
    if 'объекты/' in path:
        return "Детальная страница объекта"

    # Team pages
    if 'команда-миэль/' in path:
        if path == 'команда-миэль/index.html':
            return "Список сотрудников"
        else:
            return "Профиль сотрудника"

    # Service pages
    if path in ['контакты/index.html', 'о-компании/index.html', 'вакансии/index.html']:
        page_names = {
            'контакты/index.html': 'Контакты',
            'о-компании/index.html': 'О компании',
            'вакансии/index.html': 'Вакансии'
        }
        return page_names.get(path, "Служебная страница")

    # FAQ pages
    if 'часто-задаваемы-вопросы/' in path:
        if path == 'часто-задаваемы-вопросы/index.html':
            return "Список FAQ"
        else:
            return "Детальная страница FAQ"

    # Reviews pages
    if 'список-отзывов/' in path:
        return "Список отзывов"

    # Analytics pages
    if 'аналитика/' in path:
        return "Аналитика"

    # Search results pages
    if 'search/' in path:
        return "Результаты поиска"

    # New buildings pages
    if 'новостройки/' in path:
        if path.endswith('новостройки/index.html'):
            return "Список новостроек"
        else:
            return "Детальная страница новостройки"

    # Realty (favorites, comparisons)
    if 'realty/' in path:
        return "Личный кабинет (избранное/сравнение)"

    # Pages (sitemap and others)
    if 'pages/' in path:
        return "Служебная страница"

    # Default - determine by URL pattern
    if any(x in url for x in ['/1k-', '/2k-', '/3k-', '/студии', '/аренда']):
        return "Каталог недвижимости"

    return "Другая страница"


def wrap_text(text, width=70):
    """
    Wrap long text lines to specified width (default 90 characters).
    Preserves existing line breaks and wraps only long lines.

    Args:
        text: Input text string
        width: Maximum line width (default 90)

    Returns:
        Text with wrapped lines
    """
    if not text or len(text) <= width:
        return text

    # Split by existing newlines first
    paragraphs = text.split('\n')
    wrapped_paragraphs = []

    for paragraph in paragraphs:
        if len(paragraph) <= width:
            wrapped_paragraphs.append(paragraph)
        else:
            # Wrap long lines at word boundaries
            words = paragraph.split(' ')
            lines = []
            current_line = ""

            for word in words:
                if not current_line:
                    current_line = word
                elif len(current_line) + 1 + len(word) <= width:
                    current_line += " " + word
                else:
                    lines.append(current_line)
                    current_line = word

            if current_line:
                lines.append(current_line)

            wrapped_paragraphs.extend(lines)

    return '\n'.join(wrapped_paragraphs)


def format_block_for_yaml(block, is_example=True):
    """
    Format block description for YAML output (legacy function, not currently used).

    Args:
        block: Block dictionary with id, heading, description
        is_example: Whether this is an example block

    Returns:
        Formatted string with block information
    """
    lines = []

    # Block heading
    if block.get('heading'):
        lines.append(f"- {block['heading']}")
    else:
        # If no heading, use ID
        lines.append(f"- Блок `{block['id']}`")

    # Description
    if block.get('description'):
        # Разбиваем описание по точкам с запятой
        parts = block['description'].split('; ')
        for part in parts:
            if part.strip():
                lines.append(f"  {part.strip()}")

    # Отмечаем общие блоки
    if block.get('is_common'):
        lines.append("  Общий блок для всех страниц, не учитывается при определении типа страницы")

    return '\n'.join(lines)


def main():
    """
    Main function to analyze all HTML pages.

    Environment Variables:
        ZDKVARTIRA_BASE_URL: Base URL for the website (default: https://zdkvartira.ru)
    """

    # Calculate paths relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.join(script_dir, 'analyze-sources', 'zdkvartira.ru')
    output_dir = os.path.join(script_dir, 'results')
    page_types_dir = os.path.join(output_dir, 'page-types')
    page_lists_dir = os.path.join(output_dir, 'page-lists')

    print(f"Configuration:")
    print(f"  Base URL: {BASE_URL}")
    print(f"  Source directory: analyze-sources/zdkvartira.ru")
    print(f"  Output directory: results")
    sys.stdout.flush()

    # Создаем директории вывода если не существуют
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(page_types_dir, exist_ok=True)
    os.makedirs(page_lists_dir, exist_ok=True)

    print("\nНачинаю анализ страниц...")
    sys.stdout.flush()

    # Собираем все HTML файлы
    pages = []
    html_files = []

    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.html'):
                html_files.append(os.path.join(root, file))

    print(f"Найдено {len(html_files)} HTML файлов")
    sys.stdout.flush()

    # Анализируем каждую страницу
    for i, html_file in enumerate(html_files, 1):
        if i % 50 == 0:
            print(f"Обработано {i}/{len(html_files)} страниц...")
            sys.stdout.flush()

        try:
            page_info = extract_page_info(html_file, base_url=BASE_URL, base_dir=base_dir)
            page_info['type'] = classify_page_type(page_info)
            pages.append(page_info)
        except Exception as e:
            print(f"Ошибка при обработке {html_file}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\nПроанализировано {len(pages)} страниц")
    sys.stdout.flush()

    # Шаг 1: Создаем pages.txt с табуляцией в качестве разделителя
    print("\nСоздаю pages.txt...")
    sys.stdout.flush()
    with open(os.path.join(output_dir, 'pages.txt'), 'w', encoding='utf-8') as f:
        for page in sorted(pages, key=lambda x: x['url']):
            f.write(f"{page['url']}\t{page['type']}\t{page['title']}\n")

    print(f"Сохранено {len(pages)} страниц в pages.txt")
    sys.stdout.flush()

    # Шаг 1.5: Создаем pages.csv с обязательным квотированием всех текстовых полей
    print("\nСоздаю pages.csv...")
    sys.stdout.flush()
    with open(os.path.join(output_dir, 'pages.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(['url', 'type', 'title'])
        for page in sorted(pages, key=lambda x: x['url']):
            writer.writerow([page['url'], page['type'], page['title']])

    print(f"Сохранено {len(pages)} страниц в pages.csv")
    sys.stdout.flush()

    # Шаг 2: Группируем страницы по типам
    print("\nГруппирую страницы по типам...")
    sys.stdout.flush()
    type_groups = {}

    for page in pages:
        page_type = page['type']
        if page_type not in type_groups:
            type_groups[page_type] = {
                'pages': [],
                'block_signatures': {}
            }

        type_groups[page_type]['pages'].append(page)

        # Группируем по сигнатуре блоков (для выявления подтипов)
        sig = get_block_signature(page['blocks'])
        if sig not in type_groups[page_type]['block_signatures']:
            type_groups[page_type]['block_signatures'][sig] = []
        type_groups[page_type]['block_signatures'][sig].append(page)

    # Выводим статистику по типам
    print("\nСтатистика по типам страниц:")
    sys.stdout.flush()
    for page_type, group_data in sorted(type_groups.items()):
        num_pages = len(group_data['pages'])
        num_subtypes = len(group_data['block_signatures'])
        print(f"  {page_type}: {num_pages} страниц, {num_subtypes} вариантов структуры")
        sys.stdout.flush()

    # Шаг 3: Создаем types.yaml и отдельные файлы для каждого типа
    print("\nСоздаю types.yaml и файлы типов страниц...")
    sys.stdout.flush()

    yaml_data = {}

    # Сначала добавляем Главную страницу (с mainheader и footer)
    if 'Главная страница' in type_groups:
        page_type = 'Главная страница'
        group_data = type_groups[page_type]
        pages_list = group_data['pages']

        example_page = pages_list[0]

        type_info = {
            'id': page_type_to_id(page_type),
            'description': page_type,
            'example_url': example_page['url'],
            'example_title': example_page['title'],
            'total_pages': len(pages_list),
            'blocks': [],
            'pages_count': len(pages_list)
        }

        # Для главной страницы включаем ВСЕ блоки (включая mainheader и footer)
        for block in example_page['blocks']:
            block_info = {
                'id': block['id'],
                'selector': block['selector'],
            }

            if block.get('heading'):
                block_info['heading'] = block['heading']

            if block.get('description'):
                block_info['description'] = block['description']

            if block.get('is_common'):
                block_info['common_block'] = True

            type_info['blocks'].append(block_info)

        yaml_data[page_type] = type_info

    # Затем добавляем остальные типы (без mainheader и footer)
    for page_type, group_data in sorted(type_groups.items()):
        if page_type == 'Главная страница':
            continue

        pages_list = group_data['pages']

        example_page = pages_list[0]

        type_info = {
            'id': page_type_to_id(page_type),
            'description': page_type,
            'example_url': example_page['url'],
            'example_title': example_page['title'],
            'total_pages': len(pages_list),
            'blocks': [],
            'pages_count': len(pages_list)
        }

        # Добавляем только контентные блоки (исключаем mainheader и footer)
        for block in example_page['blocks']:
            if block.get('is_common'):
                continue

            block_info = {
                'id': block['id'],
                'selector': block['selector'],
            }

            if block.get('heading'):
                block_info['heading'] = block['heading']

            if block.get('description'):
                block_info['description'] = block['description']

            type_info['blocks'].append(block_info)

        yaml_data[page_type] = type_info

    # Сохраняем общий types.yaml
    print(f"Сохранено {len(yaml_data)} типов страниц в types.yaml")
    sys.stdout.flush()
    with open(os.path.join(output_dir, 'types.yaml'), 'w', encoding='utf-8') as f:
        yaml.dump(yaml_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False, width=120)

    # Шаг 4: Создаем отдельные Markdown файлы для каждого типа страницы
    print("\nСоздаю отдельные Markdown файлы для каждого типа страницы...")
    sys.stdout.flush()
    for page_type, group_data in type_groups.items():
        pages_list = group_data['pages']
        type_id = page_type_to_id(page_type)
        type_info = yaml_data[page_type]

        # Создаем Markdown файл с описанием типа
        md_filename = f"{type_id}.md"
        with open(os.path.join(page_types_dir, md_filename), 'w', encoding='utf-8') as f:
            # Заголовок
            f.write(f"# {page_type}\n\n")

            # Метаинформация
            f.write(f"**ID:** `{type_info['id']}`\n\n")
            f.write(f"**Example URL:** {type_info['example_url']}\n\n")

            # Wrap long example titles
            example_title = wrap_text(type_info['example_title'])
            f.write(f"**Example Title:** {example_title}\n\n")

            f.write(f"**Total Pages:** {type_info['total_pages']}\n\n")

            # Блоки
            f.write(f"## Content Blocks ({len(type_info['blocks'])})\n\n")

            for i, block in enumerate(type_info['blocks'], 1):
                f.write(f"### {i}. {block['id']}\n\n")
                f.write(f"- **Selector:** `{block['selector']}`\n")

                if block.get('heading'):
                    # Wrap heading if too long
                    heading = wrap_text(block['heading'])
                    f.write(f"- **Heading:** {heading}\n")

                if block.get('description'):
                    # Wrap description text and use plain text without quotes
                    desc = wrap_text(block['description'])
                    f.write(f"- **Description:** {desc}\n")

                if block.get('common_block'):
                    f.write(f"- **Common Block:** Yes\n")

                f.write("\n")

        # Создаем TXT файл со списком страниц в отдельной папке page-lists
        # Используем табуляцию как разделитель: {url}\t{title}
        txt_filename = f"{type_id}.txt"
        with open(os.path.join(page_lists_dir, txt_filename), 'w', encoding='utf-8') as f:
            for page in sorted(pages_list, key=lambda x: x['url']):
                f.write(f"{page['url']}\t{page['title']}\n")

        print(f"  Созданы {md_filename} и {txt_filename} ({len(pages_list)} страниц)")
        sys.stdout.flush()

    print(f"\n✅ Анализ завершен!")
    sys.stdout.flush()
    print(f"📁 Результаты сохранены в: results")
    sys.stdout.flush()
    print(f"   - pages.txt: список всех страниц (TAB-разделитель)")
    sys.stdout.flush()
    print(f"   - pages.csv: список всех страниц в CSV формате")
    sys.stdout.flush()
    print(f"   - types.yaml: все типы страниц с описанием блоков")
    sys.stdout.flush()
    print(f"   - page-types/: описания типов страниц (Markdown)")
    sys.stdout.flush()
    print(f"   - page-lists/: списки страниц по типам (TAB-разделитель, формат: {{type}}.txt)")
    sys.stdout.flush()


if __name__ == '__main__':
    main()
