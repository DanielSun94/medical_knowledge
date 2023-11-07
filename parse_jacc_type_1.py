import os
from util import logger
from util import cache_folder, table_figure_ocr, request_jacc, sanitize_windows_path

root_href = 'https://www.jacc.org'


def is_section(ele):
    next_sibling = ele.nextSibling
    if hasattr(ele, 'name') and ele.name == 'h1' and hasattr(next_sibling, 'name') and next_sibling.name == 'h2' and \
            isinstance(next_sibling.text, str) and len(next_sibling.text) > 0:
        return next_sibling.text
    else:
        return None


def is_subsection(ele):
    next_sibling = ele.nextSibling
    if hasattr(ele, 'name') and ele.name == 'h2' and hasattr(next_sibling, 'name') and next_sibling.name == 'h3' and \
            isinstance(next_sibling.text, str) and len(next_sibling.text) > 0:
        return next_sibling.text
    else:
        return None


def is_subsubsection(ele):
    next_sibling = ele.nextSibling
    if hasattr(ele, 'name') and ele.name == 'h3' and hasattr(next_sibling, 'name') and next_sibling.name == 'h4' and \
            isinstance(next_sibling.text, str) and len(next_sibling.text) > 0:
        return next_sibling.text
    else:
        return None


def is_subsubsubsection(ele):
    next_sibling = ele.nextSibling
    if hasattr(ele, 'name') and ele.name == 'h4' and hasattr(next_sibling, 'name') and next_sibling.name == 'h4' and \
            isinstance(next_sibling.text, str) and len(next_sibling.text) > 0:
        return next_sibling.text
    else:
        return None


def is_subsubsubsubsection(ele):
    next_sibling = ele.nextSibling
    if hasattr(ele, 'name') and ele.name == 'h5' and hasattr(next_sibling, 'name') and next_sibling.name == 'h6' and \
            isinstance(next_sibling.text, str) and len(next_sibling.text) > 0:
        return next_sibling.text
    else:
        return None


def is_paragraph(ele):
    if hasattr(ele, 'name') and ele.name == 'p':
        return ele.text
    else:
        return None


def is_list(ele):
    if hasattr(ele, 'name') and ele.name == 'table' and isinstance(ele.attrs, dict) and 'class' in ele.attrs and \
            'listgroup' in ele.attrs['class']:
        return ele.text
    else:
        return None


def is_table(ele, abbreviation):
    flag_1 = hasattr(ele, 'name') and ele.name == 'div' and isinstance(ele.attrs, dict) and 'class' in ele.attrs and \
             'article-table-content' in ele.attrs['class']
    caption_ele = ele.find('caption')

    if not flag_1 or caption_ele is None:
        return None

    caption, body, head, foot = "", "", "", ""

    body_ele = ele.find('tbody')
    head_ele = ele.find('thead')
    foot_ele = ele.find('div', attrs={'class': 'tableFooter'})
    table_label_ele = caption_ele.find('span', attrs={'class': 'captionLabel'})
    if table_label_ele is not None:
        table_title = table_label_ele.text
    else:
        table_title = sanitize_windows_path(caption_ele.text[0:50], "_")

    table_cache_folder = os.path.join(cache_folder, abbreviation, table_title)
    if os.path.exists(table_cache_folder):
        with open(os.path.join(table_cache_folder, 'table_title.txt'), 'r', encoding='utf-8-sig') as f:
            table_title = f.read()
        with open(os.path.join(table_cache_folder, 'table_content.txt'), 'r', encoding='utf-8-sig') as f:
            content_str = f.read()
        return table_title, content_str

    if caption_ele is not None:
        caption = caption_ele.text
    if head_ele is not None:
        head = remove_style(body_ele).prettify()
    if foot_ele is not None:
        foot = foot_ele.text
    if body_ele is not None:
        image_table = body_ele.find('div', attrs={'class': 'imageTable'})
        if image_table is None:
            body = remove_style(body_ele).prettify()
            content_str = caption + "\n" + head + '\n' + body + '\n' + foot
        else:
            figure_urls = [root_href + ele.get('data-lg-src') for ele in image_table.findAll('img')]
            figure_folder = os.path.join(table_cache_folder, 'figure')
            if not os.path.exists(figure_folder):
                os.makedirs(figure_folder)
                # 存在跨页表
                for j, url in enumerate(figure_urls):
                    driver = request_jacc(url)
                    driver.maximize_window()
                    driver.save_screenshot(os.path.join(figure_folder, '{}.jpg'.format(j + 1)))

            figure_name_list = os.listdir(figure_folder)
            table_str_list = [caption]
            for file_name in figure_name_list:
                idx = file_name.strip().split('.')[0]
                figure_path = os.path.join(figure_folder, file_name)
                table_str_list.append(table_figure_ocr(figure_path, table_cache_folder, idx))
            table_str_list.append(head)
            table_str_list.append(foot)
            content_str = '\n'.join(table_str_list)
    else:
        content_str = ""

    os.makedirs(table_cache_folder, exist_ok=True)
    with open(os.path.join(table_cache_folder, 'table_content.txt'), 'w', encoding='utf-8-sig') as f:
        f.write(content_str)
    with open(os.path.join(table_cache_folder, 'table_title.txt'), 'w', encoding='utf-8-sig') as f:
        f.write(table_title)
    return table_title, content_str


