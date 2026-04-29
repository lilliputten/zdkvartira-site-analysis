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
- Excludes broken links (404, 500 errors) and redirected pages (301, 302)
"""

import csv
import os
import re
import shutil
import sys

import yaml
from bs4 import BeautifulSoup

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
        return ''
    # Replace all line break characters with space
    text = re.sub(r'[\n\r\t]+', ' ', text)
    # Replace multiple consecutive spaces with single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def page_type_to_id(page_type):
    """
    Convert page type name to English dash-case ID.

    Args:
        page_type: Page type name (Russian or English)

    Returns:
        English dash-case ID string (e.g., '00-main', 'news-article')
    """
    translations = {
        # Russian names (for backward compatibility)
        'Главная страница': '00-main',
        'Каталог объектов недвижимости': 'property-catalog',
        'Страница новости': 'news-article',
        'Список новостей': 'news-list',
        'Страница услуги': 'service-page',
        'Список услуг': 'service-list',
        'Детальная страница объекта': 'property-object',
        'Контакты': 'contacts',
        'О компании': 'about',
        'Вакансии': 'vacancies',
        'Список сотрудников': 'staff-list',
        'Профиль сотрудника': 'staff-profile',
        'Список акций': 'promotions-list',
        'Детальная страницы акции': 'promotion-detail',
        'Список FAQ': 'faq-list',
        'Детальная страница FAQ': 'faq-detail',
        'Список отзывов': 'reviews-list',
        'Аналитика': 'analytics',
        'Список новостроек': 'new-buildings-list',
        'Детальная страница новостройки': 'new-building-detail',
        'Результаты поиска': 'search-results',
        'Личный кабинет (избранное/сравнение)': 'user-account',
        'Другие страницы': 'other-pages',
        'Служебная страница': 'system-page',
        # English names (preferred)
        'Home Page': '00-main',
        'Property Catalog': 'property-catalog',
        'News Article': 'news-article',
        'News List': 'news-list',
        'Service Page': 'service-page',
        'Service List': 'service-list',
        'Property Object': 'property-object',
        'Contacts': 'contacts',
        'About': 'about',
        'Vacancies': 'vacancies',
        'Staff List': 'staff-list',
        'Staff Profile': 'staff-profile',
        'Promotions List': 'promotions-list',
        'Promotion Detail': 'promotion-detail',
        'FAQ List': 'faq-list',
        'FAQ Detail': 'faq-detail',
        'Reviews List': 'reviews-list',
        'Analytics': 'analytics',
        'New Buildings List': 'new-buildings-list',
        'New Building Detail': 'new-building-detail',
        'Search Results': 'search-results',
        'User Account': 'user-account',
        'Other Pages': 'other-pages',
        'System Page': 'system-page',
    }

    return translations.get(
        page_type, re.sub(r'[^\w\s-]', '', page_type).lower().replace(' ', '-')
    )


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
        return ''

    # Build parent selector chain up to body
    parts = []
    current = parent
    depth = 0
    max_depth = 5  # Limit depth to avoid overly long selectors

    while current and current.name != '[document]' and depth < max_depth:
        parent_id = current.get('id')
        parent_classes = (
            current.get('class') or []
        )  # pyright: ignore[reportArgumentType]

        # Filter utility classes using regex pattern - matches all Bootstrap/Tailwind utility classes
        meaningful_classes = [
            c
            for c in parent_classes
            if not re.match(
                r'^(container|row|col|d-|p[trblxy]?-|m[trblxy]?-|text-|bg-|border-|flex-|justify-|align-|w-|h-|mx-|my-|px-|py-|mt-|mb-|ml-|mr-|pt-|pb-|pl-|pr-|sm-|md-|lg-|xl-|xxl-)',
                c,
                re.IGNORECASE,
            )
        ]

        if parent_id:
            # Found an ID - use it and stop (IDs are unique)
            parts.insert(0, f'#{parent_id}')
            break

        if meaningful_classes:
            class_str = '.'.join(meaningful_classes)
            parts.insert(0, f'{current.name}.{class_str}')
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
        return ''

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
    # Priority 1: Use ID if present - simplify to just the ID
    elem_id = element.get('id')
    if elem_id:
        # When an element has a unique ID, use only the ID without classes
        return f"#{elem_id}"

    # Priority 2: Use class combination with parent context
    classes = element.get('class', [])
    if classes:
        # Filter common utility classes including all spacing utilities
        meaningful_classes = [
            c
            for c in classes
            if not re.match(
                r'^(container|row|col|d-|p[trblxy]?-|m[trblxy]?-|text-|bg-|border-|flex-|justify-|align-|w-|h-|mx-|my-|px-|py-|mt-|mb-|ml-|mr-|pt-|pb-|pl-|pr-|sm-|md-|lg-|xl-|xxl-)',
                c,
                re.IGNORECASE,
            )
        ]

        if meaningful_classes:
            class_selector = '.'.join(meaningful_classes)

            # Check uniqueness without parent
            if len(soup.select(f'.{class_selector}')) == 1:
                return f'.{class_selector}'

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
                    parent_chain.insert(0, f'#{parent_id}')
                    break

                if parent_classes:
                    parent_meaningful = [
                        c
                        for c in parent_classes
                        if not re.match(
                            r'^(container|row|col|d-|p[trblxy]?-|m[trblxy]?-|text-|bg-|border-|flex-|justify-|align-|w-|h-|mx-|my-|px-|py-|mt-|mb-|ml-|mr-|pt-|pb-|pl-|pr-|sm-|md-|lg-|xl-|xxl-)',
                            c,
                            re.IGNORECASE,
                        )
                    ]
                    if parent_meaningful:
                        parent_selector = '.'.join(parent_meaningful)
                        parent_chain.insert(
                            0, f'{parent.name}.{parent_selector}'
                        )

                parent = parent.parent
                depth += 1

            # Build final selector with parent chain
            if parent_chain:
                combined = ' > '.join(
                    parent_chain + [f'{element.name}.{class_selector}']
                )
                # Verify this selector is unique or at least more specific
                if len(soup.select(combined)) <= len(
                    soup.select(f'.{class_selector}')
                ):
                    return combined

            # Fallback: use tag with classes
            return f'{element.name}.{class_selector}'

    # Priority 3: For elements without classes, try to use parent context
    parent = element.parent
    if parent:
        parent_id = parent.get('id')
        if parent_id:
            return f'#{parent_id} > {element.name}'

        parent_classes = parent.get('class', [])
        if parent_classes:
            parent_meaningful = [
                c
                for c in parent_classes
                if not re.match(
                    r'^(container|row|col|d-|p[trblxy]?-|m[trblxy]?-|text-|bg-|border-|flex-|justify-|align-|w-|h-|mx-|my-|px-|py-|mt-|mb-|ml-|mr-|pt-|pb-|pl-|pr-|sm-|md-|lg-|xl-|xxl-)',
                    c,
                    re.IGNORECASE,
                )
            ]
            if parent_meaningful:
                parent_selector = '.'.join(parent_meaningful)
                return f'.{parent_selector} > {element.name}'

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


def extract_property_object_sections(soup):
    """
    Extract specific sections for property-object pages according to requirements.

    Args:
        soup: BeautifulSoup object

    Returns:
        List of block dictionaries with predefined sections
    """
    blocks = []

    # 1. Breadcrumbs (selector: .breadcrumbs)
    breadcrumbs = soup.find(class_='breadcrumbs')
    if breadcrumbs:
        blocks.append({
            'element': breadcrumbs,
            'data': {
                'id': 'breadcrumbs',
                'selector': '.breadcrumbs',
                'parent': generate_parent_selector(breadcrumbs),
                'heading': '',
                'title': 'Навигационная цепочка',
                'description': 'Навигационная цепочка (хлебные крошки)',
                'snippet': '',
                'tag': breadcrumbs.name,
            },
        })

    # 2. ID and view statistics (starting with "ID:")
    # Look for element containing "ID:"
    id_stats_elem = None
    for elem in soup.find_all(['div', 'span', 'p']):
        text = elem.get_text()
        if text and 'ID:' in text and 'просмотров' in text:
            id_stats_elem = elem
            break

    if id_stats_elem:
        blocks.append({
            'element': id_stats_elem,
            'data': {
                'id': 'object-id-stats',
                'selector': generate_specific_selector(soup, id_stats_elem),
                'parent': generate_parent_selector(id_stats_elem),
                'heading': '',
                'title': 'ID и статистика просмотров',
                'description': 'Идентификатор объекта и статистика просмотров',
                'snippet': get_content_snippet(id_stats_elem, max_chars=80),
                'tag': id_stats_elem.name,
            },
        })

    # 3. Title (selector: .object-info__head)
    title_elem = soup.find(class_='object-info__head')
    if title_elem:
        blocks.append({
            'element': title_elem,
            'data': {
                'id': 'object-title',
                'selector': '.object-info__head',
                'parent': generate_parent_selector(title_elem),
                'heading': clean_text(title_elem.get_text()),
                'title': 'Заголовок объекта',
                'description': 'Заголовок объекта недвижимости',
                'snippet': '',
                'tag': title_elem.name,
            },
        })

    # 4. Address with badges (selector: .object-info__address)
    address_elem = soup.find(class_='object-info__address')
    if address_elem:
        blocks.append({
            'element': address_elem,
            'data': {
                'id': 'object-address',
                'selector': '.object-info__address',
                'parent': generate_parent_selector(address_elem),
                'heading': '',
                'title': 'Адрес с метками',
                'description': 'Адрес объекта с информационными метками',
                'snippet': get_content_snippet(address_elem, max_chars=80),
                'tag': address_elem.name,
            },
        })

    # 5. Gallery (big image and thumbnails) (selector: .slick-gallery)
    gallery_elem = soup.find(class_='slick-gallery')
    if gallery_elem:
        blocks.append({
            'element': gallery_elem,
            'data': {
                'id': 'object-gallery',
                'selector': '.slick-gallery',
                'parent': generate_parent_selector(gallery_elem),
                'heading': '',
                'title': 'Галерея изображений',
                'description': 'Галерея с большим изображением и миниатюрами',
                'snippet': '',
                'tag': gallery_elem.name,
            },
        })

    # 6. Details section - contains price, info, links (selector: .object-characters__section)
    # There are multiple .object-characters__section elements, we need to find the first one with price
    details_sections = soup.find_all(class_='object-characters__section')
    if details_sections:
        # First section typically contains price and characteristics
        details_elem = details_sections[0]
        blocks.append({
            'element': details_elem,
            'data': {
                'id': 'object-details',
                'selector': '.object-characters__section',
                'parent': generate_parent_selector(details_elem),
                'heading': '',
                'title': 'Детали объекта',
                'description': 'Цена, характеристики (площадь, этаж), ссылки (скачать информацию, подписаться на изменение цены)',
                'snippet': get_content_snippet(details_elem, max_chars=100),
                'tag': details_elem.name,
            },
        })

    # 7. Realtor agent in charge with contacts (selector: .object-characters__section)
    # This is typically the second .object-characters__section
    if len(details_sections) > 1:
        agent_elem = details_sections[1]
        blocks.append({
            'element': agent_elem,
            'data': {
                'id': 'realtor-agent',
                'selector': '.object-characters__section',
                'parent': generate_parent_selector(agent_elem),
                'heading': '',
                'title': 'Агент-риелтор с контактами',
                'description': 'Информация о риелторе, ответственном за объект, с контактными данными',
                'snippet': get_content_snippet(agent_elem, max_chars=100),
                'tag': agent_elem.name,
            },
        })

    # 8. Mortgage calculator (selector: .ion-calc or #ion-calc)
    mortgage_elem = soup.find(id='ion-calc') or soup.find(class_='ion-calc')
    if mortgage_elem:
        blocks.append({
            'element': mortgage_elem,
            'data': {
                'id': 'mortgage-calculator',
                'selector': '#ion-calc',
                'parent': generate_parent_selector(mortgage_elem),
                'heading': '',
                'title': 'Ипотечный калькулятор',
                'description': 'Калькулятор для расчета ипотечных платежей',
                'snippet': '',
                'tag': mortgage_elem.name,
            },
        })

    # 9. Object description (selector: .object-info__text)
    description_elem = soup.find(class_='object-info__text')
    if description_elem:
        blocks.append({
            'element': description_elem,
            'data': {
                'id': 'object-description',
                'selector': '.object-info__text',
                'parent': generate_parent_selector(description_elem),
                'heading': '',
                'title': 'Описание объекта',
                'description': 'Подробное текстовое описание объекта недвижимости',
                'snippet': get_content_snippet(description_elem, max_chars=150),
                'tag': description_elem.name,
            },
        })

    # 10. Nearby infrastructure objects (selector: .object-info__infrastructure)
    infrastructure_elem = soup.find(class_='object-info__infrastructure')
    if infrastructure_elem:
        blocks.append({
            'element': infrastructure_elem,
            'data': {
                'id': 'nearby-infrastructure',
                'selector': '.object-info__infrastructure',
                'parent': generate_parent_selector(infrastructure_elem),
                'heading': '',
                'title': 'Ближайшая инфраструктура',
                'description': 'Объекты инфраструктуры рядом с недвижимостью (школы, магазины, транспорт)',
                'snippet': '',
                'tag': infrastructure_elem.name,
            },
        })

    # 11. Location on the map (selector: .serial-section > #map)
    map_section = soup.find('section', class_='serial-section')
    map_elem = None
    if map_section:
        map_elem = map_section.find(id='map')

    if map_elem:
        blocks.append({
            'element': map_section or map_elem,
            'data': {
                'id': 'location-map',
                'selector': '.serial-section > #map',
                'parent': generate_parent_selector(map_section or map_elem),
                'heading': '',
                'title': 'Расположение на карте',
                'description': 'Интерактивная карта с местоположением объекта',
                'snippet': '',
                'tag': (map_section or map_elem).name,
            },
        })

    # 12. Similar objects (selector: .object__similars)
    similars_elem = soup.find(class_='object__similars')
    if similars_elem:
        blocks.append({
            'element': similars_elem,
            'data': {
                'id': 'similar-objects',
                'selector': '.object__similars',
                'parent': generate_parent_selector(similars_elem),
                'heading': '',
                'title': 'Похожие объекты',
                'description': 'Список похожих объектов недвижимости',
                'snippet': get_content_snippet(similars_elem, max_chars=100),
                'tag': similars_elem.name,
            },
        })

    return blocks


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
    title = title_tag.get_text().strip() if title_tag else 'Без заголовка'

    # Calculate relative path from base directory
    if base_dir is None:
        # Fallback to script directory if not provided
        base_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'sources',
            'zdkvartira.ru',
        )

    rel_path = os.path.relpath(html_path, start=base_dir)
    rel_path = rel_path.replace('\\', '/')

    # Construct URL
    if rel_path == 'index.html':
        url = base_url + '/'
    else:
        # Remove index.html from path if present
        path_part = rel_path.replace('/index.html', '')
        url = f'{base_url}/{path_part}/'

    # Detect if this is a property-object page
    is_property_object = False
    if 'объекты/' in rel_path:
        # Count path segments after объекты
        path_parts = rel_path.split('/')
        objects_index = path_parts.index('объекты') if 'объекты' in path_parts else -1

        if objects_index >= 0:
            remaining_parts = path_parts[objects_index + 1:]
            # If we have more than 2 parts (category + item), it's a single property
            if len(remaining_parts) > 2:
                is_property_object = True

    # For property-object pages, use custom section extraction
    if is_property_object:
        block_elements_data = extract_property_object_sections(soup)
        blocks = [item['data'] for item in block_elements_data]

        return {
            'url': url,
            'title': title,
            'blocks': blocks,
            'rel_path': rel_path,
        }

    # Extract all blocks in document order (for non-property-object pages)
    blocks = []

    # Track all elements with their position in the document
    block_elements = []

    # Search for section elements - process both with ID and with meaningful classes
    for section in soup.find_all('section'):
        block_id = section.get('id')

        # Skip technical ids
        if block_id and block_id in [
            'fav-count',
            'slideContainer',
            'pinContainer',
            'slide-block',
        ]:
            continue

        # If no ID, check if section has meaningful classes that can serve as identifier
        if not block_id:
            classes = (
                section.get('class') or []
            )  # pyright: ignore[reportArgumentType]
            # Filter out utility classes to see if there are meaningful ones
            meaningful_classes = [
                c
                for c in classes
                if c
                not in [
                    'container',
                    'row',
                    'col',
                    'col-md',
                    'col-lg',
                    'col-sm',
                    'pb-5',
                    'pt-5',
                    'mb-5',
                    'mt-5',
                    'py-5',
                    'my-5',
                    'pb-3',
                    'pt-3',
                    'mb-3',
                    'mt-3',
                    'pt-0',
                    'pb-0',
                    'mb-0',
                    'mt-0',
                    'p-0',
                    'm-0',
                ]
            ]

            # Only process if section has at least one meaningful class
            if not meaningful_classes:
                continue

            # Use first meaningful class as block_id
            block_id = meaningful_classes[0]

        # Determine CSS selector using improved method
        selector = generate_specific_selector(soup, section)

        # Extract block heading (h1, h2, or .caption)
        heading = ''
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
        human_title = generate_human_readable_title(
            block_id, heading, description
        )

        block_elements.append(
            {
                'element': section,
                'data': {
                    'id': block_id,
                    'selector': selector,
                    'parent': parent_selector,
                    'heading': clean_text(heading),
                    'title': clean_text(human_title),
                    'description': clean_text(description),
                    'snippet': clean_text(snippet) if snippet else '',
                    'tag': 'section',
                },
            }
        )

    # Track processed elements to avoid duplicates
    processed_elements = set()

    # Also search for important blocks without section tag
    # Check divs, uls, navs, ps, and other elements
    for element in soup.find_all(['div', 'ul', 'nav', 'aside', 'p']):
        elem_id = element.get('id')
        elem_classes = (
            element.get('class') or []
        )  # pyright: ignore[reportArgumentType]
        elem_name = element.name

        # Skip if already processed
        elem_key = id(element)
        if elem_key in processed_elements:
            continue

        # Skip already processed sections
        if element.parent and element.parent.name == 'section':
            continue

        # Check for mainheader and footer (only in divs)
        if elem_name == 'div' and (
            'mainheader' in elem_classes or 'footer' in elem_classes
        ):
            block_type = (
                'mainheader' if 'mainheader' in elem_classes else 'footer'
            )
            desc = describe_header_footer(element, block_type)

            # Generate human-readable title
            human_title = generate_human_readable_title(block_type, '', desc)

            # Generate parent selector
            parent_selector = generate_parent_selector(element)

            block_elements.append(
                {
                    'element': element,
                    'data': {
                        'id': block_type,
                        'selector': f'.{block_type}',
                        'parent': parent_selector,
                        'heading': '',
                        'title': clean_text(human_title),
                        'description': clean_text(desc),
                        'snippet': '',
                        'tag': 'div',
                        'is_common': True,
                    },
                }
            )
            processed_elements.add(elem_key)
            continue

        # Filter form (#filter) - can be any element type
        if elem_id == 'filter':
            desc = 'Форма фильтрации и поиска. Поля для выбора параметров фильтрации, кнопки применения фильтров'
            human_title = generate_human_readable_title('filter', '', desc)
            parent_selector = generate_parent_selector(element)

            block_elements.append(
                {
                    'element': element,
                    'data': {
                        'id': 'filter',
                        'selector': '#filter',
                        'parent': parent_selector,
                        'heading': '',
                        'title': clean_text(human_title),
                        'description': clean_text(desc),
                        'snippet': '',
                        'tag': elem_name,
                    },
                }
            )
            processed_elements.add(elem_key)
            continue

        # top-back block (only in divs)
        if elem_name == 'div' and 'top-back' in elem_classes:
            heading_text = ''
            caption = element.find(class_='caption')
            if caption:
                heading_text = caption.get_text().strip()

            desc = describe_top_back(element, heading_text)
            human_title = generate_human_readable_title(
                'top-back', heading_text, desc
            )
            parent_selector = generate_parent_selector(element)

            block_elements.append(
                {
                    'element': element,
                    'data': {
                        'id': 'top-back',
                        'selector': '.top-back',
                        'parent': parent_selector,
                        'heading': clean_text(heading_text),
                        'title': clean_text(human_title),
                        'description': clean_text(desc),
                        'snippet': '',
                        'tag': 'div',
                    },
                }
            )
            processed_elements.add(elem_key)
            continue

        # breadcrumbs (any element type)
        if 'breadcrumbs' in elem_classes:
            # Generate more specific selector
            selector = generate_specific_selector(soup, element)
            desc = 'Навигационная цепочка (хлебные крошки)'
            human_title = generate_human_readable_title(
                'breadcrumbs', '', desc
            )
            parent_selector = generate_parent_selector(element)

            block_elements.append(
                {
                    'element': element,
                    'data': {
                        'id': 'breadcrumbs',
                        'selector': selector,
                        'parent': parent_selector,
                        'heading': '',
                        'title': clean_text(human_title),
                        'description': clean_text(desc),
                        'snippet': '',
                        'tag': elem_name,
                    },
                }
            )
            processed_elements.add(elem_key)
            continue

        # Page title (p.caption) - appears on various pages
        if elem_name == 'p' and 'caption' in elem_classes:
            caption_text = element.get_text().strip()
            if caption_text:
                desc = f'Заголовок страницы: "{caption_text}"'
                human_title = caption_text
                parent_selector = generate_parent_selector(element)

                block_elements.append(
                    {
                        'element': element,
                        'data': {
                            'id': 'page-title',
                            'selector': 'p.caption',
                            'parent': parent_selector,
                            'heading': '',
                            'title': clean_text(human_title),
                            'description': clean_text(desc),
                            'snippet': '',
                            'tag': 'p',
                        },
                    }
                )
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

            block_elements.append(
                {
                    'element': element,
                    'data': {
                        'id': 'newhousing-item',
                        'selector': '.newhousing-item',
                        'parent': parent_selector,
                        'heading': '',
                        'title': clean_text(human_title),
                        'description': clean_text(desc),
                        'snippet': '',
                        'tag': 'div',
                    },
                }
            )
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
            content_children = element.find_all(
                ['article', 'div'],
                class_=re.compile(r'news|article|post|card'),
            )

            # Also check for common news/article structures
            if len(content_children) < 3:
                # Try alternative pattern: look for repeated similar structures
                # that have images, titles, and dates (typical news card pattern)
                potential_cards = element.find_all(
                    'div', class_=re.compile(r'd-flex|col-')
                )
                cards_with_content = []
                for card in potential_cards:
                    has_image = card.find('img')
                    has_link = card.find('a')
                    has_text = card.find(string=re.compile(r'.{20,}'))
                    if has_image and has_link and has_text:
                        cards_with_content.append(card)
                content_children = cards_with_content

            # Filter out navigation and menu items
            content_items = [
                c
                for c in content_children
                if not c.parent
                or 'nav'
                not in str(
                    c.parent.get('class') or []
                )  # pyright: ignore[reportArgumentType]
            ]

            # Only mark as content-list if we have substantial content AND no better ID exists
            if (
                len(content_items) >= 3
            ):  # At least 3 content items indicates a list
                # Generate more specific selector using parent context
                selector = generate_specific_selector(soup, element)

                # Get snippet for identification
                snippet = get_content_snippet(element, max_chars=100)

                desc = 'Список материалов (новости, статьи, аналитика). Контейнер с карточками контента'
                human_title = generate_human_readable_title(
                    'content-list', '', desc
                )
                parent_selector = generate_parent_selector(element)

                block_elements.append(
                    {
                        'element': element,
                        'data': {
                            'id': 'content-list',
                            'selector': selector,
                            'parent': parent_selector,
                            'heading': '',
                            'title': clean_text(human_title),
                            'description': clean_text(desc),
                            'snippet': clean_text(snippet) if snippet else '',
                            'tag': 'div',
                        },
                    }
                )
                processed_elements.add(elem_key)
                continue

        # Pagination navigation (nav element or .pagination)
        if elem_name == 'nav' or 'pagination' in ' '.join(
            elem_classes or []
        ):  # pyright: ignore[reportArgumentType]
            # Check if it contains pagination-like content
            has_page_links = bool(
                element.find_all(
                    'a', href=re.compile(r'\?page=|/page/|\?PAGEN')
                )
            )
            has_numbers = bool(element.find_all(string=re.compile(r'^\d+$')))
            has_next_prev = bool(
                element.find_all(
                    string=re.compile(r'следующая|предыдущая|next|prev', re.I)
                )
            )

            if (
                has_page_links
                or has_numbers
                or has_next_prev
                or 'pagination'
                in ' '.join(
                    elem_classes or []
                )  # pyright: ignore[reportArgumentType]
            ):
                desc = 'Навигация по страницам (пагинация). Ссылки на предыдущую/следующую страницу, номера страниц'
                human_title = generate_human_readable_title(
                    'pagination', '', desc
                )
                parent_selector = generate_parent_selector(element)

                block_elements.append(
                    {
                        'element': element,
                        'data': {
                            'id': 'pagination',
                            'selector': 'nav'
                            if elem_name == 'nav'
                            else f".{'.'.join(elem_classes or [])}",  # pyright: ignore[reportArgumentType]
                            'parent': parent_selector,
                            'heading': '',
                            'title': clean_text(human_title),
                            'description': clean_text(desc),
                            'snippet': '',
                            'tag': elem_name,
                        },
                    }
                )
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

    return {'url': url, 'title': title, 'blocks': blocks, 'rel_path': rel_path}


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
            'Главное меню и шапка сайта',
            "Содержит: время работы, кнопки 'Избранное' и 'Сравнение', логотип, название 'Офис в Железнодорожном', телефон, главное меню, кнопка подачи заявки, поиск",
            'Общий блок для всех страниц, не учитывается при определении типа страницы',
        ]
        return '; '.join(parts)
    else:
        parts = [
            'Подвал сайта',
            'Содержит: контакты, общая информация, меню навигации',
            'Общий блок для всех страниц, не учитывается при определении типа страницы',
        ]
        return '; '.join(parts)


def describe_top_back(element, heading):
    """
    Describe Hero block (top-back section).

    Args:
        element: BeautifulSoup element
        heading: Block heading text

    Returns:
        Description string with block details and search fields
    """
    parts = ['Hero блок с заголовком раздела']

    if heading:
        parts[0] += f' (заголовок: "{heading}")'

    # Проверяем наличие поиска
    search_box = element.find(class_=re.compile(r'search'))
    if search_box:
        parts.append('Включает форму поиска недвижимости')

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

    return '; '.join(parts)


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
            'изображения и фотографии',
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
            descriptions.append('форма обратной связи или заявки')

        if 'отзыв' in text or 'review' in block_id.lower():
            if 'video' in block_id.lower():
                descriptions.append('видеоотзывы клиентов')
            else:
                descriptions.append('текстовые отзывы клиентов')
        elif 'новост' in text or 'news' in block_id.lower():
            descriptions.append('блок новостей')
        elif 'акци' in text or 'action' in block_id.lower() or 'скидк' in text:
            descriptions.append('акции и специальные предложения')
        elif 'услуг' in text or 'service' in block_id.lower():
            descriptions.append('каталог услуг компании')
        elif (
            'команд' in text
            or 'team' in block_id.lower()
            or 'сотрудник' in text
        ):
            descriptions.append('информация о команде сотрудников')
        elif (
            'контакт' in text
            or 'contact' in block_id.lower()
            or 'адрес' in text
        ):
            descriptions.append('контактная информация')
        elif 'вопрос' in text or 'faq' in block_id.lower():
            descriptions.append('часто задаваемые вопросы и ответы')
        elif 'преимуществ' in text or 'advantage' in block_id.lower():
            descriptions.append('преимущества работы с компанией')
        elif 'этап' in text or 'stage' in block_id.lower() or 'step' in text:
            descriptions.append('этапы оказания услуги')
        elif (
            'объект' in text
            or 'flat' in text
            or 'квартир' in text
            or 'недвижимост' in text
        ):
            descriptions.append('каталог объектов недвижимости')
        elif (
            'поиск' in text or 'search' in block_id.lower() or 'фильтр' in text
        ):
            descriptions.append('форма поиска и фильтрации объектов')
        elif has_cards and has_images:
            descriptions.append('галерея карточек с изображениями')
        elif has_images:
            descriptions.append('изображения и фотографии')
        else:
            descriptions.append('текстовый информационный блок')

    # Note: Heading and CSS selector are stored separately in block data, not in description

    result = '; '.join(descriptions)

    # Capitalize first letter of the description
    if result:
        result = (
            result[0].upper() + result[1:]
            if len(result) > 1
            else result.upper()
        )

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
        English page type name string
    """
    url = page_info['url']
    path = page_info['rel_path']

    # Main page
    if path == 'index.html':
        return 'Home Page'

    # News pages
    if 'новости/' in path or 'новости-офиса/' in path:
        if path.endswith('/index.html') and path.count('/') == 1:
            return 'News List'
        else:
            return 'News Article'

    # Promotions pages
    if 'акции-и-скидки/' in path:
        if path.endswith('акции-и-скидки/index.html'):
            return 'Promotions List'
        else:
            return 'Promotion Detail'

    # Service pages
    if 'услуги/' in path:
        if path.endswith('услуги/index.html'):
            return 'Service List'
        else:
            return 'Service Page'

    # Property catalog pages
    if any(x in path for x in ['1k-', '2k-', '3k-', 'студии', 'аренда']):
        return 'Property Catalog'

    # Property detail pages (property-object) - check before generic objects/ check
    if 'объекты/' in path:
        # Count path segments after объекты
        path_parts = path.split('/')
        objects_index = path_parts.index('объекты') if 'объекты' in path_parts else -1

        if objects_index >= 0:
            # Get parts after 'объекты'
            remaining_parts = path_parts[objects_index + 1:]

            # If we have more than 2 parts (category + item), it's a single property
            # e.g., ['объекты', 'городская-недвижимость', '2-комнатная-квартира-...', 'index.html']
            if len(remaining_parts) > 2:
                return 'Property Object'
            else:
                # This is a category listing (property catalog)
                return 'Property Catalog'

    # Team pages
    if 'команда-миэль/' in path:
        if path == 'команда-миэль/index.html':
            return 'Staff List'
        else:
            return 'Staff Profile'

    # Service pages
    if path in [
        'контакты/index.html',
        'о-компании/index.html',
        'вакансии/index.html',
    ]:
        page_names = {
            'контакты/index.html': 'Contacts',
            'о-компании/index.html': 'About',
            'вакансии/index.html': 'Vacancies',
        }
        return page_names.get(path, 'System Page')

    # FAQ pages
    if 'часто-задаваемы-вопросы/' in path:
        if path == 'часто-задаваемы-вопросы/index.html':
            return 'FAQ List'
        else:
            return 'FAQ Detail'

    # Reviews pages
    if 'список-отзывов/' in path:
        return 'Reviews List'

    # Analytics pages
    if 'аналитика/' in path:
        return 'Analytics'

    # Search results pages
    if 'search/' in path:
        return 'Search Results'

    # New buildings pages
    if 'новостройки/' in path:
        if path.endswith('новостройки/index.html'):
            return 'New Buildings List'
        else:
            return 'New Building Detail'

    # Realty (favorites, comparisons)
    if 'realty/' in path:
        return 'User Account'

    # Pages (sitemap and others)
    if 'pages/' in path:
        return 'System Page'

    # Default - determine by URL pattern
    if any(x in url for x in ['/1k-', '/2k-', '/3k-', '/студии', '/аренда']):
        return 'Property Catalog'

    return 'Other Pages'


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
            current_line = ''
            # First line has reduced width to accommodate title/prefix
            first_line_width = width - title_len

            for word in words:
                if not current_line:
                    current_line = word
                elif len(current_line) + 1 + len(word) <= (
                    first_line_width if not lines else width
                ):
                    current_line += ' ' + word
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
                lines.append(f'  {part.strip()}')

    # Отмечаем общие блоки
    if block.get('is_common'):
        lines.append(
            '  Общий блок для всех страниц, не учитывается при определении типа страницы'
        )

    return '\n'.join(lines)


