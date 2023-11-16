import requests
import re
import os
import logging
from paddleocr import PPStructure, save_structure_res
from paddleocr.ppstructure.recovery.recovery_to_doc import sorted_layout_boxes, convert_info_docx
from unstructured.partition.docx import partition_docx
import cv2
from selenium import webdriver
from PIL import Image
import numpy as np
import time
from selenium.webdriver.chrome.service import Service

oxford_type_1_href_root = "https://academic.oup.com"
cache_folder = os.path.abspath('./resource/guideline/cache')
resource_path = os.path.abspath('./resource/guidelines.yaml')
save_path = os.path.abspath('./resource/guideline/guideline_data.csv')
post_file_path = os.path.abspath('./resource/guideline/post_guideline_data.csv')
chrome_driver_path = os.path.abspath('./resource/chromedriver-win64/chromedriver.exe')
sep = "<SEP>"


log_folder = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'resource', 'log')
if not os.path.exists(log_folder):
    os.makedirs(log_folder)
log_file_name = os.path.join(log_folder, '{}.txt'.format('fetch_guideline_log'))
format_ = "%(asctime)s %(process)d %(module)s %(lineno)d %(message)s"
logger = logging.getLogger()
logger.setLevel(logging.INFO)
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

file_handler = logging.FileHandler(log_file_name)
formatter = logging.Formatter(format_)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
console_handler.setLevel(logging.INFO)
file_handler.setLevel(logging.INFO)


def request_jacc(url, sleep=5):
    options = webdriver.ChromeOptions()
    options.add_argument('--log-level=3')  # 将 Chrome 浏览器的日志等级设置为 3，表示只输出错误信息，不输出运行信息
    options.add_experimental_option('useAutomationExtension', False)
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_argument('--ignore-certificate-errors')
    service = Service(executable_path=chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(url)
    time.sleep(sleep)
    return driver


def request_get_with_sleep(url, headers=None, sleep_time=10):
    response = requests.get(url, headers=headers)
    time.sleep(sleep_time)
    return response


def remove_style(ele):
    ele.attrs = {}
    for tag in ele.findAll(True):
        tag.attrs = {}
    return ele


def request_cjc(url, sleep=5):
    options = webdriver.ChromeOptions()
    options.add_argument('--log-level=3')  # 将 Chrome 浏览器的日志等级设置为 3，表示只输出错误信息，不输出运行信息
    options.add_experimental_option('useAutomationExtension', False)
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_argument('--ignore-certificate-errors')
    service = Service(executable_path=chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(url)
    time.sleep(sleep)
    return driver


def table_figure_ocr(figure_path, table_cache_folder, idx):
    table_engine = PPStructure(show_log=False)
    suffix = figure_path.strip().split(".")[-1]
    if suffix == 'gif':
        gif = Image.open(figure_path)
        frame = np.array(gif)
        img = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    else:
        img = cv2.imread(figure_path)
    result = table_engine(img)
    h, w, _ = img.shape
    docx_name = 'table_{}_ocr.docx'.format(idx)

    save_structure_res(result, table_cache_folder, 'table_{}'.format(idx))
    res = sorted_layout_boxes(result, w)
    convert_info_docx(img, res, table_cache_folder, "table_{}".format(idx))
    with open(os.path.join(table_cache_folder, docx_name), "rb") as f:
        elements = partition_docx(file=f)
    table_str = ''
    for element in elements:
        if element.category == 'Table':
            table_str += element.metadata.text_as_html + " " + sep
        else:
            table_str += element.text + " " + sep
    return table_str


def remove_non_gbk_characters(s):
    new_s = ''
    for char in s:
        try:
            char.encode('gbk')
            new_s += char
        except UnicodeEncodeError:
            new_s += ' '
    return new_s.strip()


def sanitize_windows_path(path: str, replacement: str = "_") -> str:
    """
    Sanitizes a Windows file path by replacing illegal characters with a specified replacement.

    Args:
    - path (str): The file path to sanitize.
    - replacement (str): The string to replace illegal characters with, default is "_".

    Returns:
    - str: The sanitized file path.
    """

    # Characters illegal in Windows file paths
    illegal_chars = r'<>:"/\\|\?*'

    # Replace any illegal character with the specified replacement
    sanitized_path = re.sub(f"[{re.escape(illegal_chars)}]+", replacement, path)

    # Replace any illegal trailing characters (periods or spaces)
    sanitized_path = re.sub(r"[ .]+$", replacement, sanitized_path)

    return sanitized_path

