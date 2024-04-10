import os
import json
import re
import glob
import time

from tqdm import tqdm
import pandas as pd

import openai
openai.api_key = ''


prompts = {
           'JOUR': "Parse the following, Dutch-language bibliographic description of a journal article to a valid bibtex entry of the type @article. \
                   INSTRUCTIONS:\
                     - Make sure that the name of the journal is included! \
                     - All fields should be unique. \
                    Important: Just return the bibtex entry and nothing else (no explanation, no note!).",
            'EJOUR': "Parse the following, Dutch-language bibliographic description of a online journal article to a valid bibtex entry of the type @article. \
                   INSTRUCTIONS:\
                     - Make sure that the name of the journal is included! \
                     - All fields should be unique. \
                    Important: Just return the bibtex entry and nothing else (no explanation, no note!).",
           'BOOK' : "Parse the following, Dutch-language bibliographic description of a book to a valid bibtex entry of the type @book. \
                  INSTRUCTIONS:\
                     - All fields should be unique \
                     - Only extract `booktitle` as field, not `title` \
                     - Try to extract the series number if a book appeared in a series: e.g. `152` for `(Middeleeuwse studies; 153)`, `12` for `(Tekstedities, 12)` or `XI` for `(Tekstedities; XI)` \
                    Important: Just return the bibtex entry and nothing else (no explanation, no note!)",
            'CHAP': "Parse the following, Dutch-language bibliographic description of a book chapter to a valid bibtex entry of the type @incollection. \
                   INSTRUCTIONS: \
                     - All fields should be unique \
                     - Extract the chapter's title as `title` and the containing book's title as `booktitle`. \
                     - Try to extract the series number if a book appeared in a series: e.g. `152` for `(Middeleeuwse studies; 153)` or `XI` for `(Tekstedities; XI)`. \
                    Important: Just return the bibtex entry and nothing else (no explanation, no note!).",
            'ADVS': "Parse the following, Dutch-language bibliographic description of a digital scholarly publication in the form of audiovisual material of the type @misc. \
                   INSTRUCTIONS: \
                     - All fields should be unique \
                    Important: Just return the bibtex entry and nothing else (no explanation, no note!).",
            'JFULL': "Parse the following, Dutch-language bibliographic description of a publication. \
                   INSTRUCTIONS: \
                     - Use the type @book \
                    Important: Just return the bibtex entry and nothing else (no explanation, no note!).",
            'WEB': "Parse the following, Dutch-language bibliographic description of an electronic publication online. \
                   INSTRUCTIONS: \
                     - Use the type @misc \
                     - All fields should be unique \
                    Important: Just return the bibtex entry and nothing else (no explanation, no note!).",
         }

#SELECT = 15
CUTOFF = 500

llm_path = '../data/llm-dump'
spreadsheet_path = ''
df = None

try:
    for decade_folder in sorted(glob.glob(f'{llm_path}/*')):
        print(':::', decade_folder, ':::')

        for spreadsheet_path in sorted(glob.glob(f'{decade_folder}/*.xlsx')):
            ptype = os.path.basename(spreadsheet_path).replace('.xlsx', '')
            print('     - ', spreadsheet_path)

            df = pd.read_excel(spreadsheet_path, header=0)

            if 'bibtex' not in df.columns:
                df['bibtex'] = ''

            df['bibtex'] = df['bibtex'].fillna('')
            
            df['RIS'] = df['RIS'].apply(json.loads)
            desc_str = [' '.join(t['title'].strip().split())[:CUTOFF].strip() for t in df['RIS']]
            df['RIS'] = [json.dumps(d, indent=2, ensure_ascii=False) for d in df['RIS']]

            #desc_str = desc_str[:SELECT]

            for idx, (publ, bibt) in tqdm(list(enumerate(zip(desc_str, df['bibtex'])))):
                try:
                    if not bibt:
                        if ptype == 'JOUR':
                            publ = re.sub(r'In\: .+ Speciaal nummer van\: ', 'In: ', publ)
                            publ = re.sub(r'In\: .+ Speciaal gedeelte van\: ', 'In: ', publ)

                        print('\n         >', publ)
                        messages = [{'role': 'user',
                                    'content': prompts[ptype] + ' -> ' + publ}]
                        responses = openai.ChatCompletion.create(model='gpt-3.5-turbo', messages=messages)
                        bibtex = responses['choices'][0]['message']['content']
                        print(bibtex)

                        df.loc[idx, 'bibtex'] = bibtex
                        time.sleep(.5)
                        print('=====================')
                except Exception as e:
                    print(e, ': caught exception')
        
            df.to_excel(spreadsheet_path, index=False, header=True)

except KeyboardInterrupt:
    pass

df.to_excel(spreadsheet_path, index=False, header=True)