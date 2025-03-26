# -*- coding: utf-8 -*-
"""
    gscholar_pull_by_doi.py queries Google Scholar via SerpAPI interface for the documents returned for searches by dataset DOIs.
    The search results are stored in google_organic_results_file = 'data/google_organic_results_'+date+'.json'
    Adjust date in the beginning of the script (usually year and month when the code was executed)

    Store your SerpAPI key in data/serp_api_key.json as:
    {
        'serp_api_key' : "your Serp API key"
    }

   Obtain latest dataset DOIs from EOSDIS DOI server https://doiserver.eosdis.nasa.gov/ords/f?p=100:8:::NO:::  and place the csv files into eosdis_csv_files/ directory.
   For all 10.5067 : Provider -> Data, Status=Registered, Query
   For ORNL and SEDAC Home->Monthly Report->'ORNL DAAC' or 'SEDAC'. ORNL and SEDAC csv files can be combined. The csv with 10.5067 DOI has more extended format.
   Keep two latest .csv files in eosdis_csv_files/ directory.

   Using the content of these csv files create a single column csv file that contains the DOIs for SerpAPI search:
    awk -F'"' '{print $4}' eosdis_CSV_FILES/all_eosdis_dois_20240223.csv > eosdis_CSV_FILES/all_eosdis_dois_20240223_1col.csv
    awk -F'"' '{print $4}' eosdis_CSV_FILES/ornl_sedac_dois_20240223.csv >> eosdis_CSV_FILES/all_eosdis_dois_20240223_1col.csv
    name the column 'DOI'
    pass the name of this single column csv file to the script:
   gscholar_pull_by_doi.py eosdis_CSV_FILES/all_eosdis_dois_20240223_1col.csv

   In the script:
   *    Set an earliest document publication year for SerpAPI search: as_ylo
   *    Adjust the date for naming output files. I usually use month and year when the search was performed: jan2025
"""

from serpapi import GoogleSearch
import os
import sys
import json
from urllib.parse import urlsplit, parse_qsl
import re
import time
import datetime
import pandas as pd
import eosutilities as eosutil

#Set an earliest document publication year for SerpAPI search
as_ylo = '2024'

# Adjust the date for naming output files. I usually use current month and year
date = 'jan2025'

key = eosutil.loadJSON('serp_api_key.json')['serp_api_key']
print(key)

if len(sys.argv) < 2 or not os.path.exists(sys.argv[1]):
  print("Please, supply name of .csv file with DOIs to search with DOIs arranged into a single column called 'DOI'")
  exit()
csv_file = sys.argv[1]
print(csv_file)

google_organic_results_file = 'data/google_organic_results_'+date+'.json'
searched_dois_file = 'data/searched_dois_'+date+'.json'

def getDataFrameFromCSV(csv_file):
  column_names = ['DOI']
  df = pd.read_csv(csv_file) # note to self: change to variable filename
  df = df[column_names]
  return df['DOI'].tolist()

def get_articles(doi, article_results, counter):
  params = {
    "api_key": key,
    "engine": "google_scholar",
    "q": doi,
    "hl": "en",        # search language
    "lr": "lang_en",   # return results only in English language
    "as_vis": "1",     # do not include citations
    "as_ylo": as_ylo   # return results with publication year as_ylo and later
    #"as_yhi": "2023",  # to 2023
    #"start": "0"       # first page
  }

  search = GoogleSearch(params)
  page = 1
  loop_is_true = True
  while loop_is_true:
    
    search_results = search.get_dict()
    try:
        print(search_results['search_metadata']['status'])
    except:
        print(search_results['error'])
        exit()
    if 'organic_results' in search_results:
        if len(search_results['organic_results']) >= 1:
            results = search_results['organic_results']
            for result in results:
                result['doi'] = doi
                article_results.append(result)
        else: 
          return (article_results, counter)
    else: 
      return (article_results, counter)
        
    if 'serpapi_pagination' in search_results:
        if (not 'next' in search_results['serpapi_pagination']):
            loop_is_true = False
        else:
            search.params_dict.update(dict(parse_qsl(urlsplit(search_results["serpapi_pagination"]["next"]).query)))        
            print('Now on page ', page, 'of results for doi: ', doi, ' | time: ', datetime.datetime.now())
            page += 1
    else:
        loop_is_true = False
  counter += page
  return (article_results, counter)

dois2search = getDataFrameFromCSV(csv_file)


# As the search may get interrupted, thus results for each DOI search are dumped into the 
# file and the DOIs that have been searched are also recorded

article_results = []
if os.path.exists(google_organic_results_file):
    with open(google_organic_results_file) as gs_file:
        article_results = json.load(gs_file)
searched_dois = []
if os.path.exists(searched_dois_file):
    with open(searched_dois_file) as doi_file:
        searched_dois = json.load(doi_file)
    print ("Already searched "+str(len(searched_dois))+" DOIs")

counter = 0
doi_count = 0
for doi in dois2search:
  if doi in searched_dois:
    print (doi + " was already searched")
    continue
  print (doi + " is not in searched_dois")
  doi_count += 1
  searched_dois.append(doi)
  (article_results, counter) = get_articles(doi, article_results, counter)
  with open(google_organic_results_file, 'w') as output:
    json.dump(article_results, output, indent=4)
  with open(searched_dois_file, 'w') as output:
    json.dump(searched_dois, output, indent=4) 
  if doi_count%50 == 0:
    time.sleep(60)  #sleep 1 min

with open(google_organic_results_file, 'w') as output:
        json.dump(article_results, output, indent=4) 

with open(searched_dois_file, 'w') as output:
        json.dump(searched_dois, output, indent=4) 

print('\n\n### COUNTER: ', counter, ' ###')