def generate_analysis_report(yaml_data, output_dir):
    """Generate ANALYSIS.md report with duplicate detection."""
    analysis_path = os.path.join(output_dir, 'ANALYSIS.md')
    total_types = len(yaml_data)
    total_pages = sum(
        info.get('pages_count', 0) for info in yaml_data.values()
    )

    # Build table
    table_rows = []
    for page_type, info in sorted(yaml_data.items()):
        type_id = info.get('id', 'unknown')
        pages_count = info.get('pages_count', 0)
        table_rows.append(f'| {page_type} | `{type_id}` | {pages_count} | 1 |')

    # Detect duplicates by comparing selectors
    potential_duplicates = detect_duplicate_types(yaml_data)

    # Generate report content
    lines = ['# Page Type Analysis Report\n']
    lines.append(
        'This report analyzes page types to identify potential duplicates.\n'
    )
    lines.append('## Summary Statistics\n')
    lines.append(f'**Total Page Types:** {total_types}\n')
    lines.append(f'**Total Pages Analyzed:** {total_pages}\n')
    lines.append('| Page Type | ID | Pages | Variants |')
    lines.append('|---|---|---|---|')
    lines.extend(table_rows)
    lines.append('')
    lines.append('## Potential Duplicates\n')
    lines.append('Page types with similar block structures:\n')

    if potential_duplicates:
        for dup in potential_duplicates:
            lines.append(f'### {dup["type1"]} vs {dup["type2"]}\n')
            lines.append(f'- **Similarity:** {dup["similarity"]:.1%}')
            lines.append(
                f'- **Common Blocks:** {dup["common_blocks"]}/{dup["total_blocks"]}'
            )
            lines.append(f'- **Pages:** {dup["pages1"]} vs {dup["pages2"]}')
            lines.append(
                f'- **IDs:** `{dup["type1_id"]}` vs `{dup["type2_id"]}`\n'
            )
            if dup['similarity'] > 0.9:
                lines.append(
                    '**Recommendation:** HIGH - Consider merging these types.\n'
                )
            elif dup['similarity'] > 0.7:
                lines.append(
                    '**Recommendation:** MEDIUM - Review for possible merge.\n'
                )
            lines.append('')
    else:
        lines.append('No significant duplicates found.\n')

    lines.append('## Recommendations\n')
    if potential_duplicates:
        high = [d for d in potential_duplicates if d['similarity'] > 0.9]
        med = [d for d in potential_duplicates if 0.7 < d['similarity'] <= 0.9]
        if high:
            lines.append(
                f'**High Priority:** {len(high)} pair(s) need review.\n'
            )
        if med:
            lines.append(
                f'**Medium Priority:** {len(med)} pair(s) may need review.\n'
            )
    else:
        lines.append('All page types appear distinct. No action required.\n')

    with open(analysis_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f'Analysis report saved to: ANALYSIS.md')


