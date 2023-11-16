import copy

from util import logger, remove_style, cache_folder, request_get_with_sleep
import os


none_str = 'none'
root_href = 'https://rs.yiigle.com/api/xml/getXmlFileUrl?url='


def parse_cjc_type_1_dom(abbreviation, dom):
    reference_ele_list = dom.find_all('sup')
    for ele in reference_ele_list:
        ele.decompose()
    doc_title = dom.find('div', attrs={'class': 'art_title'}).text
    content_div = dom.find('div', attrs={'class': 'body_content'})
    content_list = content_div.contents
    start_idx = 99999
    for i, item in enumerate(content_list):
        if is_section_ele(item):
            start_idx = i
            break
    if start_idx == 99999:
        raise ValueError('Start Point Not Found Error')

    content_dict = {'title': {none_str: {none_str: {none_str: {'text': [doc_title], 'figure': {}, "table": {}}}}}}
    target_folder = os.path.join(cache_folder, abbreviation)
    os.makedirs(target_folder, exist_ok=True)

    unidentified_number = UnidentifiedNumber()
    for item in content_list[start_idx:]:
        if is_section_ele(item):
            sec_name = parse_section_name(item)
            content_dict[sec_name] = parse_section(item, target_folder, unidentified_number)
    return content_dict


class UnidentifiedNumber(object):
    def __init__(self):
        self.number = 0

    def get_next(self):
        self.number += 1
        number = copy.deepcopy(self.number)
        return number


def is_section_ele(ele):
    if ele.name == 'div' and isinstance(ele.attrs, dict) and 'class' in ele.attrs and 'sec' in ele.attrs['class']:
        return True
    else:
        return False


def is_subsection_ele(ele):
    flag = False
    if ele.name == 'div' and isinstance(ele.attrs, dict) and 'class' in ele.attrs and 'sec' in ele.attrs['class']:
        parent = ele.parent
        if parent.name == 'div' and isinstance(parent.attrs, dict) and 'class' in parent.attrs and 'sec' in \
                parent.attrs['class']:
            flag = True
    return flag


def is_subsubsection_ele(ele):
    flag = False
    if ele.name == 'div' and isinstance(ele.attrs, dict) and 'class' in ele.attrs and 'sec' in ele.attrs['class']:
        parent = ele.parent
        if parent.name == 'div' and isinstance(parent.attrs, dict) and 'class' in parent.attrs and 'sec' in \
                parent.attrs['class']:
            grandparent = ele.parent.parent
            if grandparent.name == 'div' and isinstance(grandparent.attrs, dict) and 'class' \
                    in grandparent.attrs and 'sec' in grandparent.attrs['class']:
                flag = True
    return flag


def is_subsubsubsection(ele):
    flag = False
    if ele.name == 'div' and isinstance(ele.attrs, dict) and 'class' in ele.attrs and 'sec' in ele.attrs['class']:
        parent = ele.parent
        if parent.name == 'div' and isinstance(parent.attrs, dict) and 'class' in parent.attrs and 'sec' in \
                parent.attrs['class']:
            grandparent = ele.parent.parent
            if grandparent.name == 'div' and isinstance(grandparent.attrs, dict) and 'class' \
                    in grandparent.attrs and 'sec' in grandparent.attrs['class']:
                grandgrandparent = ele.parent.parent.parent
                if grandgrandparent.name == 'div' and isinstance(grandgrandparent.attrs, dict) and 'class' \
                        in grandgrandparent.attrs and 'sec' in grandgrandparent.attrs['class']:
                    flag = True
    return flag


def parse_subsection_name(ele, default_name):
    sec_name = parse_name_general(ele)
    if sec_name is None:
        return default_name
    else:
        return sec_name


def parse_name_general(ele):
    sec_name = None
    sub_element_list = ele.contents
    for sub_ele in sub_element_list:
        if sub_ele.name == 'div' or (sub_ele.name == 'div' and isinstance(sub_ele.attrs, dict)
                                     and 'class' in sub_ele.attrs and 'title' in sub_ele.attrs['class']):
            sec_name = sub_ele.text
            break
    return sec_name


def parse_subsubsection_name(ele, default_name):
    sec_name = parse_name_general(ele)
    if sec_name is None:
        return default_name
    else:
        return sec_name


def parse_subsubsubsection_name(ele, default_name):
    sec_name = parse_name_general(ele)
    if sec_name is None:
        return default_name
    else:
        return sec_name


def parse_section_name(ele):
    sec_name = parse_name_general(ele)
    if sec_name is None:
        return ele.attrs['id']
    else:
        return sec_name


def is_paragraph(ele):
    if ele.name == 'p' or (ele.name == 'div' and isinstance(ele.attrs, dict) and 'class' in ele.attrs
                           and 'p' in ele.attrs['class']):
        return True
    elif ele.name == 'div' and 'class' in ele.attrs and 'boxed-text' in ele.attrs['class']:
        return True
    else:
        return False


def parse_paragraph(ele):
    return ele.text


def is_table(ele):
    if ele.name == 'div' and isinstance(ele.attrs, dict) and 'class' in ele.attrs and 'table-wrap' in \
            ele.attrs['class']:
        return True
    else:
        return False


def parse_table(ele, unidentified_number_obj):
    try:
        table_label_ele = ele.find('div', attrs={'class': 'table-wrap-foot'})
        label = table_label_ele.find('label').text
        caption = table_label_ele.find('span').text
    except Exception:
        label = 'Unidentified Table with id {}'.format(unidentified_number_obj.get_next())
        caption = ''

    table_box = ele.find('table')
    table_text = remove_style(table_box).prettify()
    return label, caption, table_text


