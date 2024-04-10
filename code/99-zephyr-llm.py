import os
import json
import re
import glob

from tqdm import tqdm
import pandas as pd

import torch
from transformers import pipeline

pipe = pipeline("text-generation", model="HuggingFaceH4/zephyr-7b-beta", torch_dtype=torch.bfloat16, device_map="auto")

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
                     - Keep square brackets, e.g. around place names like `[Amsterdam]` \
                     - Only extract `booktitle` as field, not `title` \
                     - Try to extract the series number if a book appeared in a series: e.g. `152` for `(Middeleeuwse studies; 153)` or `XI` for `(Tekstedities; XI)` \
                    Important: Just return the bibtex entry and nothing else (no explanation, no note!)",
            'CHAP': "Parse the following, Dutch-language bibliographic description of a book chapter to a valid bibtex entry of the type @incollection. \
                   INSTRUCTIONS: \
                     - All fields should be unique \
                     - Keep square brackets in the output, e.g. around place names like `[Amsterdam]` \
                     - Extract the chapter's title as `title` and the containing book's title as `booktitle`. \
                     - Try to extract the series number if a book appeared in a series: e.g. `152` for `(Middeleeuwse studies; 153)` or `XI` for `(Tekstedities; XI)`. \
                    Important: Just return the bibtex entry and nothing else (no explanation, no note!).",
            'ADVS': "Parse the following, Dutch-language bibliographic description of a digital scholarly publication in the form of audiovisual material of the type @misc. \
                   INSTRUCTIONS: \
                     - All fields should be unique \
                     - Keep square brackets in the output, e.g. around place names like `[Amsterdam]` \
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

messages = [
    {
        "role": "system",
        "content": None,
    },
    {
        "role": "user",
        "content": None
    }
]

SELECT = 1000
CUTOFF = 500

for spreadsheet_path in glob.glob('*.xlsx'):
    if '_out' in spreadsheet_path:
        continue
    print('->', spreadsheet_path)

    ptype = os.path.basename(spreadsheet_path).replace('.xlsx', '')

    df = pd.read_excel(spreadsheet_path, header=0)
    df['RIS'] = df['RIS'].apply(json.loads)
    df['desc-str'] = [' '.join(t['title'].strip().split())[:CUTOFF].strip() for t in df['RIS']]
    
    if len(df) > SELECT:
        df = df.sample(SELECT)

    bibtexs = []

    for publ in tqdm(df['desc-str']):
        print(publ)
        if ptype == 'JOUR':
            publ = re.sub(r'In\: .+ Speciaal nummer van\: ', 'In: ', publ)
            publ = re.sub(r'In\: .+ Speciaal gedeelte van\: ', 'In: ', publ)
        
        messages[0]['content'] = prompts[ptype]
        messages[1]['content'] = publ

        prompt = pipe.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        outputs = pipe(prompt, max_new_tokens=256, do_sample=True, temperature=0.04, top_k=50, top_p=0.95)
        bibtex = outputs[0]["generated_text"].split('<|assistant|>')[-1]
        print(bibtex)
        bibtexs.append(bibtex)
        print('=====================')

    df['bibtex'] = bibtexs
    df['RIS'] = df['RIS'].apply(json.dumps)
    df.to_excel(spreadsheet_path.replace('.xlsx', '_out.xlsx'), index=True, header=True)