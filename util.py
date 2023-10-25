import requests
import time
import os
import logging

oxford_type_1_href_root = "https://academic.oup.com"
cache_folder = os.path.abspath('./resource/guideline/cache')
resource_path = os.path.abspath('./resource/guidelines.yaml')
save_path = os.path.abspath('./resource/guideline/guideline_data.csv')
post_file_path = os.path.abspath('./resource/guideline/post_guideline_data.csv')
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
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter(format_)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)



def request_get_with_sleep(url, headers=None, sleep_time=5):
    response = requests.get(url, headers=headers)
    time.sleep(sleep_time)
    return response