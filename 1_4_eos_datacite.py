'''
getDataCite(eos_dois):                                          pulls from datacite api the EOS DOIS
dataciteTranspose(datacite_found):                              converts datacite_found with EOS DOI as the main key, and transforms the main key to the publication DOI
daciteExtractCrossref(datacite):                                gets title and year from crossref
daciteExtractHabanero(crossref_valid):                          for dois not found in crossref, this function gets title and year from habanero
mergeCrossrefHabanero(datacite_crossref,datacite_habanero):     merges crossref and habanero lists
matchDataCiteEOS(datacite, eos_dois):                           matches datacite found dois to gesdisc eos csv DOIs
'''

import re
import requests
import json
import re
from crossref.restful import Works, Etiquette
from habanero import cn
import unicodedata # used to transform unicode to ascii such as '\u2026' to '...'
from bs4 import BeautifulSoup # used together with unescape to remove html tags such as &lt;
from html import unescape # used together with unescape to remove html tags such as &lt;

import eosutilities as eosutil
#set my_etiquette for crossref API. It helps filter unusual requests, and contact if necessary.
#my_etiquette = eosutil.my_etiquette
#works = Works(etiquette=my_etiquette)
my_etiquette = eosutil.loadJSON('crossref_etiquette.json')
works = Works(etiquette=Etiquette(my_etiquette['project_name'], my_etiquette['version'], my_etiquette['organization'], my_etiquette['email']))

import time
from datetime import datetime
now = datetime.now()

new_date = 'jan2025'
old_date = 'sep2024'

def getDataCite(eos_dois):
    '''
    pulls from datacite api the EOS DOIS
    returns datacite_found and error_code
    '''
    print('init\t\tgetDataCite(eos_dois)', flush=True)
    data = 0
    error_code = list()
    datacite_found = list()
    for i,e in enumerate(eos_dois):
        print(i," ",e)
        if i % 100 == 0:
            print(i,'/',len(eos_dois),'\t',now.strftime("%H:%M:%S"), flush=True)
        #print(i)
        #e['cited-by'] = list()
        tag = e['EOS DOI']
        url = 'https://api.datacite.org/dois/'+str(tag)
        try:
            metadata = requests.get(url)
            status_codes = [404, 400, 503, 408]
            if metadata.status_code in status_codes:
                error_code.append(tag)
                metadata.raise_for_status()
        except requests.exceptions.HTTPError as error:
            print(error)
            #raise
            continue
        json_data = json.loads(metadata.text)


        entries = json_data['data']['relationships']['citations']['data']
        data += len(entries)
        if len(entries) > 0:
            datacite_found.append([tag,entries])
            eosutil.saveJSON(datacite_found,'debug_datacite_found.json')
        #print(i,entries, flush=True)
        for j,entry in enumerate(entries):
            #print(entry)
            doi = entry['id']
            #e['cited-by'].append(doi)
            #print(i,j,doi, flush=True)
    print('complete\tgetDataCite(eos_dois)', flush=True)
    return datacite_found

def dataciteTranspose(datacite_found):
    '''
    converts datacite_found with EOS DOI as the main key, and transforms the main key to the publication DOI
    '''
    print('init\t\tdataciteTranspose(datacite_found)', flush=True)
    datacite_set = set()
    c = 0
    for i,d in enumerate(datacite_found): # create unique set of dois
        dois = d[1]
        for j,doi in enumerate(dois):
            #print(i,j,doi)
            datacite_set.add(doi['id'].upper())
    datacite = list()
    for i,d in enumerate(list(datacite_set)): # create list of dois
        datacite.append({'DOI': d})
    for i,d in enumerate(datacite): # match datacite_found 10.5067 tags to the publication DOIs
        d['tags'] = list()
        for j,f in enumerate(datacite_found):
            dois = f[1]
            for k,doi in enumerate(dois):
                if d['DOI'].upper() == doi['id'].upper():
                    d['tags'].append(f[0])
    print('complete\tdataciteTranspose(datacite_found)', flush=True)
    return datacite

def dataciteExtractCrossref(datacite):
    '''
    gets title and year from crossref
    returns datacite and datacite_no_crossref
    '''
    print('init\t\tdaciteExtractCrossref(datacite)', flush=True)
    datacite_no_crossref = list()
    datacite_crossref = list()
    for i,d in enumerate(datacite):
        if i % 100 == 0:
            print(i,'/',len(datacite))
        print(d['DOI'])
        try:
            item = works.doi(d['DOI'])
            try:
                d['Type'] = works.doi(d['DOI'])['type']
                print(d['Type'])
            except:
                print("No Type")
            year = None
            try:
                year = item['created'].get('date-parts')[0][0]
            except:
                try:
                    year = item['published-print'].get('date-parts')[0][0]
                except:
                    print("No year")
            title = item.get('title')
            title = title[0]
            title = BeautifulSoup(unescape(title), 'lxml').text #sanitize title from html tags
            title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode('ascii') # sanitize title from unicode
            d['Year'] = str(year)
            d['Title'] = title
            datacite_crossref.append(d)
        except:
            datacite_no_crossref.append(d['DOI'])
    print('complete\t\tdaciteExtractCrossref(datacite)', flush=True)
    return datacite_crossref

