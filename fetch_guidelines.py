import csv
import os
import bs4
import yaml
import re
from parse_cjc_type_1 import parse_cjc_type_1_dom
from parse_oxford_type_1 import parse_oxford_type_1_dom
from parse_jacc_type_1 import parse_jacc_type_1_dom
from util import request_get_with_sleep, cache_folder, resource_path, save_path, post_file_path, request_jacc, request_cjc

max_length = 4096


def parse_dom(abbreviation, dom, header, doc_format_schema):
    if doc_format_schema == 'oxford_type_1':
        content_dict = parse_oxford_type_1_dom(abbreviation, dom, header)
        pass
    elif doc_format_schema == 'jacc_type_1':
        content_dict = parse_jacc_type_1_dom(abbreviation, dom)
    elif doc_format_schema == 'cjc_type_1':
        content_dict = parse_cjc_type_1_dom(abbreviation, dom)
    else:
        raise ValueError('')
    return content_dict


def get_dom(doc_format_schema, name, url, header, cacher=None, use_cache=True):
    cache_path = os.path.join(cacher, name + '.txt')
    if use_cache and os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8-sig') as f:
            in_cache = True
            html = f.read()
    else:
        if doc_format_schema == 'oxford_type_1':
            html = request_get_with_sleep(url, headers=header).text
        elif doc_format_schema == 'jacc_type_1':
            html = request_jacc(url).page_source
        elif doc_format_schema == 'cjc_type_1':
            html = request_cjc(url).page_source
        else:
            raise ValueError('')
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
                                subsubsubsec_content = doc_content[sec][subsec][subsubsec][subsubsubsec]
                                paragraph_list = subsubsubsec_content['text']
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
    elif schema == 'jacc_type_1':
        header = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                      "image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "Cache-Control": "no-cache",
            "Cookie": "MAID=akLWpo4MNzmFxRNfjyijLA==; _gid=GA1.2.1800897025.1697769581; hubspotutk=92b8479f5e12da307d"
                      "15c7eed6304d27; __hssrc=1; JSESSIONID=5f19dc22-ddec-4092-acd7-c37b14bf8fd8; MACHINE_LAST_SEEN="
                      "2023-10-19T22%3A08%3A20.616-07%3A00; __cf_bm=okB4mpXjEGTwYwLy4fTsgKtZlkAAtVjJCzPLpMqCIo0-16977"
                      "78500-0-AQUePIqe4E7OE2ksJEkx3TqyCeOlljRdVkH3Efi/CCtWjQWjU9ncyM3RH742DQpnfR11qKjCixxqYL0qu2DPa4"
                      "o=; _ga=GA1.1.1634842690.1697769578; cf_clearance=KCBY80A88N4tn6F.h28dh_dPlELFDdNHTLlF9nYvr2A"
                      "-1697778503-0-1-518c9034.3aebb72e.2d4a7a98-0.2.1697778503; _ga_PT683VWCRG=GS1.1.1697778495.3.1"
                      ".1697778517.38.0.0; __hstc=117268889.92b8479f5e12da307d15c7eed6304d27.1697769594527.1697772560"
                      "830.1697778532124.3; __hssc=117268889.1.1697778532124; _4c_=jVLJbtswEP2VgOdIJimRIn0L0i0F2lOCHg"
                      "1JHEuMZVGgGKtukH%2Fv0JbtLEBRHQjNmzfbm3kmUws9WTKpi6LQXFKu5TXZwH4ky2dSD%2FHdxefJd2RJ2hCGcblYTNOU"
                      "PpZ1nTrfLIyzC0ZTRplcPB5hTjlPqUqLXJFrUjsDGMx0qlKBdviDVq4o%2Fg7emac6rMJ%2BiJQJqqvRbNBhYGdrWE3WhD"
                      "bG5jm9oC3Ypg0Ia3lABx8ph9yT7Y2bXsVl%2FIKe4xSNcXd9AL%2BDPljX47zkJ2LfoPRh9aW03ZOHGbvblo3tm9n6fnN7"
                      "O%2F9%2B7qAO3g3tfrSuc81%2Bxh%2B2lYeuK2ez8m4aIfZ423q3hSvGoiwu1vx16GxE08MavD%2FQ0BptiOVPIs8ILgZB"
                      "13e2h%2BhKjq4BV0TinJ2ryy7G4VIxArvD0d5EIPz1ZvVw9ymKI7Nc5VxqXF48AKlFERu797ZpwP%2BA0DqDvHtfGhszlV"
                      "1UOyb0YGC0TaxioqBobYIbzvDLNfl9PCslc82Kw1mFgDeENo0fMrw1832RtaLA%2BZonFGiW5EWVJUpUIjHAdaVqTSWL24"
                      "05CypELoTKVK4xydDNOdi5ZKEyjW6ZzSXj8cwlh93M5pcGhdJCKp1%2FbPC4uIt4%2F4gWH6MNrGc6%2FS96fxLjlbjngZ"
                      "UQuCeFPHuile%2F8OhNFVHU6CTI7ZJYp9oZ6QJC6O%2BdSlAOreZFk9Xqd5FJAUmmtEiYLzXSFm9E1eSUwzeJOT5IxdRz"
                      "i5eUv",
            "Pragma": "no-cache",
            "Sec-Ch-Ua": "\"Chromium\";v=\"118\", \"Microsoft Edge\";v=\"118\", \"Not=A?Brand\";v=\"99\"",
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": "\"Windows\"",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.57"
    }
    elif schema == 'cjc_type_1':
        header = {
            'Content-Type':'application/json',
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
                          " Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.57"
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
                dom, in_cache = get_dom(doc_format_schema, abbreviation, doc_url, header, cache_folder, use_cache=True)
                content_dict = parse_dom(abbreviation, dom, header, doc_format_schema)
                data_dict[society][doc_type][abbreviation] = content_dict

    save_content(save_path, data_dict)
    content_postprocess(post_file_path, data_dict)


if __name__ == '__main__':
    main()
