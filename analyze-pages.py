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


def generate_parent_selector(element):
    """
    Generate a CSS selector for the parent element of the given element.

    Args:
        element: BeautifulSoup element

    Returns:
        Parent CSS selector string, or empty string if no meaningful parent
    """
    parent = element.parent
    if not parent or parent.name == '[document]':
        return ""

    # Build parent selector chain up to body
    parts = []
    current = parent
    depth = 0
    max_depth = 5  # Limit depth to avoid overly long selectors

    while current and current.name != '[document]' and depth < max_depth:
        parent_id = current.get('id')
        parent_classes = current.get('class', [])

        # Filter utility classes but keep more semantic ones
        utility_classes = {
            'container', 'container-fluid', 'row',
            'col', 'col-md', 'col-lg', 'col-sm', 'col-xl', 'col-12', 'col-lg-8', 'col-lg-4',
            'pb-5', 'pt-5', 'mb-5', 'mt-5', 'py-5', 'my-5', 'px-5', 'mx-5',
            'pb-3', 'pt-3', 'mb-3', 'mt-3', 'py-3', 'my-3', 'px-3', 'mx-3',
            'pb-4', 'pt-4', 'mb-4', 'mt-4', 'py-4', 'my-4', 'px-4', 'mx-4',
            'pt-0', 'pb-0', 'mb-0', 'mt-0', 'p-0', 'm-0',
            'd-flex', 'flex-column', 'align-items-center', 'justify-content-center',
            'text-center', 'text-left', 'text-right'
        }
        meaningful_classes = [c for c in parent_classes if c not in utility_classes]

        if parent_id:
            # Found an ID - use it and stop (IDs are unique)
            parts.insert(0, f"#{parent_id}")
            break

        if meaningful_classes:
            class_str = '.'.join(meaningful_classes)
            parts.insert(0, f"{current.name}.{class_str}")
        else:
            # No meaningful identifier, just use tag name
            # But skip generic tags like div unless they're at root level
            if current.name in ['div', 'span'] and depth > 0:
                # Skip generic containers in the middle of the tree
                pass
            else:
                parts.insert(0, current.name)

        current = current.parent
        depth += 1

    if not parts:
        return ""

    return ' > '.join(parts)


