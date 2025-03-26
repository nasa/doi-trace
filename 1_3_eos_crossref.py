'''
Top note: commented out Habanero API because it does not indicate preprints like crossref.restful does

getCrossRef(prefix):                   from EventData returns a list of DOIS and a list of non-DOI references (such as wikipedia, websites or twitter)
extractCrossRef(crossref_valid):       iterates over the valid DOIs through the crossref.restful API
crAddTags(cr_dois,crossref_valid):     adds Cited-References to the DOIs
matchCrossRef_EOS(eos_dois,cr_dois):   returns list of dicts ['DOI', 'Title', 'Year', 'Cited-References']
doiNotInEOS(eos_crossref_matched):     returns a list of crossref dois that dont have eos dois

Event Data User Guide
https://www.eventdata.crossref.org/guide/service/query-api/

'''

import requests
import json
import re
from crossref.restful import Works, Etiquette
import unicodedata # used to transform unicode to ascii such as '\u2026' to '...'
from bs4 import BeautifulSoup # used together with unescape to remove html tags such as &lt;
from html import unescape # used together with unescape to remove html tags such as &lt;
import pandas as pd
import eosutilities as eosutil

#set my_etiquette for crossref API. 
my_etiquette = eosutil.loadJSON('crossref_etiquette.json')
works = Works(etiquette=Etiquette(my_etiquette['project_name'], my_etiquette['version'], my_etiquette['organization'], my_etiquette['email']))

import time
from datetime import datetime
now = datetime.now()

new_date = 'jan2025'
old_date = 'sep2024'

def getCrossRef(eos_dois):
    '''
    expects prefix such as 10.5067
    returns a list of DOIS and a list of non-DOI references (such as wikipedia, websites or twitter)
    '''
    prefix = ['10.5067','10.3334','10.7927']
    good_source_ids = [
        'crossref',
        'datacite'
    ]
    bad_source_ids = [
        'cambia-lens',
        'newsfeed',
        'reddit-links',
        'twitter',
        'wikipedia',
        'wordpressdotcom'
    ]
    valid_dois = [d['EOS DOI'] for d in eos_dois]
    crossref_valid = list()
    crossref_invalid = list()
    for p in prefix:
        cursor = ''
        while cursor is not None:
            print('https://api.eventdata.crossref.org/v1/events?mailto=',my_etiquette['email'],'&obj-id.prefix=',p,'&cursor=',cursor)
            r = requests.get('https://api.eventdata.crossref.org/v1/events?mailto='+my_etiquette['email']+'&obj-id.prefix='+p+'&cursor='+cursor) #+'&from-occurred-date=2023-01-01')
            crossref_get = json.loads(r.text)
            if cursor == '':
                print('EOS DOI:',p)
                print('CrossRef results to be pulled:',crossref_get['message']['total-results'],'in batches of 1000')
            cursor = crossref_get['message']['next-cursor']
            print(cursor, flush=True)
            for c in crossref_get['message']['events']:
                source_id = c['source_id']
                if source_id not in bad_source_ids:
                    eos_doi = c['obj_id'].upper()
                    eos_doi = eos_doi.rsplit('HTTPS://DOI.ORG/')[1]
                    #eos_doi = eos_doi.rstrip('.')
                    #eos_doi = eos_doi.rstrip(')')
                    c['subj_id'] = c['subj_id'].upper()
                    if eos_doi in valid_dois and re.search('HTTPS://DOI.ORG/',c['subj_id']):
                        crossref_valid.append(
                            {
                                "DOI" : c['subj_id'].rsplit('HTTPS://DOI.ORG/')[1],
                                "EOS DOI" : eos_doi
                            }
                        )
                    else:
                        crossref_invalid.append(
                            {
                                "DOI" : c['subj_id'],
                                "EOS DOI" : eos_doi
                            }
                        )
    print('CrossRef results pulled:',len(crossref_valid) + len(crossref_invalid))
    print('crossref_valid:',len(crossref_valid))
    print('crossref_invalid:',len(crossref_invalid))
    print('complete\tgetCrossRef(prefix)', flush=True)
    return crossref_valid

