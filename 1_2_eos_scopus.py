'''
    Obtain Scopus API key from https://dev.elsevier.com/apikey/manage and store it in scopus_api_key.json
    The api key sometimes exceeded limits, you need to get a new key when it happens

    getSCOPUS(term)                     receives an EOS DOI, and returns ElsSearch result back.
    matchSCOPUS_EOS(eos_dois)           uses getSCOPUS() function and then matches with gesdisc EOS

    https://raw.githubusercontent.com/ElsevierDev/elsapy/master/exampleProg.py
    https://github.com/ElsevierDev/elsapy/blob/master/README.md

    Before running the script set new_date and old_date values
'''

import requests
import re
import json

from elsapy.elsclient import ElsClient
from elsapy.elsprofile import ElsAuthor, ElsAffil
from elsapy.elsdoc import FullDoc, AbsDoc
from elsapy.elssearch import ElsSearch
import eosutilities as eosutil
import time
from datetime import datetime
now = datetime.now()

scopus_api_key = eosutil.loadJSON('scopus_api_key.json')['scopus_api_key']
print(scopus_api_key)

new_date = 'jan2025'
old_date = 'sep2024'

SEARCH_CROSSREF = False

def getSCOPUS(term):
    '''
    receives an EOS DOI, and returns ElsSearch result back.
    '''
    term = '"'+str(term)+'"'
    term = term.split('(',1)[0] # for ORNLS that have parenthesis in the doi name
    #print(term)
    client = ElsClient(scopus_api_key)
    ## Initialize doc search object using Scopus and execute search, retrieving all results
    doc_srch = ElsSearch(term,'scopus')
    doc_srch.execute(client, get_all = True)
    #print (term, len(doc_srch.results), "results.")
    return doc_srch.results

def matchSCOPUS_EOS(eos_dois):
    '''
    function uses getScopus() for every EOS doi in eos_dois
    creates a full_scopus list
    creates scopus_and_refs with only SCOPUS_ID and EOS DOI
    returns a list of dicts ['SCOPUS_ID', 'DOI', 'Title', 'Year', 'ISBN', 'ISSN', 'EISSN', 'Cited-References']
    '''
    print('init\t\tmatchSCOPUS_EOS(eos_dois)', flush=True)
    full_scopus = list()
    scopus_and_refs = list()
    scopus_errors = list()
    for i,e in enumerate(eos_dois):
        if i % 100 == 0:
            print(i,'/',len(eos_dois),'\t',now.strftime("%H:%M:%S"), flush=True)
        try:
            results = getSCOPUS(e['EOS DOI']) # will return 'Result set was empty' if no matches
        except:
            print(e['EOS DOI'],'could not be pulled from SCOPUS ElsSearch')
            results = [{'error': None}]
            pass
        if not results[0].get('error', None) and (results[0].get('error', None) != 'Result set was empty'): # if no error was returned
            for result in results:
                try:
                    isbn = result.get('prism:isbn', None)
                    if isbn:
                        isbn = isbn[0].get('$', None)
                except:
                    pass
                try:
                    scopus_id = result['dc:identifier']
                    full_scopus.append({'SCOPUS_ID' : re.sub('SCOPUS_ID:','',result.get('dc:identifier','')),
                                       'DOI' : result.get('prism:doi', None),
                                       'Title' : result.get('dc:title', None),
                                       'Year' : re.search(r'\d{4}',result.get('prism:coverDate')).group(0), # get first four digits from yyyy-mm-dd
                                       'ISBN' : isbn,
                                       'ISSN' : result.get('prism:issn', None),
                                       'EISSN' : result.get('prism:eIssn', None),
        #                                'EOS DOI': e['EOS DOI'],
        #                                'LP Agency': e['LP Agency'],
        #                                'Shortname': e['Shortname']
        #                                'Cited-References': [e]
                                       #'source-id' : entry.get('source-id', None)
                                      })
                    scopus_and_refs.append({'SCOPUS_ID' : re.sub('SCOPUS_ID:','',result.get('dc:identifier','')),
                                            'Cited-References': [e]
                                      })
                except:
                    print(e['EOS DOI'],'missing scopus_id')
                    scopus_errors.append(e['EOS DOI'])
    
    # create unique list of scopus DOIs
    unique = set()
    for doi in full_scopus:
        unique.add(tuple(doi.items()))
    unique_list = []
    for u in unique:
        unique_list.append(dict(u))
    # add citation list to each scopus DOI
    for u in unique_list:
        u['Cited-References'] = []
        for sr in scopus_and_refs:
            if u['SCOPUS_ID'] == sr['SCOPUS_ID']:
                u['Cited-References'].append(sr['Cited-References'][0])
    #uppercases DOIS
    for u in unique_list:
        if u['DOI']:
            u['DOI'] = u['DOI'].upper()
    eosutil.saveJSON(scopus_errors,'debug_scopus.json')
    print('complete\tmatchSCOPUS_EOS(eos_dois)', flush=True)
    return unique_list

def removeNullDOIs(scopus_dois):
    '''
    removes entries where DOI is null
    '''
    null_dois=0
    wos = list()
    for e in scopus_dois:
        if e["DOI"]:
            wos.append(e)
        else:
            null_dois += 1
    print('removeNullDOIs(scopus_dois): removed ',null_dois)
    return wos

def findNewCitations(g_citations_old, g_citations_new):
    g_citations = list()
    old_result_ids = list()
    for i,g in enumerate(g_citations_old):
        old_result_ids.append(g['SCOPUS_ID'])
    for i,g in enumerate(g_citations_new):
        if g['SCOPUS_ID'] in old_result_ids:
            continue
        g_citations.append(g)
    return g_citations


eos_dois = eosutil.getEOSCSV()                         # returns list of dicts with keys = ['DOI_NAME', 'LP_AGENCY', 'SPECIAL']
eos_dois = eosutil.getAcronyms(eos_dois)               # replaced long LP Agency names to short Acronyms

g_citations = matchSCOPUS_EOS(eos_dois)                # uses getSCOPUS() function and then matches with gesdisc EOS
eosutil.saveJSON(g_citations,'debug_eos_scopus_matched_wnull_dois.json')
g_citations = removeNullDOIs(g_citations)
eosutil.saveJSON(g_citations,'debug_eos_scopus_matched.json')

g_citations_old = eosutil.loadJSON('eos_scopus_matched_'+old_date+'.json')
g_citations = findNewCitations(g_citations_old, g_citations)
eosutil.saveJSON(g_citations,'debug_eos_scopus_matched.json')

g_citations = eosutil.addCrossrefType(g_citations)
g_citations = eosutil.excludeBadTypes(g_citations)

eosutil.saveJSON(g_citations,'eos_scopus_matched_'+new_date+'.incr.json')

# save all Scopus citations
eosutil.saveJSON((g_citations_old+g_citations),'eos_scopus_matched_'+new_date+'.json')

