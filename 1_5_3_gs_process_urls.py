'''
    The purpose of 1_5_1_serpapi.py is to process results of SerpAPI output to create a list where:
    * The results with the same result_id are combined
    * All dataset DOIs (or ShortNames) for result_id are combined
    * When possible a document DOI for given document URL is derived 
    * Retain document publication year, title, and author name for future Crossref search
    * PDFs and preprints are eliminated

    before running the script:
        * make sure that there is 'data/google_organic_results_'+date+'.incr.json or data/google_organic_citations_short_name_ges_disc_'+date+'.incr.json
        * adjust values of DOI (True for DOI search, False for ShortName search) and date (I use month+year), 
    the date is needed to figure out filename of input files and name output file.

    The output is stored in data/google_organic_citations_'+date+'.incr.json or data/google_organic_citations_short_name_ges_disc_'+date+'.incr.json
'''

# DOIs can be derived for copernicus, nature, ametsoc URLs
# DOIs can not be derived for ieeexplore, sciencedirect, mdpi
# web sites that publish preprints: www.researchsquare.com, essopenarchive.org, authorea.com, and techrxiv.org

import os
import sys
import json
import re
import time
import datetime
import pandas as pd
import unicodedata # used to transform unicode to ascii such as '\u2026' to '...'
from bs4 import BeautifulSoup # used together with unescape to remove html tags such as &lt;
from html import unescape # used together with unescape to remove html tags such as &lt;

EXCLUDE_PREPRINTS = True	# do not process GScholar results if their "link" contains "preprint" string
EXCLUDE_PDF = True	        # do not process GScholar results if they are "type": "Pdf" or their link contains ".pdf" string

# when search by DOI change to True; False if GS was searched by ShortName
DOI = False #True
date='feb2025'

if DOI:
    google_organic_results = 'data/google_organic_results_'+date+'.incr.json'
    google_organic_citations = 'data/google_organic_citations_'+date+'.incr.json'
else:
    google_organic_results = 'data/google_organic_results_short_name_ges_disc_'+date+'.incr.json'
    google_organic_citations = 'data/google_organic_citations_short_name_ges_disc_'+date+'.incr.json'

with open(google_organic_results) as gs_file:
  article_results = json.load(gs_file)

def find_citation_by_id (result_id, organic_citations):
  for citation in organic_citations:
    if citation['result_id'] == result_id:
      return citation
  return None

