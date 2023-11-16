import os
import bs4
from docx.exceptions import InvalidSpanError
from bs4 import NavigableString
from bs4.element import Tag
from util import logger
from util import sep
from util import oxford_type_1_href_root as href_root
from util import request_get_with_sleep, cache_folder, table_figure_ocr, remove_non_gbk_characters


def is_section(ele):
    return hasattr(ele, 'name') and ele.name == 'h2'


def is_subsection(ele):
    return hasattr(ele, 'name') and ele.name == 'h3'


def is_subsubsection(ele):
    return hasattr(ele, 'name') and ele.name == 'h4'


def is_subsubsubsection(ele):
    return hasattr(ele, 'name') and ele.name == 'h5'


def is_subsubsubsubsection(ele):
    return hasattr(ele, 'name') and ele.name == 'h6'


def is_paragraph(ele):
    return hasattr(ele, 'name') and ele.name == 'p' and hasattr(ele, 'attrs') and 'class' in ele.attrs \
        and 'chapter-para' in ele.attrs['class']


def is_list(ele):
    flag_unordered_list = hasattr(ele, 'name') and ele.name == 'ul'
    flag_ordered_list = hasattr(ele, 'name') and ele.name == 'ol'
    return flag_ordered_list or flag_unordered_list


def is_table(ele):
    flag_1 = hasattr(ele, 'name') and ele.name == 'div'
    if flag_1 is False:
        return False
    flag_2 = ele.find('div', attrs={'class': 'table-wrap-title'}) is not None
    flag_3 = ele.find('div', attrs='graphic-wrap') is not None and \
        ele.find('div', attrs='graphic-wrap').find('a') is not None
    if (flag_2 and flag_3) is False:
        return False
    flag_4 = 'Open in new tab' in ele.find('div', attrs='graphic-wrap').find('a').text
    return flag_4


def is_figure(ele):
    flag_1 = hasattr(ele, 'name') and ele.name == 'div'
    if flag_1 is False:
        return False
    flag_2 = ele.find('div', attrs={'class': 'label'}) is not None
    flag_3 = ele.find('div', attrs='graphic-wrap') is not None
    if not (flag_2 and flag_3):
        return False

    flag_4 = ele.find('div', attrs='graphic-wrap').find('a', attrs={'class': 'fig-view-orig'}) is not None and \
        'Open in new tab' in ele.find('div', attrs='graphic-wrap').find('a', attrs={'class': 'fig-view-orig'}).text
    return flag_4


def get_figure_content(ele, header, abbreviation):
    href = href_root + ele.find('a').attrs['href']

    fig_label = ele.find('div', attrs={'class': 'fig-label'}).text
    fig_label = remove_non_gbk_characters(fig_label)
    figure_cache_folder = os.path.join(cache_folder, abbreviation, fig_label)

    if os.path.exists(figure_cache_folder):
        with open(os.path.join(figure_cache_folder, 'suffix.txt'), 'r', encoding='utf-8-sig') as f:
            figure_suffix = remove_non_gbk_characters(f.read())
        with open(os.path.join(figure_cache_folder, 'figure.' + figure_suffix), 'rb') as f:
            figure = f.read()
        with open(os.path.join(figure_cache_folder, 'caption.txt'), 'r', encoding='utf-8-sig') as f:
            figure_caption = remove_non_gbk_characters(f.read())
        with open(os.path.join(figure_cache_folder, 'name.txt'), 'r', encoding='utf-8-sig') as f:
            figure_name = remove_non_gbk_characters(f.read())
    else:
        response = request_get_with_sleep(href, headers=header).text
        figure_content_html = bs4.BeautifulSoup(response, 'html.parser')

        figure_name = remove_non_gbk_characters(figure_content_html.find('div', attrs={'class': 'label'}).get_text())
        figure_href = figure_content_html.find('a', attrs={'class': 'fig-view-orig'}).get('href')
        figure_caption = remove_non_gbk_characters(figure_content_html.find('div', attrs={'class': 'caption'}).text)
        figure_data_type = remove_non_gbk_characters(
            figure_content_html.find('a', attrs={'class': 'fig-view-orig'}).get(
                'data-path-from-xml').strip().split('.')[-1])
        figure = request_get_with_sleep(figure_href).content

        os.makedirs(figure_cache_folder)
        with open(os.path.join(figure_cache_folder, 'suffix.txt'), 'w', encoding='utf-8-sig') as f:
            f.write(figure_data_type)
        with open(os.path.join(figure_cache_folder, 'figure.' + figure_data_type), 'wb') as f:
            f.write(figure)
        with open(os.path.join(figure_cache_folder, 'caption.txt'), 'w', encoding='utf-8-sig') as f:
            f.write(figure_caption)
        with open(os.path.join(figure_cache_folder, 'name.txt'), 'w', encoding='utf-8-sig') as f:
            f.write(figure_name)
    return figure_name, figure_caption, figure