def detect_duplicate_types(yaml_data):
    """Detect potential duplicate page types by comparing block selectors."""
    potential_duplicates = []
    page_types_list = list(yaml_data.items())

    for i in range(len(page_types_list)):
        for j in range(i + 1, len(page_types_list)):
            type1_name, type1_info = page_types_list[i]
            type2_name, type2_info = page_types_list[j]

            blocks1 = type1_info.get('blocks', [])
            blocks2 = type2_info.get('blocks', [])

            if not blocks1 or not blocks2:
                continue

            selectors1 = set(b.get('selector', '') for b in blocks1)
            selectors2 = set(b.get('selector', '') for b in blocks2)

            if selectors1 and selectors2:
                common = selectors1 & selectors2
                all_sel = selectors1 | selectors2
                similarity = len(common) / len(all_sel)

                if similarity > 0.7:
                    potential_duplicates.append(
                        {
                            'type1': type1_name,
                            'type1_id': type1_info.get('id', ''),
                            'type2': type2_name,
                            'type2_id': type2_info.get('id', ''),
                            'similarity': similarity,
                            'common_blocks': len(common),
                            'total_blocks': len(all_sel),
                            'pages1': type1_info.get('pages_count', 0),
                            'pages2': type2_info.get('pages_count', 0),
                        }
                    )

    potential_duplicates.sort(key=lambda x: x['similarity'], reverse=True)
    return potential_duplicates


