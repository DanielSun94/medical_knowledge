import os
from transformers import AutoTokenizer
import csv

def main():
    folder = os.path.abspath('./resource/textbooks')
    file_list = os.listdir(os.path.join(folder, 'source'))
    cache_folder = '/home/disk/sunzhoujian/hugginface'
    backbone = "THUDM/chatglm2-6b"
    tokenizer = AutoTokenizer.from_pretrained(backbone, trust_remote_code=True, cache_dir=cache_folder)

    for file in file_list:
        data = [['key', 'content']]
        file_path = os.path.join(folder, 'source', file)
        file_name = '.'.join(os.path.basename(file_path).split('.')[0: -1])
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            textbook = f.readlines()
            for paragraph in textbook:
                tokenized_paragraph = tokenizer(paragraph)
                if len(tokenized_paragraph['input_ids']) < 50:
                    continue
                data.append([paragraph[:2048], paragraph[:2048]])
        save_path = os.path.join(folder, 'target', file_name+'.csv')
        with open(save_path, 'w', encoding='utf-8-sig', newline='') as f:
            csv.writer(f).writerows(data)

        idx = 0
        with open(save_path, 'r', encoding='utf-8-sig', newline='') as f:
            csv_reader = csv.reader(f)
            for _ in csv_reader:
               idx += 1
            print(idx)
        print('{} processed'.format(file))


if __name__ == '__main__':
    main()