# 效果不好，不用了
# def vertical_table_figure_concat(figure_dict):
#     figure_list = []
#     for idx in range(len(figure_dict)):
#         image = Image.open(io.BytesIO(figure_dict[idx+1]))
#         figure_list.append(image)
#     total_width = max(img.width for img in figure_list)
#     total_height = sum(img.height for img in figure_list)
#     new_fig = Image.new('RGB', (total_width, total_height))
#     y_offset = 0
#     for img in figure_list:
#         new_fig.paste(img, (0, y_offset))
#         y_offset += img.height
#     return new_fig


def get_table_content(ele, header, abbreviation, re_ocr):
    href = href_root + ele.find('div', attrs='graphic-wrap').find('a').attrs['href']
    table_title = ele.find('span', attrs={'class': 'title-label'})
    if table_title is None:
        table_title = ele.find('div', attrs={'class': "table-wrap-title"}).get('id')
    else:
        table_title = remove_non_gbk_characters(table_title.text)
    table_cache_folder = os.path.join(cache_folder, abbreviation, table_title)

    flag = os.path.exists(os.path.join(table_cache_folder, 'table_resource.txt'))

    # 访问大图，保存图片链接和表格部分信息
    if not flag:
        table_page = request_get_with_sleep(href, headers=header).text
        table_page_html = bs4.BeautifulSoup(table_page, 'html.parser')
        caption_ele = table_page_html.find('div', attrs={'class': 'caption'})
        if caption_ele is not None:
            caption_text = caption_ele.find('p', attrs={'class': 'chapter-para'}).text
        else:
            caption_text = ''
        # table_number = table_page_html.find('span', attrs={'class': 'title-label'})
        # if table_number is not None:
        #     table_number = table_number.text
        # else:
        #     table_number = ''
        candidate_ele = table_page_html.find('div', attrs={'class': 'table-modal'})
        candidate_ele = candidate_ele.find('div', attrs={'class': 'table-modal'})
        figure_flag = True if len(candidate_ele.findAll('img', attrs={'class': 'contentFigures'})) > 0 else False

        if figure_flag:
            figure_elements = candidate_ele.findAll('img', attrs={'class': 'contentFigures'})
            figure_urls = [ele.get('src') for ele in figure_elements]
            suffix_list = [ele.get('data-path-from-xml') for ele in figure_elements]
            suffix_list = [ele.strip().split('.')[-1] for ele in suffix_list]
            os.makedirs(table_cache_folder, exist_ok=True)
            with open(os.path.join(table_cache_folder, 'table_resource.txt'), 'w', encoding='utf-8-sig') as f:
                for url, suffix in zip(figure_urls, suffix_list):
                    f.write('{}${}\n'.format(url, suffix))
        else:
            with open(os.path.join(table_cache_folder, 'table_resource.txt'), 'w', encoding='utf-8-sig') as f:
                f.write('TEXT')
        with open(os.path.join(table_cache_folder, 'caption.txt'), 'w', encoding='utf-8-sig') as f:
            f.write(remove_non_gbk_characters(caption_text))
        # with open(os.path.join(table_cache_folder, 'table_number.txt'), 'w', encoding='utf-8-sig') as f:
        #     f.write(remove_non_gbk_characters(table_number))
    else:
        candidate_ele, table_page_html = None, None
        with open(os.path.join(table_cache_folder, 'caption.txt'), 'r', encoding='utf-8-sig') as f:
            caption_text = f.read()
        # with open(os.path.join(table_cache_folder, 'table_number.txt'), 'r', encoding='utf-8-sig') as f:
        #     table_number = f.read()

    with open(os.path.join(table_cache_folder, 'table_resource.txt'), 'r', encoding='utf-8-sig') as f:
        data = f.read()
        figure_flag_2 = False if 'TEXT' in data else True

    if figure_flag_2:
        resource_list = []
        content = {}
        with open(os.path.join(table_cache_folder, 'table_resource.txt'), 'r', encoding='utf-8-sig') as f:
            resource = f.readlines()
            for line in resource:
                resource_list.append(["$".join(line.split('$'))[:-1], line.split('$')[-1].replace('\n', '')])

        for j, (url, suffix) in enumerate(resource_list):
            figure_path = os.path.join(table_cache_folder, '{}.{}'.format(j + 1, suffix))
            if not os.path.exists(figure_path):
                table = request_get_with_sleep(url).content
                with open(figure_path, 'wb') as f:
                    f.write(table)
                logger.info('figure table download')
            else:
                with open(figure_path, 'rb') as f:
                    table = f.read()
            content[j + 1] = table, suffix

        assert len(content) > 0
        ocr_flag = os.path.exists(os.path.join(table_cache_folder, 'content.txt'))
        if not ocr_flag or re_ocr:
            table_content_text = ""
            for key in content:
                sub_figure_path = os.path.join(table_cache_folder, str(key) + '.{}'.format(content[key][1]))
                try:
                    table_content_text = table_content_text + " {} ".format(sep) + \
                                     table_figure_ocr(sub_figure_path, table_cache_folder, key)
                # 这里有时候会莫名出现错误
                except IndexError:
                    logger.error('{} OCR failed '.format(table_title))
                except InvalidSpanError:
                    logger.error('{} OCR failed '.format(table_title))
            with open(os.path.join(table_cache_folder, 'content.txt'), 'w', encoding='utf-8-sig') as f:
                f.write(remove_non_gbk_characters(table_content_text))
        else:
            with open(os.path.join(table_cache_folder, 'content.txt'), 'r', encoding='utf-8-sig') as f:
                table_content_text = f.read()
    else:
        if os.path.exists(os.path.join(table_cache_folder, 'content.txt')):
            with open(os.path.join(table_cache_folder, 'content.txt'), 'r', encoding='utf-8-sig') as f:
                table_content_text = f.read()
        else:
            assert candidate_ele is not None and table_page_html is not None
            content = candidate_ele.prettify()
            foot_node = table_page_html.find('div', attrs={'class': 'footnote'})
            if foot_node is None:
                foot = ''
            else:
                foot = foot_node.prettify()
            table_content_text = caption_text + ' ' + sep + ' ' + content + ' ' + sep + ' ' + foot
            os.makedirs(table_cache_folder)
            with open(os.path.join(table_cache_folder, 'content.txt'), 'w', encoding='utf-8-sig') as f:
                f.write(remove_non_gbk_characters(table_content_text))

    return remove_non_gbk_characters(caption_text), remove_non_gbk_characters(table_content_text)