def load_excluded_urls(script_dir):
    """
    Load URLs to exclude from analysis (broken links and redirects).

    Args:
        script_dir: Directory containing the script

    Returns:
        Set of URLs to exclude
    """
    excluded_urls = set()
    analyze_sources_dir = os.path.join(script_dir, 'sources')

    # Load broken links
    broken_links_path = os.path.join(analyze_sources_dir, 'broken-links.yaml')
    if os.path.exists(broken_links_path):
        try:
            with open(broken_links_path, 'r', encoding='utf-8') as f:
                broken_links = yaml.safe_load(f)
                if broken_links:
                    for item in broken_links:
                        if 'url' in item:
                            excluded_urls.add(item['url'])
            print(
                f'Loaded {len([u for u in excluded_urls])} broken links to exclude'
            )
        except Exception as e:
            print(f'Warning: Could not load broken-links.yaml: {e}')

    # Load redirected pages
    redirected_pages_path = os.path.join(
        analyze_sources_dir, 'redirected-pages.yaml'
    )
    if os.path.exists(redirected_pages_path):
        try:
            with open(redirected_pages_path, 'r', encoding='utf-8') as f:
                redirected_pages = yaml.safe_load(f)
                if redirected_pages:
                    for item in redirected_pages:
                        if 'url' in item:
                            excluded_urls.add(item['url'])
            print(
                f'Loaded redirected pages to exclude (total excluded: {len(excluded_urls)})'
            )
        except Exception as e:
            print(f'Warning: Could not load redirected-pages.yaml: {e}')

    return excluded_urls