def daciteExtractHabanero(crossref_valid):
    '''
    for dois not found in crossref, this function gets title and year from habanero
    returns crossref, no_crossref
    '''
    print('init\tdaciteExtractCrossref(datacite_no_crossref)', flush=True)
    crossref_dois = set()
    for c in crossref_valid:
        crossref_dois.add(c)
    crossref_dois = list(crossref_dois)
    crossref = list()
    no_crossref = list()
    print('init extractHabanero:',len(crossref_dois),' Unique DOIs')
    for i, doi in enumerate(crossref_dois):
        if i % 100 == 0:
            print(i,'/',len(crossref_dois))
        #print(i,doi)
        try:
            bib = cn.content_negotiation(ids = doi, format = "bibentry")
            year = re.search(r'year = {(\S+)},', bib).group(1) #year  = 10.1016/j.ecoleng.2021.106488,
            title = re.search(r'title = {(.*)}', bib).group(1) #title = {xxx xxxxx xxxx}
            crossref.append(
                {
                    "DOI" : doi.upper(),
                    "Year" : str(year),
                    "Title" : title
                }
            )
        #break
        except:
            no_crossref.append({"DOI": doi.upper()})
            print("could not retrieve bib for: "+doi.upper())
    print('complete extractHabanero:',len(datacite_no_crossref),' Unique DOIs')
    print('complete\tdaciteExtractCrossref(datacite_no_crossref)', flush=True)
    return crossref, no_crossref

def mergeCrossrefHabanero(datacite_crossref,datacite_habanero):
    '''
    merges crossref and habanero lists
    '''
    print('init\t\tmergeCrossrefHabanero(datacite_crossref,datacite_habanero)', flush=True)
    for d in datacite_crossref:
        for h in datacite_habanero:
            if d['DOI'].upper() == h['DOI'].upper():
                d['Title'] = h['Title']
                d['Year'] = h['Year']
    print('complete\tmergeCrossrefHabanero(datacite_crossref,datacite_habanero)', flush=True)
    return datacite_crossref

def matchDataCiteEOS(datacite, eos_dois):
    '''
    matches datacite found dois to gesdisc eos csv DOIs
    returns list of dicts with desired keys ['DOI', 'Title', 'Year', 'Cited-References']
    '''
    print('init\t\tmatchDataCiteEOS(datacite, eos_dois)', flush=True)
    for i,d in enumerate(datacite):
        #print(i)
        if i % 100 == 0:
            print(i,'/',len(datacite))
        cited_references = set()
        for doi in d['tags']:
            cited_references.add(doi)
        d['Cited-References'] = list(cited_references)
        del d['tags']
    valid_gesdisc = list()
    for i,e in enumerate(eos_dois):
        valid_gesdisc.append(e['EOS DOI'])
    count = 0
    for i,g in enumerate(datacite):
        for j,e in enumerate(eos_dois):
            for k,ref in enumerate(g['Cited-References']):
                if ref == e['EOS DOI']:
                    #print(i,j,k,c,type(c))
                    g['Cited-References'][k] = e
                    count += 1
    print('matching dois:',count)
    print('complete\tmatchDataCiteEOS(datacite, eos_dois)', flush=True)
    return datacite



eos_dois = eosutil.getEOSCSV()                              # returns list of dicts with keys = ['DOI_NAME', 'LP_AGENCY', 'SPECIAL']
eos_dois = eosutil.getAcronyms(eos_dois)                    # replaced long LP Agency names to short Acronyms

datacite_found = getDataCite(eos_dois)
datacite_transposed = dataciteTranspose(datacite_found)            #converts datacite_found with EOS DOI as the main key, and transforms the main key to the publication DOI
datacite_crossref = dataciteExtractCrossref(datacite_transposed)                    # gets title and year from crossref api

eos_datacite_matched = matchDataCiteEOS(datacite_crossref, eos_dois)   #matches datacite found 'dois' to EOS DOIs change to datacite_dois if working with habanero
eosutil.saveJSON(eos_datacite_matched,'debug_eos_datacite_matched.json')

#eos_datacite_matched = eosutil.loadJSON('debug_eos_datacite_matched.json')
eos_datacite_matched = eosutil.excludeBadTypes(eos_datacite_matched)

eosutil.saveJSON(eos_datacite_matched,'debug_eos_datacite_matched.json')

# Find new records since the last time the update was made
g_citations_old = eosutil.loadJSON('eos_datacite_matched_'+old_date+'.json')
g_citations_incr = eosutil.findNewCitations(g_citations_old, eos_datacite_matched)
eosutil.saveJSON(g_citations_incr,'eos_datacite_matched_'+new_date+'.incr.json')

# Save all citations
eosutil.saveJSON((g_citations_old+g_citations_incr),'eos_datacite_matched_'+new_date+'.json')