def extractCrossRef(crossref_dois):
    '''
    iterates over the valid DOIs through the crossref.restful API
    '''
    print('init\t\textractCrossRef(crossref_valid)', flush=True)
    crossref = list()
    no_crossref = list()
    print('extractCrossRef:',len(crossref_dois),' Unique DOIs')
    for i, rec in enumerate(crossref_dois):
        doi = rec['DOI']
        if i % 100 == 0:
            print(i,'/',len(crossref_dois),'\t',now.strftime("%H:%M:%S"), flush=True)
        #print(i,doi, flush=True)
        rec['Title'] = ''
        rec['Year'] = ''
        rec['Type'] = ''
        try:
            record = works.doi(doi)
            if record and (record.get('subtype') != 'preprint'):
                title = record['title'][0]
                title = BeautifulSoup(unescape(title), 'lxml').text #sanitize title from html tags
                title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode('ascii') # sanitize title from unicodea
                rec['Title'] = title
                try:
                    year = record['created'].get('date-parts')[0][0]
                    rec['Year'] = str(year)
                except:
                    try:
                        year = record['published-print'].get('date-parts')[0][0]
                        rec['Year'] = str(year)
                    except:
                        pass
                try:
                    rec['Type'] = record['type']
                except:
                    pass
                crossref.append(rec)
                print(rec['DOI'],rec['Year'],rec['Type'])
            else:
                no_crossref.append(rec)
                #print("could not retrieve bib for: "+doi.upper()).
        except:
            print(i,'/',len(crossref_dois),doi)
            pass
    print('complete extractCrossRef:',len(crossref_dois),' Unique DOIs')
    print('complete\textractCrossRef(crossref_valid)', flush=True)
    return crossref

def crAddTags(cr_dois,crossref_valid):
    '''
    adds Cited-References to the DOIs
    '''
    print('init\t\tcrAddTags(cr_dois,crossref_valid)', flush=True)
    for cr in cr_dois:
        cr['Cited-References'] = list()
        cr['Cited-References-Set'] = set()
        for entry in crossref_valid:
            if entry['DOI'].upper() == cr['DOI'].upper():
                eosdoi = {'EOS DOI': entry['EOS DOI']}
                cr['Cited-References-Set'].add(tuple(eosdoi.items()))
        for set_ref in list(cr['Cited-References-Set']):
            cr['Cited-References'].append(dict(set_ref))
        del cr['Cited-References-Set']
    print('complete\tcrAddTags(cr_dois,crossref_valid)', flush=True)
    return cr_dois

def combineDuplicates(crossref_pairs):
    df = pd.DataFrame(eos_dois)
    g_unique_dois = set()
    for g in crossref_pairs:
        g_unique_dois.add(g['DOI'])
    g_unique_results = list()
    for doi in list(g_unique_dois):
        g_unique_results.append({
            'DOI' : doi,
            'EOS DOIs' : set()
            #'Cited-References' : ()
        })
    for rec in crossref_pairs:
        for g_unique in g_unique_results:
            if rec['DOI'] == g_unique['DOI']:
                g_unique['EOS DOIs'].add(rec['EOS DOI'])
    for rec in g_unique_results:
        rec['Cited-References'] = list()
        for doi in rec['EOS DOIs']:
            rec['Cited-References'].append({
                    'EOS DOI':doi,
                    'LP Agency':df.loc[df['EOS DOI'] == doi]['LP Agency'].values[0],
                    'Shortname':df.loc[df['EOS DOI'] == doi]['Shortname'].values[0]
                        })
        del rec['EOS DOIs']
    return g_unique_results


