import os
from dataclasses import dataclass
from datetime import datetime
import random
from time import sleep
from typing import List, Union, Generator
from pathlib import Path

from lacinizatar import lacin
import re
import string
import requests
from bs4 import BeautifulSoup


# TRANSLATOR_TEXT_LEN_LIMIT = 5000
TRANSLATOR_TEXT_LEN_LIMIT = 5000
LATINIZER_URL = 'https://baltoslav.eu/tar/index.php?mova=by'
LATINIZER_RESULT_ELEMENT_ID = 'izid'
ORIGINAL_FILE_NAME = 'tdesktop_be_v2510130.strings'
ORIGINAL_FILE_PATH = Path(os.path.dirname(os.path.abspath(__file__))) / ORIGINAL_FILE_NAME
TRANSLATED_FILE_NAME = f'tdesktop_be_latin_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S.%f")}_PART.strings'
# TRANSLATED_FILE_NAME = f'tdesktop_be_latin_PART.strings'
TRANSLATED_FILE_PATH = Path(os.path.dirname(os.path.abspath(__file__))) / TRANSLATED_FILE_NAME

@dataclass
class TranslationString:
    tag: str
    original: str
    translation: Union[str, None]

    def __init__(self, tag, original):
        self.tag = tag
        self.original = original
        self.translation = None

    @classmethod
    def construct_from_string(cls, s: str) -> 'TranslationString':
        match = re.search(r'^"(.*)"\s+=\s+"(.*)";$', s)
        try:
            tag = match.group(1)
            original = match.group(2)

            return cls(tag=tag, original=original)
        except AttributeError:
            print(f'String doesn\'t look like part of translation: "{s}"')

    def as_translated_string(self):
        return rf'"{self.tag}" = "{self.translation}";'


def latinize_string(original_string: str) -> str:
    # if original_string.startswith('Бел'):
    #     return r'Biełaruskaja#Praciahnuć pa-biełarusku#Kantakty#Vykliki#Nałady#Ab prahramie#Abnavić#Načny režym#Dadać ulikovy zapis#Užyć hety ŭlikovy zapis#Zadać emodzi-status#Źmianić emodzi-status#Maje historyi#Nie apaviaščać#Apaviaščać#Adkryć Telegram#Schavać u vobłaść apaviaščeńniaŭ#Vyjści z Telegram#Telegram usio jašče zapuščany.\nVy možacie vyklučyć jaho ŭ Naładach.\nKali hety značok źnikaje z vobłaści apaviaščeńniaŭ,\nvy možacie pieraciahnuć jaho siudy sa schavanych značkoŭ.#Studzień#Luty#Sakavik#Krasavik#Maj#Červień'
    # else:
    #     return r'Lipień#Žnivień#Vierasień#Kastryčnik#Listapad#Śniežań#studzienia#lutaha#sakavika#krasavika#maja#červienia#lipienia#žniŭnia#vieraśnia#kastryčnika#listapada#śniežnia#Stu#Lut#Sak#Kra#Maj#Čer#Lip#Žni#Vier#Kas#Lis#Śnie'

    if len(original_string) > TRANSLATOR_TEXT_LEN_LIMIT:
        raise ValueError('Latinizer accepts strings no longer than 5000 chars')

    request_data = {
        'mova': 'by',
        'lat': 'on',
        't': original_string,
    }

    sleep(random.choice(range(3, 10)))
    response = requests.post(url=LATINIZER_URL, data=request_data)
    if not response.ok:
        raise requests.RequestException(f'Unsuccessful request: {response}')

    soup = BeautifulSoup(response.content, 'html.parser')
    latinized = soup.find(id=LATINIZER_RESULT_ELEMENT_ID).text

    # TODO verify /n is actually //n, not /n in output string

    return latinized


def is_string_contains_translation_text(s: str) -> bool:
    return bool(re.match(r'^"(.*)"\s+=\s+"(.*)";$', s))


def read_original_file_as_lines(path: str) -> List[str]:
    original_lines = open(path, 'r', encoding="utf8").readlines()

    return original_lines


def build_string_objects(lines: List[str]) -> List[TranslationString]:
    string_objects = []
    for line in lines:
        if is_string_contains_translation_text(line):
            string_objects.append(TranslationString.construct_from_string(line))

    return string_objects


def get_text_batch(string_objects: List[TranslationString]) -> Generator[List[TranslationString], None, None]:
    batch = []
    batch_len = 0
    for obj in string_objects:
        if batch_len + len(obj.original) + 1 > TRANSLATOR_TEXT_LEN_LIMIT:
            yield batch
            batch = []
            batch_len = 0

        batch.append(obj)
        batch_len += len(obj.original) + 1

    yield batch


def convert_to_latin(string_objects: List[TranslationString]):
    # create file
    translated_file = open(TRANSLATED_FILE_PATH, 'w', encoding='utf8')
    # split into 5000 chars batches
    for objects_batch in get_text_batch(string_objects):
        batch_as_str = '#'.join(obj.original for obj in objects_batch)
        # translate batch
        batch_latinized_str = latinize_string(batch_as_str)
        # get_translation to objects
        for obj, translation in zip(objects_batch, batch_latinized_str.split('#')):
            obj.translation = translation
        # reconstruct file
        batch_translated_lines = [obj.as_translated_string() + '\n' for obj in objects_batch]
        translated_file.writelines(batch_translated_lines)

    translated_file.close()


lines = read_original_file_as_lines(ORIGINAL_FILE_PATH)
obj = build_string_objects(lines)
convert_to_latin(obj)
pass