def remove_style(ele):
    ele.attrs = {}
    for tag in ele.findAll(True):
        tag.attrs = {}
    return ele


def is_figure(ele, abbreviation):
    if not (ele.name == 'section' and isinstance(ele.attrs, dict) and 'class' in ele.attrs and
            'article-section__inline-figure' in ele.attrs['class']):
        return None

    caption_ele = ele.find('span', attrs={'class': 'captionLabel'})
    full_caption_ele = ele.find('figcaption', attrs={'class': 'figure__caption'})
    if caption_ele is None or full_caption_ele is None:
        return None

    caption = caption_ele.text

    figure_cache_folder = os.path.join(cache_folder, abbreviation, caption)
    if not os.path.exists(figure_cache_folder):
        full_caption = full_caption_ele.text
        figure_start_idx = full_caption.find('Figure')
        full_caption = full_caption[figure_start_idx:]

        figure_url = root_href + ele.find('img', attrs={"class": 'figure__image'}).get('data-lg-src')

        driver = request_jacc(figure_url)
        driver.maximize_window()

        os.makedirs(figure_cache_folder)
        driver.save_screenshot(os.path.join(figure_cache_folder, 'figure.jpg'))
        with open(os.path.join(figure_cache_folder, 'figure.jpg'), 'rb') as f:
            figure = f.read()
        with open(os.path.join(figure_cache_folder, 'caption.txt'), 'w', encoding='utf-8-sig') as f:
            f.write(full_caption)
    else:
        with open(os.path.join(figure_cache_folder, 'figure.jpg'), 'rb') as f:
            figure = f.read()
        with open(os.path.join(figure_cache_folder, 'caption.txt'), 'r', encoding='utf-8-sig') as f:
            full_caption = f.read()
    return caption, full_caption, figure


