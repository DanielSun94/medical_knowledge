import csv
import os
import bs4
import yaml
import re
from parse_oxford_type_1 import parse_oxford_type_1_dom
from util import request_get_with_sleep, cache_folder, resource_path, save_path, post_file_path

max_length = 2048


def parse_dom(abbreviation, dom, header, doc_format_schema):
    if doc_format_schema == 'oxford_type_1':
        content_dict = parse_oxford_type_1_dom(abbreviation, dom, header)
    elif doc_format_schema == 'jacc_type_1':
        # TBD
        raise ValueError('')
    else:
        raise ValueError('')
    return content_dict


def get_dom(name, url, header, cacher=None, use_cache=True):
    cache_path = os.path.join(cacher, name + '.txt')
    if use_cache and os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8-sig') as f:
            in_cache = True
            html = f.read()
    else:
        html = request_get_with_sleep(url, headers=header).text
        with open(cache_path, 'w', encoding='utf-8-sig') as f:
            f.write(html)
            in_cache = False
    dom = bs4.BeautifulSoup(html, 'html.parser')
    return dom, in_cache


def discard_section_numer(string):
    result = re.search(string, "[1-9.]+")
    # 去除段号
    if result is not None and result.span()[0] == 0:
        new_string = string[result.span()[1]:]
    else:
        new_string = string
    return new_string


def content_postprocess(path, content_dict):
    head = ['key', 'content']
    data_to_write = [head]
    for society in content_dict:
        for doc_type in content_dict[society]:
            for abbreviation in content_dict[society][doc_type]:
                doc_content = content_dict[society][doc_type][abbreviation]
                title = doc_content['title']['none']['none']['none']['text'][0]
                for sec in doc_content:
                    sec_ = discard_section_numer(sec)
                    for subsec in doc_content[sec]:
                        subsec_ = discard_section_numer(subsec)
                        for subsubsec in doc_content[sec][subsec]:
                            subsubsec_ = discard_section_numer(subsubsec)
                            for subsubsubsec in doc_content[sec][subsec][subsubsec]:
                                subsubsubsec_ = discard_section_numer(subsubsubsec)

                                paragraph_list = doc_content[sec][subsec][subsubsec][subsubsubsec]['text']
                                for i, paragraph in enumerate(paragraph_list):
                                    key = '; '.join([title, sec_, subsec_, subsubsec_, subsubsubsec_,
                                                     'paragraph', str(i)]).strip()[: max_length]
                                    content = paragraph.replace('\n', '').strip()
                                    if len(content) > max_length:
                                        content = content[: max_length]
                                    data_to_write.append([key, content])

                                # 由于VQA功能不成熟，暂时不对图做处理
                                # figure_dict = doc_content[sec][subsec][subsubsec][subsubsubsec]['figure']
                                # for key in figure_dict:
                                #     key = '; '.format([title, sec_, subsec_, subsubsec_, subsubsubsec_, 'figure', key])
                                #
                                #     data_to_write.append([society, doc_type, abbreviation, sec, subsec, subsubsec,
                                #                           subsubsubsec, 'figure', key,
                                #                           figure_dict[key].replace('\n', '')])

                                table_dict = doc_content[sec][subsec][subsubsec][subsubsubsec]['table']
                                for table_name in table_dict:
                                    key = '; '.join([title, sec_, subsec_, subsubsec_, subsubsubsec_, 'table',
                                                     table_name])[: max_length]
                                    content = table_dict[table_name].replace('\n', '')[: max_length]
                                    data_to_write.append([key, content])
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        csv.writer(f).writerows(data_to_write)



def save_content(path, content_dict):
    head = ['society', 'doc_type', 'abbreviation_name', 'section', 'subsection', 'subsubsection', 'subsubsubsection',
            'data_type', 'key', 'content']
    data_to_write = [head]
    for society in content_dict:
        for doc_type in content_dict[society]:
            for abbreviation in content_dict[society][doc_type]:
                doc_content = content_dict[society][doc_type][abbreviation]
                for sec in doc_content:
                    for subsec in doc_content[sec]:
                        for subsubsec in doc_content[sec][subsec]:
                            for subsubsubsec in doc_content[sec][subsec][subsubsec]:
                                paragraph_list = doc_content[sec][subsec][subsubsec][subsubsubsec]['text']
                                for i, paragraph in enumerate(paragraph_list):
                                    data_to_write.append([society, doc_type, abbreviation, sec, subsec, subsubsec,
                                                          subsubsubsec, 'text', i, paragraph.replace('\n', '')])
                                figure_dict = doc_content[sec][subsec][subsubsec][subsubsubsec]['figure']
                                for key in figure_dict:
                                    data_to_write.append([society, doc_type, abbreviation, sec, subsec, subsubsec,
                                                          subsubsubsec, 'figure', key, figure_dict[key].replace('\n', '')])
                                table_dict = doc_content[sec][subsec][subsubsec][subsubsubsec]['table']
                                for key in table_dict:
                                    data_to_write.append([society, doc_type, abbreviation, sec, subsec, subsubsec,
                                                          subsubsubsec, 'table', key, table_dict[key].replace('\n', '')])
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        csv.writer(f).writerows(data_to_write)


def get_header(schema):
    if schema == 'oxford_type_1':
        header = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,"
                  "image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
           "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Cookie": "OUP_SessionId=yu3rlcjt5tdetp4gsjnmneoi; Oxford_AcademicMachineID=638333607940692687; "
                      "fpestid=ZbRj__jSOK6VQjgz4MdvwIWLfOos-gb-xCW53o-L9Z0LGqkWtDvFu1whsFOtWPzYiYuzAA",
            "Host": "academic.oup.com",
            "Pragma": "no-cache",
            "Sec-Ch-Ua": "\"Chromium\";v=\"118\", \"Microsoft Edge\";v=\"118\", \"Not=A?Brand\";v=\"99\"",
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": "\"Windows\"",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.57"
        }
    else:
        raise ValueError('')
    return header


def main():
    os.makedirs(cache_folder, exist_ok=True)
    with open(resource_path, 'r', encoding='utf-8-sig') as f:
        resource = yaml.load(f, yaml.FullLoader)
        documents, journal_mapping = resource['documents'], resource['journal_mapping']
        journal_mapping_dict = dict()
        for target in journal_mapping:
            for source in journal_mapping[target]:
                journal_mapping_dict[source] = target

    data_dict = dict()
    for society in documents:
        data_dict[society] = dict()
        for doc_type in documents[society]:
            data_dict[society][doc_type] = dict()
            for doc_name in documents[society][doc_type]:
                doc_url = documents[society][doc_type][doc_name]['url']
                journal = documents[society][doc_type][doc_name]['journal']
                abbreviation = documents[society][doc_type][doc_name]['abbreviation']
                doc_format_schema = journal_mapping_dict[journal]
                header = get_header(doc_format_schema)

                dom, in_cache = get_dom(abbreviation, doc_url, header, cache_folder, use_cache=True)
                content_dict = parse_dom(abbreviation, dom, header, doc_format_schema)

                data_dict[society][doc_type][abbreviation] = content_dict

    save_content(save_path, data_dict)
    content_postprocess(post_file_path, data_dict)


if __name__ == '__main__':
    main()