organic_citations = []
index = 0
for result in article_results:
  # check if this result_id is already in organic_citations
  citation = find_citation_by_id(result['result_id'], organic_citations)
  if citation:
    if DOI:
      citation['dois'].append(result['doi'])
    else:
      citation['ShortNames'].append(result['ShortName'])
    continue

  title = result['title']
  (author, year, pub_doi, link) = ('', '', '', '')
  pub_info = result['publication_info']['summary']
  #print(pub_info)
  pub_info = BeautifulSoup(unescape(pub_info), 'lxml').text
  pub_info =  unicodedata.normalize('NFKD', pub_info).encode('ascii', 'ignore').decode('ascii')
  #print(pub_info)

  try:
    author = result['authors'][0]['name']
  except:
    try: 
      author = re.match(r'^((?:\S+\s+){1}[^\r\n\t\f\v ,]+).*',pub_info).group(1)
    except:
      author = ''

  try:
    year = ''.join(re.findall(r'\s+(\d{4})\s+',pub_info)[0])  # articles from 1980 and later
    year='('+year+')'
  except:
    year = ''

  if result.get('type'):
    resp = re.search(r'Pdf', result['type'])
    if resp and EXCLUDE_PDF:
      continue
  
  if result.get('link'):
    if re.search(r'\.pdf', result['link']) and EXCLUDE_PDF:
      continue
    if re.search(r'daac\.ornl\.gov', result['link']):   # exclude ORNL document
      continue 
    if re.search(r'preprint', result['link']) and EXCLUDE_PREPRINTS:
      continue
    if re.search(r'www\.researchsquare\.com', result['link']) and EXCLUDE_PREPRINTS:  # www.researchsquare.com is Website for preprint publications
      continue
    if re.search(r'essopenarchive\.org', result['link']) and EXCLUDE_PREPRINTS:  # essopenarchive.org is Website for preprint publications
      continue
    if re.search(r'biorxiv\.org', result['link']) and EXCLUDE_PREPRINTS:  # biorxiv.org is Website for preprint publications
      continue
    if re.search(r'medrxiv\.org', result['link']) and EXCLUDE_PREPRINTS:  # medrxiv.org is Website for preprint publications
      continue
    if (re.search(r'authorea\.com', result['link']) or re.search(r'techrxiv\.org', result['link'])) and EXCLUDE_PREPRINTS:  # authorea.com and techrxiv.org are Website for preprint publications
      continue
    link = result['link']
    resp = re.search(r'\/(10\.\d+.*)$', result['link'])
    if resp:
      pub_doi = resp[0]
      pub_doi = re.sub(r'(\/full|\/meta|\.pdf|\.abstract|\.short|\&.*|\/download|\/html|\?.*|\#.*|\;|\)|\/$|\.$)','',pub_doi)
    elif re.search(r'copernicus\.org', result['link']):
      resp = re.search(r'\//(\S+)\.copernicus\.org\/articles\/(\d+)\/(\d+)\/(\d+)', result['link'])
      if resp:
        pub_doi = '10.5194/'+resp[1]+'-'+resp[2]+'-'+resp[3]+'-'+resp[4]
    elif re.search(r'nature\.com\/articles\/', result['link']):
      resp = re.search(r'nature\.com\/articles\/(\S+)', result['link'])
      if resp:
        pub_doi = '10.1038/'+resp[1]                            # looks like some Nature articles have doi prefix 10.1057
        pub_doi = re.sub(r'(\?.*|\/briefing.*)', '', pub_doi)
        pub_doi = re.sub(r'%E2%80%', '-', pub_doi)
        resp = re.match(r'10.1038\/sdata(\d{4})(\d+)', pub_doi)
        if resp:
          pub_doi = '10.1038/sdata.'+resp[1]+'.'+resp[2]
        # https://www.nature.com/articles/s41558%E2%80%92019%E2%80%920592%E2%80%928 should translate to 10.1038/s41558-019-0592-8
    elif re.search(r'journals\.ametsoc\.org', result['link']):
      resp=re.search(r'\/((\w+|\.+|\-+|_+)*)\.xml', result['link'])
      if resp:
        pub_doi = '10.1175/'+resp[1]
        pub_doi = re.sub(r'_1', '.1', pub_doi)
        if not re.search(r'-', pub_doi):
          resp=re.match(r'10.1175\/(\w+)(d|D)(\d{2})(\d{4})', pub_doi)
          if resp:
            pub_doi = '10.1175/'+resp[1]+'-'+resp[2]+'-'+resp[3]+'-'+resp[4]+'.1'
    if pub_doi:
      pub_doi=re.sub(r'^\/', '', pub_doi)
      pub_doi=re.sub(r'(\/|\;|\)|\.|\.full)$', '', pub_doi)
      if re.search(r'elementa', pub_doi) or re.search(r'iwaponline\.com', link) or re.search(r'academic\.oup\.com', link):
        # https://iwaponline.com/jwcc/article/doi/10.2166/wcc.2024.010/102891
        # https://academic.oup.com/biolinnean/advance-article-abstract/doi/10.1093/biolinnean/blae053/7695211
        pub_doi = re.sub(r'\/\d+$', '', pub_doi)
      elif re.search(r'taylorfrancis\.com\/books', link):
        # https://www.taylorfrancis.com/books/mono/10.1201/9781003220510/understanding-gis-sustainable-development-goals-paul-holloway
        resp=re.match(r'(10\.\d+\/\d+)\/', pub_doi)
        if resp:
          pub_doi = resp[1]
      elif re.search(r'taylorfrancis\.com\/chapters', link):
        # https://www.taylorfrancis.com/chapters/edit/10.1201/9781003541141-10/overview-satellite-image-radiometry-solar-reflective-optical-domain-philippe-teillet
        resp=re.match(r'(10\.\d+\/\d+-\d+)\/', pub_doi)
        if resp:
          pub_doi = resp[1]
    # https://www.authorea.com/doi/full/10.22541/au.163759718.81714860 should translate to 10.22541/au.163759718.81714860/v1
  citation = {
      'result_id'	: result['result_id'],
      'link'		: link,
      'pub_doi'		: pub_doi,
      #'index'		: str(index)+'.',
      'author'	 	: author,
      'year'		: year,
      'title'		: title
     }
  if DOI:
    citation['dois'] = [result['doi']]
  else:
    citation['ShortNames'] = [result['ShortName']]
  organic_citations.append(citation)
  index += 1

with open(google_organic_citations, 'w') as output:
  json.dump(organic_citations, output, indent=4)