def generate_specific_selector(soup, element):
    """
    Generate a more specific CSS selector for an element by analyzing its context.

    Args:
        soup: BeautifulSoup object
        element: The target element

    Returns:
        A specific CSS selector string with parent context when needed
    """
    # Priority 1: Use ID if present
    elem_id = element.get('id')
    if elem_id:
        classes = element.get('class', [])
        # Filter out common utility classes
        meaningful_classes = [c for c in classes if c not in [
            'container', 'row', 'col', 'col-md', 'col-lg', 'col-sm',
            'pb-5', 'pt-5', 'mb-5', 'mt-5', 'py-5', 'my-5', 'pb-3', 'pt-3', 'mb-3', 'mt-3'
        ]]

        if meaningful_classes:
            return f"#{elem_id}.{'.'.join(meaningful_classes)}"
        return f"#{elem_id}"

    # Priority 2: Use class combination with parent context
    classes = element.get('class', [])
    if classes:
        # Filter common classes
        meaningful_classes = [c for c in classes if c not in [
            'container', 'row', 'col', 'col-md', 'col-lg', 'col-sm',
            'pb-5', 'pt-5', 'mb-5', 'mt-5', 'py-5', 'my-5'
        ]]

        if meaningful_classes:
            class_selector = '.'.join(meaningful_classes)

            # Check uniqueness without parent
            if len(soup.select(f".{class_selector}")) == 1:
                return f".{class_selector}"

            # Try with parent context - build parent chain
            parent_chain = []
            parent = element.parent
            depth = 0
            max_depth = 3  # Limit to 3 levels up to avoid overly long selectors

            while parent and depth < max_depth:
                parent_id = parent.get('id')
                parent_classes = parent.get('class', [])

                if parent_id:
                    # Found parent with ID - use it
                    parent_chain.insert(0, f"#{parent_id}")
                    break

                if parent_classes:
                    parent_meaningful = [c for c in parent_classes if c not in [
                        'container', 'row', 'col', 'col-md', 'col-lg', 'col-sm',
                        'pb-5', 'pt-5', 'mb-5', 'mt-5', 'py-5', 'my-5'
                    ]]
                    if parent_meaningful:
                        parent_selector = '.'.join(parent_meaningful)
                        parent_chain.insert(0, f"{parent.name}.{parent_selector}")

                parent = parent.parent
                depth += 1

            # Build final selector with parent chain
            if parent_chain:
                combined = ' > '.join(parent_chain + [f"{element.name}.{class_selector}"])
                # Verify this selector is unique or at least more specific
                if len(soup.select(combined)) <= len(soup.select(f".{class_selector}")):
                    return combined

            # Fallback: use tag with classes
            return f"{element.name}.{class_selector}"

    # Priority 3: For elements without classes, try to use parent context
    parent = element.parent
    if parent:
        parent_id = parent.get('id')
        if parent_id:
            return f"#{parent_id} > {element.name}"

        parent_classes = parent.get('class', [])
        if parent_classes:
            parent_meaningful = [c for c in parent_classes if c not in [
                'container', 'row', 'col', 'col-md', 'col-lg', 'col-sm',
                'pb-5', 'pt-5', 'mb-5', 'mt-5', 'py-5', 'my-5'
            ]]
            if parent_meaningful:
                parent_selector = '.'.join(parent_meaningful)
                return f".{parent_selector} > {element.name}"

    # Last resort: just tag name
    return element.name