def parse_jacc_type_1_dom(abbreviation, dom):
    doc_title = dom.find('h1').text
    content_div = dom.find('div', attrs={'class': 'hlFld-Fulltext'})
    content_list = content_div.contents
    start_idx = 99999
    for i, item in enumerate(content_list):
        if is_section(item):
            start_idx = i
            break
    if start_idx == 99999:
        raise ValueError('Start Point Not Found Error')

    none_str = 'none'
    content_dict = {'title': {none_str: {none_str: {none_str: {'text': [doc_title], 'figure': {}, "table": {}}}}}}
    sec_ptr, subsec_ptr, subsubsec_ptr, subsubsubsec_ptr = none_str, none_str, none_str, none_str

    current_idx, next_idx = start_idx, start_idx
    while next_idx < len(content_list):
        current_idx = next_idx
        item = content_list[current_idx]
        if is_section(item):
            sec_ptr = is_section(item)
            logger.info('Section: {}'.format(sec_ptr))
            # 这个编号要看看是不是jacc都是这样
            subsec_ptr = none_str
            subsubsec_ptr = none_str
            subsubsubsec_ptr = none_str
            content_dict[sec_ptr] = {none_str: {none_str: {none_str: {'text': [], 'figure': {}, "table": {}}}}}
            next_idx += 2

        elif is_subsection(item):
            subsec_ptr = is_subsection(item)
            logger.info('Subsection: {}'.format(subsec_ptr))
            subsubsec_ptr = none_str
            subsubsubsec_ptr = none_str
            if subsec_ptr not in content_dict[sec_ptr]:
                content_dict[sec_ptr][subsec_ptr] = {none_str: {none_str: {'text': [], 'figure': {}, "table": {}}}}
            next_idx += 2

        elif is_subsubsection(item):
            subsubsec_ptr = is_subsubsection(item)
            logger.info('Subsubsection: {}'.format(subsubsec_ptr))
            subsubsubsec_ptr = none_str
            if subsubsec_ptr not in content_dict[sec_ptr][subsec_ptr]:
                content_dict[sec_ptr][subsec_ptr][subsubsec_ptr] = {none_str: {'text': [], 'figure': {}, "table": {}}}
            next_idx += 2

        elif is_subsubsubsection(item):
            subsubsubsec_ptr = is_subsubsubsection(item)
            logger.info('Subsubsubsection: {}'.format(subsubsubsec_ptr))
            if subsubsubsec_ptr not in content_dict[sec_ptr][subsec_ptr][subsubsec_ptr]:
                content_dict[sec_ptr][subsec_ptr][subsubsec_ptr][subsubsubsec_ptr] = \
                    {'text': [], 'figure': {}, "table": {}}
            next_idx += 2

        elif is_subsubsubsubsection(item):
            subsubsubsection_ptr = is_subsubsubsection(item)
            logger.info('Subsubsubsection: {}'.format(subsubsubsection_ptr))
            content_dict[sec_ptr][subsec_ptr][subsubsec_ptr][subsubsubsec_ptr]['text']\
                .append("\n{}\n".format(subsubsubsection_ptr))
            next_idx += 2

        elif is_list(item):
            new_item = remove_style(item)
            item_str = new_item.prettify()
            content_dict[sec_ptr][subsec_ptr][subsubsec_ptr][subsubsubsec_ptr]['text'].append(item_str)
            next_idx += 1

        elif is_paragraph(item):
            paragraph_text = is_paragraph(item)
            content_dict[sec_ptr][subsec_ptr][subsubsec_ptr][subsubsubsec_ptr]['text'].append(paragraph_text)
            next_idx += 1

        elif is_table(item, abbreviation):
            caption, table_str = is_table(item, abbreviation)
            content_dict[sec_ptr][subsec_ptr][subsubsec_ptr][subsubsubsec_ptr]['table'][caption] = table_str
            logger.info('Table Caption: {}'.format(caption))
            next_idx += 1

        elif is_figure(item, abbreviation):
            caption, full_caption, figure = is_figure(item, abbreviation)
            content_dict[sec_ptr][subsec_ptr][subsubsec_ptr][subsubsubsec_ptr]['figure'][caption] = full_caption
            logger.info(caption)
            next_idx += 1
        else:
            f_1 = item.name == 'div' and isinstance(item.attrs, dict) and 'class' in item.attrs and \
                     'anchor-spacer' in item.attrs['class']
            f_2 = item.name == 'fn'
            f_3 = item.name == 'p' and len(item.text) == 0
            f_4 = item.name == 'div' and isinstance(item.attrs, dict) and 'class' in item.attrs and \
                'article__references' in item.attrs['class']
            f_5 = item.name == 'div' and isinstance(item.attrs, dict) and 'class' in item.attrs and \
                'NLM_app-group' in item.attrs['class']
            f_6 = item == '\n'
            if not (f_1 or f_2 or f_3 or f_4 or f_5 or f_6):
                logger.info('UNKNOWN ITEM, Please Check')
                logger.info(item)

            next_idx += 1
    return content_dict
