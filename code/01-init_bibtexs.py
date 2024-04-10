import os
import shutil
import re
import glob
import json

import pandas as pd
import rispy

def clean_dir(dir_name):
    try:
        shutil.rmtree(dir_name)
    except FileNotFoundError:
        pass
    os.mkdir(dir_name)

dump_dir = '../data/llm-dump'
clean_dir(dump_dir)

ris_dir = '../data/ris-dump'
for decade_dir in sorted(os.listdir(ris_dir)):
    if decade_dir.startswith('.'):
        continue
    print('- ', decade_dir)
    clean_dir(f'{dump_dir}/{decade_dir}/')


    for ris_filepath in glob.glob(f'{ris_dir}/{decade_dir}/*.ris'):
        ty = os.path.basename(ris_filepath.replace('.ris', ''))
        with open(ris_filepath) as bibliography_file:
            entries = rispy.load(bibliography_file)

        cells = []
        for idx, entry in enumerate(entries):
            cells.append((f'{decade_dir}-{ty}-{idx + 1}', json.dumps(entry, indent=2), ''))
        
        df = pd.DataFrame(cells, columns=('index', 'RIS', 'bibtex')).set_index('index')
        df.to_excel(f'{dump_dir}/{decade_dir}/{ty}.xlsx', header=True, index=True)