def get_content_snippet(element, max_chars=80):
    """
    Extract a short text snippet from an element for identification.

    Args:
        element: BeautifulSoup element
        max_chars: Maximum length of snippet

    Returns:
        Short text snippet
    """
    # Get text, clean it
    text = element.get_text(separator=' ', strip=True)

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)

    # Truncate if too long
    if len(text) > max_chars:
        text = text[:max_chars] + '...'

    return text.strip()


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

    # Search for section elements - process both with ID and with meaningful classes
    for section in soup.find_all('section'):
        block_id = section.get('id')

        # Skip technical ids
        if block_id and block_id in ['fav-count', 'slideContainer', 'pinContainer', 'slide-block']:
            continue

        # If no ID, check if section has meaningful classes that can serve as identifier
        if not block_id:
            classes = section.get('class', [])
            # Filter out utility classes to see if there are meaningful ones
            meaningful_classes = [c for c in classes if c not in [
                'container', 'row', 'col', 'col-md', 'col-lg', 'col-sm',
                'pb-5', 'pt-5', 'mb-5', 'mt-5', 'py-5', 'my-5', 'pb-3', 'pt-3', 'mb-3', 'mt-3',
                'pt-0', 'pb-0', 'mb-0', 'mt-0', 'p-0', 'm-0'
            ]]

            # Only process if section has at least one meaningful class
            if not meaningful_classes:
                continue

            # Use first meaningful class as block_id
            block_id = meaningful_classes[0]

        # Determine CSS selector using improved method
        selector = generate_specific_selector(soup, section)

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

        # Generate detailed block description (without content snippet)
        description = describe_block_detailed(section, block_id, heading)

        # Get content snippet separately
        snippet = get_content_snippet(section, max_chars=100)

        # Generate parent selector
        parent_selector = generate_parent_selector(section)

        # Generate human-readable title
        human_title = generate_human_readable_title(block_id, heading, description)

        block_elements.append({
            'element': section,
            'data': {
                'id': block_id,
                'selector': selector,
                'parent': parent_selector,
                'heading': clean_text(heading),
                'title': clean_text(human_title),
                'description': clean_text(description),
                'snippet': clean_text(snippet) if snippet else '',
                'tag': 'section'
            }
        })

    # Track processed elements to avoid duplicates
    processed_elements = set()

    # Also search for important blocks without section tag
    # Check divs, uls, navs, ps, and other elements
    for element in soup.find_all(['div', 'ul', 'nav', 'aside', 'p']):
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

            # Generate human-readable title
            human_title = generate_human_readable_title(block_type, '', desc)

            # Generate parent selector
            parent_selector = generate_parent_selector(element)

            block_elements.append({
                'element': element,
                'data': {
                    'id': block_type,
                    'selector': f".{block_type}",
                    'parent': parent_selector,
                    'heading': '',
                    'title': clean_text(human_title),
                    'description': clean_text(desc),
                    'snippet': '',
                    'tag': 'div',
                    'is_common': True
                }
            })
            processed_elements.add(elem_key)
            continue

        # Filter form (#filter) - can be any element type
        if elem_id == 'filter':
            desc = 'Форма фильтрации и поиска. Поля для выбора параметров фильтрации, кнопки применения фильтров'
            human_title = generate_human_readable_title('filter', '', desc)
            parent_selector = generate_parent_selector(element)

            block_elements.append({
                'element': element,
                'data': {
                    'id': 'filter',
                    'selector': '#filter',
                    'parent': parent_selector,
                    'heading': '',
                    'title': clean_text(human_title),
                    'description': clean_text(desc),
                    'snippet': '',
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

            desc = describe_top_back(element, heading_text)
            human_title = generate_human_readable_title('top-back', heading_text, desc)
            parent_selector = generate_parent_selector(element)

            block_elements.append({
                'element': element,
                'data': {
                    'id': 'top-back',
                    'selector': '.top-back',
                    'parent': parent_selector,
                    'heading': clean_text(heading_text),
                    'title': clean_text(human_title),
                    'description': clean_text(desc),
                    'snippet': '',
                    'tag': 'div'
                }
            })
            processed_elements.add(elem_key)
            continue

        # breadcrumbs (any element type)
        if 'breadcrumbs' in elem_classes:
            # Generate more specific selector
            selector = generate_specific_selector(soup, element)
            desc = 'Навигационная цепочка (хлебные крошки)'
            human_title = generate_human_readable_title('breadcrumbs', '', desc)
            parent_selector = generate_parent_selector(element)
            
            block_elements.append({
                'element': element,
                'data': {
                    'id': 'breadcrumbs',
                    'selector': selector,
                    'parent': parent_selector,
                    'heading': '',
                    'title': clean_text(human_title),
                    'description': clean_text(desc),
                    'snippet': '',
                    'tag': elem_name
                }
            })
            processed_elements.add(elem_key)
            continue

        # Page title (p.caption) - appears on various pages
        if elem_name == 'p' and 'caption' in elem_classes:
            caption_text = element.get_text().strip()
            if caption_text:
                desc = f'Заголовок страницы: "{caption_text}"'
                human_title = caption_text
                parent_selector = generate_parent_selector(element)
                
                block_elements.append({
                    'element': element,
                    'data': {
                        'id': 'page-title',
                        'selector': 'p.caption',
                        'parent': parent_selector,
                        'heading': '',
                        'title': clean_text(human_title),
                        'description': clean_text(desc),
                        'snippet': '',
                        'tag': 'p'
                    }
                })
                processed_elements.add(elem_key)
                continue

        # Realty object cards (.newhousing-item) - new buildings list
        if elem_name == 'div' and 'newhousing-item' in elem_classes:
            # Extract card details
            caption_elem = element.find(class_='newhousing-item__caption')
            caption = caption_elem.get_text().strip() if caption_elem else ''
            
            type_elem = element.find(class_='newhousing-item__type')
            prop_type = type_elem.get_text().strip() if type_elem else ''
            
            price_elem = element.find(class_='newhousing-item__price')
            price = price_elem.get_text().strip() if price_elem else ''
            
            desc = 'Карточка объекта недвижимости'
            if caption:
                desc += f' с названием: "{caption}"'
            if prop_type:
                desc += f'; тип/адрес: {prop_type}'
            if price:
                desc += f'; цена: {price}'
            
            human_title = caption if caption else 'Карточка новостройки'
            parent_selector = generate_parent_selector(element)
            
            block_elements.append({
                'element': element,
                'data': {
                    'id': 'newhousing-item',
                    'selector': '.newhousing-item',
                    'parent': parent_selector,
                    'heading': '',
                    'title': clean_text(human_title),
                    'description': clean_text(desc),
                    'snippet': '',
                    'tag': 'div'
                }
            })
            processed_elements.add(elem_key)
            continue

        # Content container with news/articles list - IMPROVED DETECTION
        # Only detect if it's truly a content list, not just any container
        if elem_name == 'div' and 'container' in elem_classes and not elem_id:
            # Skip if this container is inside a section we've already processed
            parent_section = element.find_parent('section')
            if parent_section and parent_section.get('id'):
                continue

            # Check for direct content children that look like news/article cards
            # Be more specific about what constitutes a content card
            content_children = element.find_all(['article', 'div'],
                                                 class_=re.compile(r'news|article|post|card'))

            # Also check for common news/article structures
            if len(content_children) < 3:
                # Try alternative pattern: look for repeated similar structures
                # that have images, titles, and dates (typical news card pattern)
                potential_cards = element.find_all('div', class_=re.compile(r'd-flex|col-'))
                cards_with_content = []
                for card in potential_cards:
                    has_image = card.find('img')
                    has_link = card.find('a')
                    has_text = card.find(string=re.compile(r'.{20,}'))
                    if has_image and has_link and has_text:
                        cards_with_content.append(card)
                content_children = cards_with_content

            # Filter out navigation and menu items
            content_items = [c for c in content_children
                           if not c.parent or 'nav' not in str(c.parent.get('class', []))]

            # Only mark as content-list if we have substantial content AND no better ID exists
            if len(content_items) >= 3:  # At least 3 content items indicates a list
                # Generate more specific selector using parent context
                selector = generate_specific_selector(soup, element)

                # Get snippet for identification
                snippet = get_content_snippet(element, max_chars=100)

                desc = 'Список материалов (новости, статьи, аналитика). Контейнер с карточками контента'
                human_title = generate_human_readable_title('content-list', '', desc)
                parent_selector = generate_parent_selector(element)

                block_elements.append({
                    'element': element,
                    'data': {
                        'id': 'content-list',
                        'selector': selector,
                        'parent': parent_selector,
                        'heading': '',
                        'title': clean_text(human_title),
                        'description': clean_text(desc),
                        'snippet': clean_text(snippet) if snippet else '',
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
                desc = 'Навигация по страницам (пагинация). Ссылки на предыдущую/следующую страницу, номера страниц'
                human_title = generate_human_readable_title('pagination', '', desc)
                parent_selector = generate_parent_selector(element)

                block_elements.append({
                    'element': element,
                    'data': {
                        'id': 'pagination',
                        'selector': 'nav' if elem_name == 'nav' else f".{'.'.join(elem_classes)}",
                        'parent': parent_selector,
                        'heading': '',
                        'title': clean_text(human_title),
                        'description': clean_text(desc),
                        'snippet': '',
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
            "Общий блок для всех страниц, не учитывается при определении типа страницы"
        ]
        return "; ".join(parts)
    else:
        parts = [
            "Подвал сайта",
            "Содержит: контакты, общая информация, меню навигации",
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

    return "; ".join(parts)


def generate_human_readable_title(block_id, heading, description):
    """
    Generate a human-readable title for a block based on its ID, heading, and description.
    Priority: 1) Heading (if exists), 2) Predefined title map, 3) Description (if meaningful), 4) Formatted block_id
    
    Args:
        block_id: Block identifier (from id attribute or class name)
        heading: Block heading text (if any)
        description: Block description text
    
    Returns:
        Human-readable title string, or empty string if should be omitted
    """
    
    # Priority 1: If there's a heading, use it as the title
    if heading:
        return heading
    
    # Map of block IDs to human-readable Russian titles
    title_map = {
        'breadcrumbs': 'Навигационная цепочка',
        'object__about': 'Каталог объектов недвижимости',
        'adv-price': 'Планировки и цены',
        'experts': 'Служба показов',
        'map': 'Карта расположения',
        'maps': 'Транспортная доступность',
        'otdelka': 'Типы отделки',
        'help': 'Инфраструктура',
        'advantages': 'Преимущества проекта',
        'serial-section': 'Информационный блок',
        'photos': 'Фотоотчёты',
        'flat-change': 'Взаимозачёт',
        'materials': 'Документация проекта',
        'search-inner': 'Расширенный поиск',
        'search-more': 'Дополнительные фильтры',
        'form': 'Форма обратной связи',
        'special': 'Специальные предложения',
        'search-gray': 'Поиск по каталогу',
        'mainheader': 'Шапка сайта',
        'footer': 'Подвал сайта',
        'filter': 'Фильтр поиска',
        'news': 'Новости',
        'actions': 'Акции',
        'services': 'Услуги',
        'add': 'Дополнительные ссылки',
        'word': 'Обращение руководителя',
        'last-video-reviews': 'Видеоотзывы',
        'news-detail': 'Содержание новости',
        'other-news': 'Другие новости',
        'office': 'Фотографии офиса',
        'team': 'Команда сотрудников',
        'reviews': 'Отзывы клиентов',
        'faq-list': 'Часто задаваемые вопросы',
        'stages': 'Этапы работы',
        'consultation': 'Консультация специалиста',
        'contacts-info': 'Контактная информация',
        'pagination': 'Навигация по страницам',
        'content-list': 'Список материалов',
        'page-title': 'Заголовок страницы',
        'newhousing-item': 'Карточка новостройки',
    }
    
    # Priority 2: If we have a predefined title for this block_id, use it
    if block_id in title_map:
        return title_map[block_id]
    
    # Priority 3: Use description if it's meaningful and different from generic patterns
    # Skip descriptions that are too generic or start with technical terms
    if description:
        # Check if description is meaningful (not just generic patterns)
        generic_patterns = [
            'галерея карточек',
            'текстовый информационный',
            'форма обратной связи',
            'каталог объектов',
            'блок новостей',
            'изображения и фотографии'
        ]
        
        desc_lower = description.lower()
        is_generic = any(pattern in desc_lower for pattern in generic_patterns)
        
        # If description is not generic and not too long, use first part as title
        if not is_generic and len(description) < 100:
            # Take first sentence or first 60 characters
            title_from_desc = description.split(';')[0].strip()
            if len(title_from_desc) > 10 and len(title_from_desc) < 80:
                return title_from_desc
    
    # Priority 4: Fallback - capitalize and format the block_id
    # But only if it looks like a meaningful ID (has underscores or is not just CSS classes)
    
    # Check if block_id looks like a CSS utility class (short, with hyphens, no underscores)
    # Examples: bg-white, py-2, pt-4, col-lg-8
    import re
    is_utility_class = bool(re.match(r'^[a-z]{2,4}-[a-z0-9]+$', block_id))
    
    if is_utility_class:
        # This is a CSS utility class, not a meaningful ID
        # Return empty string - we'll use description as fallback in output
        return ''
    
    if '_' in block_id or '-' in block_id:
        # Replace underscores and hyphens with spaces, capitalize words
        formatted = block_id.replace('_', ' ').replace('-', ' ')
        return formatted.title()
    
    # If block_id is just a simple word, capitalize it
    return block_id.capitalize() if block_id else ''


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

    # Note: Heading and CSS selector are stored separately in block data, not in description

    result = "; ".join(descriptions)

    # Capitalize first letter of the description
    if result:
        result = result[0].upper() + result[1:] if len(result) > 1 else result.upper()

    return result


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


def wrap_text(text, title_len=0, width=80):
    """
    Wrap long text lines to specified width (default 70 characters).
    Preserves existing line breaks and wraps only long lines.
    First line is shorter by title_len to account for prefix text.

    Args:
        text: Input text string
        title_len: Length of prefix/title that appears before wrapped text (default 0)
        width: Maximum line width (default 70)

    Returns:
        Text with wrapped lines, first line adjusted for title_len
    """
    if not text or len(text) <= width:
        return text

    # Split by existing newlines first
    paragraphs = text.split('\n')
    wrapped_paragraphs = []

    for paragraph in paragraphs:
        if len(paragraph) <= width - title_len:
            wrapped_paragraphs.append(paragraph)
        else:
            # Wrap long lines at word boundaries
            words = paragraph.split(' ')
            lines = []
            current_line = ""
            # First line has reduced width to accommodate title/prefix
            first_line_width = width - title_len

            for word in words:
                if not current_line:
                    current_line = word
                elif len(current_line) + 1 + len(word) <= (first_line_width if not lines else width):
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

            # Add parent selector if present
            if block.get('parent'):
                block_info['parent'] = block['parent']

            # Add human-readable title
            if block.get('title'):
                block_info['title'] = block['title']

            if block.get('heading'):
                block_info['heading'] = block['heading']

            if block.get('description'):
                block_info['description'] = block['description']

            # Add content snippet if present
            if block.get('snippet'):
                block_info['snippet'] = block['snippet']

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

            # Add parent selector if present
            if block.get('parent'):
                block_info['parent'] = block['parent']

            # Add human-readable title
            if block.get('title'):
                block_info['title'] = block['title']

            if block.get('heading'):
                block_info['heading'] = block['heading']

            if block.get('description'):
                block_info['description'] = block['description']

            # Add content snippet if present
            if block.get('snippet'):
                block_info['snippet'] = block['snippet']

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
                # Determine what to show as the block header
                display_title = block.get('title', '')
                heading = block.get('heading', '')
                description = block.get('description', '')
                
                # If no meaningful title, use description as fallback
                if not display_title and description:
                    # Use first sentence or first part of description as title
                    display_title = description.split(';')[0].strip()
                    # Cap length to avoid overly long titles
                    if len(display_title) > 80:
                        display_title = display_title[:77] + '...'
                
                # Check if title came from heading
                title_from_heading = heading and display_title == heading
                
                # Determine if we should show description
                # Don't show if it matches the title or if title was derived from description
                title_from_description = not block.get('title') and description and display_title
                show_description = description and (not display_title or (description.lower() != display_title.lower() and not title_from_description))

                f.write(f"### {i}. {display_title}\n\n")
                f.write(f"- **Selector:** `{block['selector']}`\n")

                # Add parent selector if present
                if block.get('parent'):
                    parent = wrap_text(block['parent'])
                    f.write(f"- **Parent:** `{parent}`\n")

                # Only show heading if it wasn't used as the title
                if heading and not title_from_heading:
                    title_prefix = "- **Heading:** "
                    heading_text = wrap_text(heading, len(title_prefix))
                    f.write(f"{title_prefix}{heading_text}\n")

                # Show description only if it's different from title
                if show_description:
                    desc_prefix = "- **Description:** "
                    desc_text = wrap_text(description, len(desc_prefix))
                    f.write(f"{desc_prefix}{desc_text}\n")

                # Add content snippet as separate line if present
                if block.get('snippet'):
                    snippet_prefix = "- **Пример содержимого:** "
                    snippet_text = wrap_text(block['snippet'], len(snippet_prefix))
                    f.write(f"{snippet_prefix}{snippet_text}\n")

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
