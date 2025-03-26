''' 
    gscholar_get_increment.py needs two dates:
        old_date - this is when gscholar_pull_by_doi.py was run previous time
        new_date - this is when gscholar_pull_by_doi.py was run last time
    there should two data/google_organic_results_* files in data/ directory with the name for each date
    the script stores the increment in data/google_organic_results_'+new_date+'.incr.json file
    and rewrites data/google_organic_results_'+new_date+'.json to contain all old results plus the increment

    Adjust old_date and new_date values before running the script
    If the script was ran for DOI search then set DOI = True

    The output is stored in data/google_organic_results_'+new_date+'.incr.json
    or for GES DISC ShortName search in data/google_organic_results_short_name_ges_disc_'+new_date+'.incr.json

    The file with new results will be overwritten to contain old results and increment
'''

import json
import pandas as pd
import eosutilities as eosutil


old_date = 'sep2024'
new_date = 'jan2025'
DOI = True  # set to False if looking for increment for GES DISC ShortName dataset search

# program will look for google_organic_results_<date>.json files in data/ directory

if DOI:
    old_results_file = 'google_organic_results_'+old_date+'.json'
    new_results_file = 'google_organic_results_'+new_date+'.json'
    new_results_incr_file = 'google_organic_results_'+new_date+'.incr.json'
else:
    old_results_file = 'google_organic_results_short_name_ges_disc_'+old_date+'.json'
    new_results_file = 'google_organic_results_short_name_ges_disc_'+new_date+'.json'
    new_results_incr_file = 'google_organic_results_short_name_ges_disc_'+new_date+'.incr.json'

new_results = eosutil.loadJSON(new_results_file)
all_results = eosutil.loadJSON(old_results_file)

df = pd.DataFrame(all_results, columns=["result_id"])
old_result_ids = df['result_id'].tolist()

new_results_incr = list()

for result in new_results:
    if result['result_id'] in old_result_ids:
        continue
    new_results_incr.append(result)
    all_results.append(result)

# save increment
eosutil.saveJSON(new_results_incr, new_results_incr_file)

# overwrite new_results_file to contain old results and the increment
eosutil.saveJSON(all_results, new_results_file)