def parse_oxford_type_1_dom(abbreviation, dom, header, re_ocr):
    doc_title = dom.find('h1')
    doc_title = doc_title.text
    content_div = dom.find('div', attrs={'data-widgetname': 'ArticleFulltext'})
    content_list = content_div.contents
    start_idx = 99999
    for i, item in enumerate(content_list):
        if hasattr(item, 'text') and hasattr(item, 'name') and item.name == 'h2':
            start_idx = i
            break
    if start_idx == 99999:
        raise ValueError('Start Point Not Found Error')

    none_str = 'none'
    content_dict = {'title': {none_str: {none_str: {none_str: {'text': [doc_title], 'figure': {}, "table": {}}}}}}
    sec_ptr, subsec_ptr, subsubsec_ptr, subsubsubsec_ptr = none_str, none_str, none_str, none_str
    for item in content_list[start_idx:]:
        if is_section(item):
            logger.info('Section: {}'.format(remove_non_gbk_characters(item.text)))
            if "reference" in item.text.lower():
                break
            sec_ptr = item.text
            subsec_ptr = none_str
            subsubsec_ptr = none_str
            subsubsubsec_ptr = none_str
            content_dict[sec_ptr] = {none_str: {none_str: {none_str: {'text': [], 'figure': {}, "table": {}}}}}

        elif is_subsection(item):
            logger.info('Subsection: {}'.format(remove_non_gbk_characters(item.text)))
            subsec_ptr = item.text
            subsubsec_ptr = none_str
            subsubsubsec_ptr = none_str
            if subsec_ptr not in content_dict[sec_ptr]:
                content_dict[sec_ptr][subsec_ptr] = {none_str: {none_str: {'text': [], 'figure': {}, "table": {}}}}
        elif is_subsubsection(item):
            logger.info('Subsubsection: {}'.format(remove_non_gbk_characters(item.text)))
            subsubsec_ptr = item.text
            subsubsubsec_ptr = none_str
            if subsubsec_ptr not in content_dict[sec_ptr][subsec_ptr]:
                content_dict[sec_ptr][subsec_ptr][subsubsec_ptr] = {none_str: {'text': [], 'figure': {}, "table": {}}}
        elif is_subsubsubsection(item):
            logger.info('Subsubsubsection: {}'.format(remove_non_gbk_characters(item.text)))
            subsubsubsec_ptr = item.text
            if subsubsubsec_ptr not in content_dict[sec_ptr][subsec_ptr][subsubsec_ptr]:
                content_dict[sec_ptr][subsec_ptr][subsubsec_ptr][subsubsubsec_ptr] = \
                    {'text': [], 'figure': {}, "table": {}}
        elif is_subsubsubsubsection(item):
            logger.info('Subsubsubsection: {}'.format(remove_non_gbk_characters(item.text)))
            content_dict[sec_ptr][subsec_ptr][subsubsec_ptr][subsubsubsec_ptr]['text']\
                .append("\n{}\n".format(item.text))
        elif is_list(item):
            content_dict[sec_ptr][subsec_ptr][subsubsec_ptr][subsubsubsec_ptr]['text'].append(item.text)
        elif is_paragraph(item):
            content_dict[sec_ptr][subsec_ptr][subsubsec_ptr][subsubsubsec_ptr]['text'].append(item.text)
        elif is_table(item):
            caption, table_content = get_table_content(item, header, abbreviation, re_ocr)
            content_dict[sec_ptr][subsec_ptr][subsubsec_ptr][subsubsubsec_ptr]['table'][caption] = table_content
            logger.info('Table Caption: {}'.format(caption))
        elif is_figure(item):
            fig_name, fig_caption, fig = get_figure_content(item, header, abbreviation)
            content_dict[sec_ptr][subsec_ptr][subsubsec_ptr][subsubsubsec_ptr]['figure'][fig_name] = fig_caption
            logger.info(fig_name)
        else:
            flag_2 = not (isinstance(item, Tag) and hasattr(item, 'name') and item.name == 'div' and 'class'
                          in item.attrs and 'video' in item.attrs['class'])
            flag_1 = not (isinstance(item, Tag) and hasattr(item, 'name') and item.name == 'div' and 'class'
                          in item.attrs and 'video-jump' in item.attrs['class'])
            flag_3 = isinstance(item, NavigableString) and \
                (str(item.encode('utf-8')) == '\n' or len(str(item.encode('utf-8'))) == 0)
            if not (flag_2 or flag_1 or flag_3):
                logger.info('UNKNOWN ITEM, Please Check')
                logger.info(item)
    return content_dict