def parse_subsubsubsection(ele, target_folder, unidentified_number):
    item_list = ele.contents
    content_dict = {'text': [], 'figure': {}, "table": {}}

    for i, item in enumerate(item_list):
        if item.name == 'div' and isinstance(item.attrs, dict) and 'class' in item.attrs and 'title' in \
                item.attrs['class']:
            continue

        if is_paragraph(item):
            paragraph = parse_paragraph(item)
            content_dict['text'].append(paragraph)
        elif is_table(item):
            label, caption, table_text = parse_table(item, unidentified_number)
            content_dict['table'][label] = caption + "\n" + table_text
        elif is_figure(item):
            label, caption, figure = parse_figure(item, target_folder)
            content_dict['figure'][label] = caption
        else:
            logger.info('unknown')
            logger.info(item.text)
    return content_dict


def parse_subsubsection(item, target_folder, unidentified_number):
    item_list = item.contents
    content_dict = {none_str: {'text': [], 'figure': {}, "table": {}}}

    for i, item in enumerate(item_list):
        default_name = 'ele {}'.format(i)
        if item.name == 'div' and isinstance(item.attrs, dict) and 'class' in item.attrs and 'title' in \
                item.attrs['class']:
            continue

        if is_subsubsubsection(item):
            subsubsubsection_name = parse_subsubsubsection_name(item, default_name)
            content_dict[subsubsubsection_name] = parse_subsubsubsection(item, target_folder, unidentified_number)
        elif is_paragraph(item):
            paragraph = parse_paragraph(item)
            content_dict[none_str]['text'].append(paragraph)
        elif is_table(item):
            label, caption, table_text = parse_table(item, unidentified_number)
            content_dict[none_str]['table'][label] = caption + "\n" + table_text
        elif is_figure(item):
            label, caption, figure = parse_figure(item, target_folder)
            content_dict[none_str]['figure'][label] = caption
        else:
            logger.info('unknown')
            logger.info(item.text)
    return content_dict


def is_figure(item):
    if item.name == 'div' and isinstance(item.attrs, dict) and 'class' in item.attrs and 'fig' in \
            item.attrs['class']:
        return True
    else:
        return False


def parse_figure(item, target_folder):
    label = item.find('label', attrs={'class': 'label'}).text.strip()
    figure_cache_folder = os.path.join(target_folder, label)
    if not os.path.exists(figure_cache_folder):
        caption = item.find('div', attrs={'class': 'fig_note'}).text.replace(label, '').strip()
        target_item = item.find('img')
        figure_url = root_href + target_item.attrs['xlink:href']

        figure = request_get_with_sleep(figure_url).content

        os.makedirs(figure_cache_folder)
        with open(os.path.join(figure_cache_folder, 'figure.jpg'), 'wb') as f:
            f.write(figure)
        with open(os.path.join(figure_cache_folder, 'caption.txt'), 'w', encoding='utf-8-sig') as f:
            f.write(caption)
    else:
        with open(os.path.join(figure_cache_folder, 'figure.jpg'), 'rb') as f:
            figure = f.read()
        with open(os.path.join(figure_cache_folder, 'caption.txt'), 'r', encoding='utf-8-sig') as f:
            caption = f.read()
    return label, caption, figure


def parse_subsection(ele, target_folder, unidentified_number):
    item_list = ele.contents
    content_dict = {none_str: {none_str: {'text': [], 'figure': {}, "table": {}}}}

    for i, item in enumerate(item_list):
        default_name = 'ele {}'.format(i)
        if item.name == 'div' and isinstance(item.attrs, dict) and 'class' in item.attrs and 'title' in \
                item.attrs['class']:
            continue
        if is_subsubsection_ele(item):
            subsubsection_name = parse_subsubsection_name(item, default_name)
            content_dict[subsubsection_name] = parse_subsubsection(item, target_folder, unidentified_number)
        elif is_paragraph(item):
            paragraph = parse_paragraph(item)
            content_dict[none_str][none_str]['text'].append(paragraph)
        elif is_table(item):
            label, caption, table_text = parse_table(item, unidentified_number)
            content_dict[none_str][none_str]['table'][label] = caption + "\n" + table_text
        elif is_figure(item):
            label, caption, figure = parse_figure(item, target_folder)
            content_dict[none_str][none_str]['figure'][label] = caption
        else:
            logger.info('unknown')
            logger.info(item.text)
    return content_dict


def parse_section(ele, target_folder, unidentified_number):
    content_list = ele.contents

    content_dict = {none_str: {none_str: {none_str: {'text': [], 'figure': {}, "table": {}}}}}

    for i, item in enumerate(content_list):
        default_sub_sec_name = 'ele {}'.format(i)
        if item.name == 'div' and isinstance(item.attrs, dict) and 'class' in item.attrs and 'title' in \
                item.attrs['class']:
            continue
        if is_subsection_ele(item):
            sub_section_name = parse_subsection_name(item, default_sub_sec_name)
            content_dict[sub_section_name] = parse_subsection(item, target_folder, unidentified_number)
        elif is_paragraph(item):
            paragraph = parse_paragraph(item)
            content_dict[none_str][none_str][none_str]['text'].append(paragraph)
        elif is_table(item):
            label, caption, table_text = parse_table(item, unidentified_number)
            content_dict[none_str][none_str][none_str]['table'][label] = caption + "\n" + table_text
        elif is_figure(item):
            label, caption, figure = parse_figure(item, target_folder)
            content_dict[none_str][none_str][none_str]['figure'][label] = caption
        else:
            logger.info('unknown')
            logger.info(item.text)
    return content_dict