def clean_results_directory(output_dir):
    """
    Clean up the results directory before generating new results.
    Removes all existing files and subdirectories in results/.
    Skips files that cannot be deleted (e.g., locked .swp files).

    Args:
        output_dir: Path to the results directory
    """
    if not os.path.exists(output_dir):
        return
    
    print(f'Cleaning results directory: {output_dir}')
    
    removed_count = 0
    skipped_count = 0
    
    # Walk through directory tree from bottom to top (deepest first)
    for root, dirs, files in os.walk(output_dir, topdown=False):
        # Remove files first
        for file_name in files:
            file_path = os.path.join(root, file_name)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                    removed_count += 1
            except Exception as e:
                # Skip files that can't be deleted (locked temp files, etc.)
                skipped_count += 1
        
        # Then remove directories (except the root output_dir)
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                if os.path.isdir(dir_path):
                    shutil.rmtree(dir_path, ignore_errors=True)
                    removed_count += 1
            except Exception:
                # Skip directories that can't be deleted
                skipped_count += 1
    
    if skipped_count > 0:
        print(f'Results directory cleaned: {removed_count} items removed, {skipped_count} items skipped (locked)')
    else:
        print(f'Results directory cleaned: {removed_count} items removed')


def main():
    """
    Main function to analyze all HTML pages.

    Environment Variables:
        ZDKVARTIRA_BASE_URL: Base URL for the website (default: https://zdkvartira.ru)
    """

    # Calculate paths relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.join(script_dir, 'sources', 'zdkvartira.ru')
    output_dir = os.path.join(script_dir, 'results')
    page_types_dir = os.path.join(output_dir, 'page-types')
    page_lists_dir = os.path.join(output_dir, 'page-lists')

    print(f'Configuration:')
    print(f'  Base URL: {BASE_URL}')
    print(f'  Source directory: sources/zdkvartira.ru')
    print(f'  Output directory: results')
    sys.stdout.flush()

    # Clean results directory before generating new results
    clean_results_directory(output_dir)

    # Create output directories if they don't exist
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(page_types_dir, exist_ok=True)
    os.makedirs(page_lists_dir, exist_ok=True)

    # Load excluded URLs (broken links and redirects)
    print('\nLoading excluded URLs...')
    sys.stdout.flush()
    excluded_urls = load_excluded_urls(script_dir)
    print(f'Total URLs to exclude: {len(excluded_urls)}')
    sys.stdout.flush()

    print('\nStarting page analysis...')
    sys.stdout.flush()

    # Собираем все HTML файлы
    pages = []
    html_files = []
    skipped_count = 0

    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.html'):
                html_path = os.path.join(root, file)

                # Calculate the URL that would correspond to this file
                rel_path = os.path.relpath(html_path, start=base_dir)
                rel_path = rel_path.replace('\\', '/')

                # Construct URL to check against exclusion list
                if rel_path == 'index.html':
                    url = BASE_URL + '/'
                else:
                    path_part = rel_path.replace('/index.html', '')
                    url = f'{BASE_URL}/{path_part}/'

                # Skip if URL is in exclusion list
                if url in excluded_urls:
                    skipped_count += 1
                    continue

                html_files.append(html_path)

    print(f'Найдено {len(html_files)} HTML файлов ({skipped_count} excluded)')
    sys.stdout.flush()

    # Analyze each page
    for i, html_file in enumerate(html_files, 1):
        if i % 50 == 0:
            print(f'Processed {i}/{len(html_files)} pages...')
            sys.stdout.flush()

        try:
            page_info = extract_page_info(
                html_file, base_url=BASE_URL, base_dir=base_dir
            )
            page_info['type'] = classify_page_type(page_info)
            pages.append(page_info)
        except Exception as e:
            # Use relative path in error message
            rel_error_path = os.path.relpath(html_file, start=script_dir)
            print(f'Error processing {rel_error_path}: {e}')
            import traceback

            traceback.print_exc()

    print(f'\nAnalyzed {len(pages)} pages')
    sys.stdout.flush()

    # Step 1: Create pages.txt with tab delimiter
    print('\nCreating pages.txt...')
    sys.stdout.flush()
    with open(
        os.path.join(output_dir, 'pages.txt'), 'w', encoding='utf-8'
    ) as f:
        for page in sorted(pages, key=lambda x: x['url']):
            type_id = page_type_to_id(page['type'])
            f.write(f"{page['url']}\t{type_id}\t{page['title']}\n")

    print(f'Saved {len(pages)} pages to pages.txt')
    sys.stdout.flush()

    # Step 1.5: Create pages.csv with mandatory quoting of all text fields
    print('\nCreating pages.csv...')
    sys.stdout.flush()
    with open(
        os.path.join(output_dir, 'pages.csv'),
        'w',
        encoding='utf-8-sig',
        newline='',
    ) as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(['url', 'type', 'title'])
        for page in sorted(pages, key=lambda x: x['url']):
            type_id = page_type_to_id(page['type'])
            writer.writerow([page['url'], type_id, page['title']])

    print(f'Saved {len(pages)} pages in pages.csv')
    sys.stdout.flush()

    # Step 2: Group pages by type
    print('\nGrouping pages by type...')
    sys.stdout.flush()
    type_groups = {}

    for page in pages:
        page_type = page['type']
        if page_type not in type_groups:
            type_groups[page_type] = {'pages': [], 'block_signatures': {}}

        type_groups[page_type]['pages'].append(page)

        # Group by block signature (for identifying subtypes)
        sig = get_block_signature(page['blocks'])
        if sig not in type_groups[page_type]['block_signatures']:
            type_groups[page_type]['block_signatures'][sig] = []
        type_groups[page_type]['block_signatures'][sig].append(page)

    # Output type statistics
    print('\nType statistics:')
    sys.stdout.flush()
    for page_type, group_data in sorted(type_groups.items()):
        num_pages = len(group_data['pages'])
        num_subtypes = len(group_data['block_signatures'])
        print(
            f'  {page_type}: {num_pages} pages, {num_subtypes} structure variants'
        )
        sys.stdout.flush()

    # Output statistics by type
    print('\nPage type statistics:')
    sys.stdout.flush()
    for page_type, group_data in sorted(type_groups.items()):
        num_pages = len(group_data['pages'])
        num_subtypes = len(group_data['block_signatures'])
        print(
            f'  {page_type}: {num_pages} pages, {num_subtypes} structure variants'
        )
        sys.stdout.flush()

    # Step 3: Create types.yaml and individual files for each page type
    print('\nCreating types.yaml and page type files...')
    sys.stdout.flush()

    yaml_data = {}

    # First add Home Page (with mainheader and footer)
    if 'Home Page' in type_groups:
        page_type = 'Home Page'
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
            'pages_count': len(pages_list),
        }

        # For Home Page include ALL blocks (including mainheader and footer)
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

    # Then add other types (without mainheader and footer)
    for page_type, group_data in sorted(type_groups.items()):
        if page_type == 'Home Page':
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
            'pages_count': len(pages_list),
        }

        # Add only content blocks (exclude mainheader and footer)
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

    # Save the combined types.yaml
    print(f'Saved {len(yaml_data)} page types to types.yaml')
    sys.stdout.flush()
    with open(
        os.path.join(output_dir, 'types.yaml'), 'w', encoding='utf-8'
    ) as f:
        yaml.dump(
            yaml_data,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            width=120,
        )

    # Generate ANALYSIS.md report with duplicate detection
    print('\nGenerating page type analysis report...')
    sys.stdout.flush()
    generate_analysis_report(yaml_data, output_dir)

    # Step 4: Create individual Markdown files for each page type
    print('\nCreating individual Markdown files for each page type...')
    sys.stdout.flush()
    for page_type, group_data in type_groups.items():
        pages_list = group_data['pages']
        type_id = page_type_to_id(page_type)
        type_info = yaml_data[page_type]

        # Create file with type description
        md_filename = f'{type_id}.md'
        with open(
            os.path.join(page_types_dir, md_filename), 'w', encoding='utf-8'
        ) as f:
            # Title
            f.write(f'# {page_type}\n\n')

            # Meta information
            f.write(f"**ID:** `{type_info['id']}`\n\n")
            f.write(f"**Example URL:** {type_info['example_url']}\n\n")

            # Wrap long example titles
            example_title = wrap_text(type_info['example_title'])
            f.write(f'**Example Title:** {example_title}\n\n')

            f.write(f"**Total Pages:** {type_info['total_pages']}\n\n")

            # Blocks
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
                title_from_description = (
                    not block.get('title') and description and display_title
                )
                show_description = description and (
                    not display_title
                    or (
                        description.lower() != display_title.lower()
                        and not title_from_description
                    )
                )

                f.write(f'### {i}. {display_title}\n\n')
                f.write(f"- **Selector:** `{block['selector']}`\n")

                # Add parent selector if present
                if block.get('parent'):
                    parent = wrap_text(block['parent'])
                    f.write(f'- **Parent:** `{parent}`\n')

                # Only show heading if it wasn't used as the title
                if heading and not title_from_heading:
                    title_prefix = '- **Heading:** '
                    heading_text = wrap_text(heading, len(title_prefix))
                    f.write(f'{title_prefix}{heading_text}\n')

                # Show description only if it's different from title
                if show_description:
                    desc_prefix = '- **Description:** '
                    desc_text = wrap_text(description, len(desc_prefix))
                    f.write(f'{desc_prefix}{desc_text}\n')

                # Add content snippet as separate line if present
                if block.get('snippet'):
                    snippet_prefix = '- **Пример содержимого:** '
                    snippet_text = wrap_text(
                        block['snippet'], len(snippet_prefix)
                    )
                    f.write(f'{snippet_prefix}{snippet_text}\n')

                if block.get('common_block'):
                    f.write(f'- **Common Block:** Yes\n')

                f.write('\n')

        # Create TXT file with page list in separate page-lists folder
        # Using tab as delimiter: {url}\t{title}
        txt_filename = f'{type_id}.txt'
        with open(
            os.path.join(page_lists_dir, txt_filename), 'w', encoding='utf-8'
        ) as f:
            for page in sorted(pages_list, key=lambda x: x['url']):
                f.write(f"{page['url']}\t{page['title']}\n")

        print(
            f'  Created {md_filename} and {txt_filename} ({len(pages_list)} pages)'
        )
        sys.stdout.flush()

    print(f'\n[SUCCESS] Analysis completed!')
    sys.stdout.flush()
    print(f'[INFO] Results saved to: results')
    sys.stdout.flush()
    print(f'   - pages.txt: list of all pages (TAB-separated)')
    sys.stdout.flush()
    print(f'   - pages.csv: list of all pages in CSV format')
    sys.stdout.flush()
    print(f'   - types.yaml: all page types with block descriptions')
    sys.stdout.flush()
    print(f'   - page-types/: page type descriptions (Markdown)')
    sys.stdout.flush()
    print(
        f'   - page-lists/: page lists by type (TAB-separated, format: {{type}}.txt)'
    )
    sys.stdout.flush()


if __name__ == '__main__':
    main()