def matchCrossRef_EOS(eos_dois,cr_dois):
    '''
    returns list of dicts ['DOI', 'Title', 'Year', 'Cited-References']
    '''
    print('init\t\tmatchCrossRef_EOS(eos_dois,cr_dois)', flush=True)
    cr_dois_with_tags = cr_dois.copy()
    matched_dois = list()
    for i,c in enumerate(cr_dois_with_tags):
        valid_eos_dois = list()
        for ref in c['Cited-References']:
            for j,e in enumerate(eos_dois):
                if ref['EOS DOI'] == e['EOS DOI']:
                    ref['LP Agency'] = e['LP Agency']
                    ref['Shortname'] = e['Shortname']
                    valid_eos_dois.append(ref)
        if valid_eos_dois:
            c['Cited-References'] = valid_eos_dois
            matched_dois.append(c)
    print('complete\tmatchCrossRef_EOS(eos_dois,cr_dois)', flush=True)
    return matched_dois

def setToDict(unique):
    l1 = list()
    for u in unique:
        l1.append(dict(u))
    return l1
def setToDOIList(doiset):
    l1 = list()
    for s in doiset:
        l1.append(s[0][1])
    return l1
def crossRefStats(crossref_restful,no_crossref_restful):
    #stats:
    print('crossref_restful:',len(crossref_restful))
    print('no_crossref_restful:',len(no_crossref_restful))

def doiNotInEOS(eos_crossref_matched):
    '''
    returns a list of crossref dois that dont have eos dois
    '''
    print('init\t\tdoiNotInEOS(eos_crossref_matched)', flush=True)
    not_in_eos = set()
    for i,e in enumerate(eos_crossref_matched):
        flag = 0
        for tag in e['Cited-References']:
            if not tag.get('LP Agency'):
                flag = 1
                not_in_eos.add(tag['EOS DOI'])
    not_in_eos = list(not_in_eos)            
    not_in_eos.sort()
    print('complete\tdoiNotInEOS(eos_crossref_matched)', flush=True)
    return not_in_eos

def findNewCitations(g_citations_old, g_citations_new):
    g_citations = list()
    old_result_ids = list()
    for i,g in enumerate(g_citations_old):
        old_result_ids.append(g['DOI'])
    for i,g in enumerate(g_citations_new):
        if g['DOI'] in old_result_ids:
            continue
        g_citations.append(g)
    return g_citations


eos_dois = eosutil.getEOSCSV()                            # returns list of dicts with keys = ['DOI_NAME', 'LP_AGENCY', 'SPECIAL']
eos_dois = eosutil.getAcronyms(eos_dois)               # replaced long LP Agency names to short Acronyms

# enter list of prefix. returns a list of DOIS and a list of non-DOI references (such as wikipedia, websites or twitter)
g_citations = getCrossRef(eos_dois) 
eosutil.saveJSON(g_citations,'debug_eos_crossref_matched.json')

# Combine entries that have the same DOI and add Agency and ShortName to EOS DOIs
g_citations = combineDuplicates(g_citations)
eosutil.saveJSON(g_citations,'debug_eos_crossref_matched_no_dups.json')

# Extract Year, Title, and Type from Crossref. If not extracted save in no_crossref list
g_citations = extractCrossRef(g_citations)
eosutil.saveJSON(g_citations,'debug_eos_crossref_matched.json')

g_citations = eosutil.excludeBadTypes(g_citations)
eosutil.saveJSON(g_citations,'debug_eos_crossref_matched.json')

# Find new records since the last time the update was made
g_citations_old = eosutil.loadJSON('eos_crossref_matched_'+old_date+'.json')
g_citations = eosutil.findNewCitations(g_citations_old, g_citations)
eosutil.saveJSON(g_citations,'eos_crossref_matched_'+new_date+'.incr.json')

# Save all Crossref citations 
eosutil.saveJSON((g_citations_old+g_citations),'eos_crossref_matched_'+new_date+'.json')

