'''
getGoogleFromCrossref(g_citations):             for google results missing doi, run through crossref.restful API
removeNoCrossref(g_citations):                  if after running getGoogleFromCrossref(g_citations) function, if ['pub_doi'] is still empty, remove it from g_citations and add it to g_citations_no_crossref list
cleanGoogleCrossrefWorks(g_citations):          iterates over the crossref_restful_works list pulled from crossref API, finds the one with highest Jaro Winkler score.
matchGoogle_EOS(g_citations_clean, eos_dois):   matches google pulled 'dois' to eos csv DOIs
combineDuplicates(g_citations_clean):           combines duplicates

start zotero translation server:
    docker run -d -p 1969:1969 --rm --name translation-server translation-server
stop zotero translation server:
    docker kill translation-server
code is in /home/igerasim/translation-server

https://github.com/zotero/translation-server
'''

import unicodedata # used to transform unicode to ascii such as '\u2026' to '...'
from bs4 import BeautifulSoup # used together with unescape to remove html tags such as &lt;
from html import unescape # used together with unescape to remove html tags such as &lt;
import jellyfish
from jellyfish import jaro_winkler_similarity # used to find google & crossref title similarities
import os
import json
import re 

from crossref.restful import Works, Etiquette
import eosutilities as eosutil
#set my_etiquette for crossref API. It helps filter unusual requests, and contact if necessary.
my_etiquette = eosutil.my_etiquette
works = Works(etiquette=my_etiquette)

import time
from datetime import datetime
now = datetime.now()

# Change to True for search by DOI or False for search by ShortName
byDOI = False #True
new_date = 'feb2025'
old_date = 'aug2024'

def getGoogleFromCrossref(g_citations):
    '''
    from the google organic results, if the pub_doi is empty, the function queries crossref.restful API.
    query is 'Author (Year) Title'
    works.Work(query) returns a list of highest matching DOIS based on query.
    This function sanitizes the google retrieved title and crossref title from unicode characters and html tags.
    
    Jaro Winkler Similarity algorithm is used to give a score of title similarity.
    If the score is 1, break the loop, move on to next publication
    otherwise, add up to 3 differnt publications to ['crossref_restful_works'] list
    
    bad_type_list dismisses peer-reviews, posted-content, component and datasets from matching by title.
    
    returns a list of dicts with keys ['result_id', 'link', 'pub_doi', 'index', 'author', 'year', 'title', 'dois', 'crossref_restful_works']
    '''
    start = time.time()
    now = datetime.now()
    print('init\t\tgetGoogleFromCrossref(g_citations)',now.strftime("%H:%M:%S"), flush=True)
    bad_type_list = [ # list of publication types to ignore
        'peer-review', 
        'posted-content',
        'component',
        'dataset'
    ]
        
    for i,g in enumerate(g_citations):
        if i % 100 == 0:
            now = datetime.now()
            print(i,'/',len(g_citations),'\t',now.strftime("%H:%M:%S"), flush=True)
        #print(i,'/',len(g_citations), flush=True)
        if g.get('pub_doi','') == '': # if no pub_doi then run works.query
            author = g.get('author')
            year = g.get('year')
            if g.get('zotero') and len(g['zotero']) and g['zotero'].get('date' ,'') and re.search(r'\d{4}', g['zotero']['date']):
                year=re.search(r'\d{4}', g['zotero']['date'])[0]
                year = '('+year+')'
            title = g.get('title')
            title = BeautifulSoup(unescape(title), 'lxml').text #sanitize title from html tags
            title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode('ascii') # sanitize title from unicode
            title = title.replace('...','')
            query = str(author)+' + '+str(year)+' + '+str(title) # create query for works.Works
            query = query.replace('+  +','+') # when year is empty, remove extra + sign
            print(query)
            w = works.query(bibliographic=query).select('DOI', 'title','published-print','issue','type') # keys to retrieve
            g['crossref_restful_works'] = list()
            works_iter = 0
            for j,item in enumerate(w): # iterate over the queried list, break after 5 results pulled
                item_type = item.get('type',None)
                works_iter += 1
                if works_iter > 3:
                    break
                if item and item_type not in bad_type_list: # if item not in the bad list
                    #print(i,j,works_iter,item_type)
                    cr_title = item.get('title')
                    cr_doi = item.get('DOI')
                    if cr_title:
                        cr_title = cr_title[0]
                        cr_title = BeautifulSoup(unescape(cr_title), 'lxml').text #sanitize title from html tags
                        cr_title = unicodedata.normalize('NFKD', cr_title).encode('ascii', 'ignore').decode('ascii') # sanitize title from unicode
                        
                        jaro_winkler_s = jaro_winkler_similarity(title.upper(),cr_title.upper()) # get jaro winkler similarity score
                        
                    cr_year = None # get year from either published-print or issue
                    try:
                        cr_year = item['published-print']['date-parts'][0][0]
                        c_published += 1
                    except:
                        pass
                    if not cr_year:
                        try:
                            cr_year = item['issue']['date-parts'][0][0]
                            c_issued += 1
                        except:
                            pass
                    #print(i,j,jaro_winkler_s)
                    if jaro_winkler_s > 0.95: # if the jaro score is above 0.9, add it to the list of cited-references
                        #print(cr_doi,year)
                        flag = 1 if item_type == 'journal-article' else 0 # priority for journal-articles
#                         year = year.replace('(','')
#                         year = year.replace(')','')
#                         if (cr_year) and (year):
#                             if (cr_year == int(year)) or (cr_year == int(year)+1) or (cr_year == int(year)-1):
                        g['crossref_restful_works'].append(
                            {
                                'cr_doi': cr_doi,
                                'cr_year': year,
                                'g_title': title,
                                'cr_title': cr_title,
                                'type' : item_type,
                                'year' : year,
                                'score' : [jaro_winkler_s,flag]
                            }
                        )
                        #print(cr_year,'\t', year,'\t',jaro_winkler_s,'\t',title)
                        #print(i,j,len(g['crossref_restful_works']))
                        if jaro_winkler_s == 1.0: #if perfect score of 1.0, then break
                            #print('jaro 1.0')
                            break
                        if len(g['crossref_restful_works']) > 3: # break after 3 valid dois added
                            break
                            # else:
                            #     print(cr_year,'\t', year,jaro_winkler_s,'\t',title)
    end = time.time()
    print('complete\tgetGoogleFromCrossref(g_citations)\tTotal Execution Time:',end - start, flush=True)
    return g_citations


def removeNoCrossref(g_citations):
    '''
    if after running getGoogleFromCrossref(g_citations) function, if ['pub_doi'] is still empty, remove it from g_citations and add it to g_citations_no_crossref list
    return g_citations, g_citations_no_crossref
    '''
    print('init\t\tremoveNoCrossref(g_citations)', flush=True)
    g_citations_no_crossref = list()
    remove_index = list()
    for i,g in enumerate(g_citations):
        if g['pub_doi'] == '':
            if not g.get('crossref_restful_works') or len(g.get('crossref_restful_works')) == 0: # if no crossref works were pulled
                g_citations_no_crossref.append(g)
                remove_index.append(i)
    remove_index.sort()
    #print('remove_index',remove_index)
    for e in reversed(remove_index): 
        del g_citations[e] # remove the g_citations that have empty pub_doi and no crossref works
    print('complete\tremoveNoCrossref(g_citations)', flush=True)
    return g_citations, g_citations_no_crossref

def cleanGoogleCrossrefWorks(g_citations):
    '''
    iterates over the crossref_restful_works list pulled from crossref API, finds the one with highest Jaro Winkler score.
    keeps the max, discards the rest
    
    returns g_citation with valid pub_doi from crossref, and clean title.
    '''
    print('init\t\tcleanGoogleCrossrefWorks(g_citations)', flush=True)
    for i,g in enumerate(g_citations):
        if g.get('crossref_restful_works') and g['pub_doi'] == '':
            score_list = list()
            for j,w in enumerate(g['crossref_restful_works']):
                score_list.append(w['score'])
                try:
                    del w['type']
                except:
                    pass
                try:
                    del w['score']
                except:
                    pass
            max_score = max(score_list) # get highest jaro similarity and journal-article (score = 1)
            max_index = score_list.index(max_score) #get index
            #print(i,max_score,max_index)
            g['pub_doi'] = g['crossref_restful_works'][max_index]['cr_doi']
            #g['cr_doi'] = g['crossref_restful_works'][max_index]['cr_doi']

            if not g['crossref_restful_works'][max_index]['cr_title']: # rare occurance that cr_title is None
                g['crossref_restful_works'][max_index]['cr_title'] = ''
                #print(g['result_id'])
                
            if len(g['title']) < len(g['crossref_restful_works'][max_index]['cr_title']):
                g['title'] = g['crossref_restful_works'][max_index]['cr_title']
                
            if not g['year']:
                g['year'] = '('+str(g['crossref_restful_works'][max_index]['year'])+')'
                
            del g['crossref_restful_works']
    print('complete\tcleanGoogleCrossrefWorks(g_citations)', flush=True)
    return g_citations

def matchGoogle_EOS(g_citations_clean, eos_dois):
    '''
    matches google pulled 'dois' to eos csv DOIs
    returns list of dicts with desired keys ['result_id', 'DOI', 'Title', 'Year', 'Cited-References']
    '''
    print('init\t\tmatchGoogle_EOS(g_citations_clean, eos_dois)', flush=True)
    g_citations = list()
    for i,g in enumerate(g_citations_clean):
        #print(i)
        cited_references = set()
        if byDOI:
            for d in g['dois']:
                cited_references.add(d)
        else:
            for d in g['ShortNames']:
                cited_references.add(d)
        year = g.get('year')
        if year:
            year = year.replace('(','')
            year = year.replace(')','')
        g_citations.append(
        {
           'result_id': g['result_id'],
           'link': g['link'],
           'pub_doi': g['pub_doi'].upper(),
           'DOI' : g['pub_doi'].upper(),
           'Title': g.get('title'),
           'Author': g.get('author'),
           'Year': year,
           'Type': g.get('Type'),
           'Cited-References': list(cited_references),
           'zotero' : g.get('zotero')
        })
    
    count = 0
    for i,g in enumerate(g_citations):
        for j,e in enumerate(eos_dois):
            for k,ref in enumerate(g['Cited-References']):
                if ref == e['EOS DOI']:
                    #print(i,j,k,c,type(c))
                    g['Cited-References'][k] = e
                    count += 1
    print(count)
    print('complete\tmatchGoogle_EOS(g_citations_clean, eos_dois)', flush=True)
    return g_citations

def combineDuplicates(g_citations_clean):
    ''' combines duplicates '''
    g_unique_dois = set()
    for g in g_citations_clean:
        g_unique_dois.add(g['pub_doi'].upper())
    g_unique_results = list()
    for doi in list(g_unique_dois):
        g_unique_results.append({
            'result_id' : list(),
            'link': list(),
            'pub_doi' : doi,
            'refs' : set()
        })
    for g_clean in g_citations_clean:
        for g_unique in g_unique_results:
            if g_clean['pub_doi'].upper() == g_unique['pub_doi'].upper():
                g_unique['result_id'].append(g_clean['result_id'])
                g_unique['link'].append(g_clean['link'])
                g_unique['author'] = g_clean['author']
                g_unique['year'] = g_clean['year']
                g_unique['title'] = g_clean['title']
                if g_clean.get('zotero', ''):
                    g_unique['zotero'] = g_clean['zotero']
                else:
                    g_unique['zotero'] = {}
                if byDOI:
                    for doi in g_clean['dois']:
                        g_unique['refs'].add(doi)
                else:
                    for sn in g_clean['ShortNames']:
                        g_unique['refs'].add(sn)
    for g in g_unique_results:
        if byDOI:
            g['dois'] = list(g['refs'])
        else:
            g['ShortNames'] = list(g['refs'])
        del g['refs']
    return g_unique_results

def getZoteroItemsByURL(g):
    url=g['link']
    print(url)
    g['zotero'] = {}
    if re.search('pure.mpg.de', url) or re.search('gfzpublic.gfz-potsdam.de', url):
        return g
    stream = os.popen('curl -d \"'+url+'\" -H \'Content-Type: text/plain\' http://127.0.0.1:1969/web')
    output = stream.read()
    print(output)
    if re.match('No items returned from any translator', output):
        return g
    try:
        json_object = json.loads(output)
        if re.search('ShieldSquare Captcha', json_object[0]['title']):
            return g
        g['zotero'] = json_object[0]
        if g['zotero'].get('DOI', ''):
            g['pub_doi'] = g['zotero']['DOI']
            # need to handle "DOI": "https://doi.org/10.26076/49d7-eeca"
        elif g['zotero'].get('extra', '') and re.search('DOI', g['zotero']['extra']):
            resp = re.search(r'(10\.\d+.*)$', g['zotero']['extra'])     
            if resp: 
                g['pub_doi'] = resp[0]
        if g['zotero'].get('date' ,''):
            g['year'] = re.search(r'\d{4}', g['zotero']['date'])[0]
            g['year'] = '('+g['year']+')'
    except:
        pass
    return g

def getZoteroItemsByDOI(g):
    if not g['pub_doi']:
        return g
    stream = os.popen('curl -d \"'+g['pub_doi']+'\" -H \'Content-Type: text/plain\' http://127.0.0.1:1969/search')
    output = stream.read()
    print(output)
    if re.match('No items returned from any translator', output):
        return g
    try:
        json_object = json.loads(output)
        g['zotero'] = json_object[0]
        if g['zotero'].get('DOI', ''):
            g['pub_doi'] = g['zotero']['DOI']
        elif g['zotero'].get('extra', '') and re.search('DOI', g['zotero']['extra']):
            resp = re.search(r'(10\.\d+.*)$', g['zotero']['extra'])
            if resp:
                g['pub_doi'] = resp[0]
        if g['zotero'].get('date' ,''):
            g['year'] = re.search(r'\d{4}', g['zotero']['date'])[0]
            g['year'] = '('+g['year']+')'
    except:
        pass
    return g


def getZoteroItems(g_citations):
    for i,g in enumerate(g_citations):
        if g.get('pub_doi','') and len(g['pub_doi']): # if pub_doi then continue
            continue
        if g.get('zotero', '') and len(g['zotero']):
            if re.match(r'webpage', g['zotero']['itemType']) and len(g['pub_doi']):
                g = getZoteroItemsByDOI(g)
            continue
        else:
            g = getZoteroItemsByURL(g)
            if len(g['zotero']) and not re.match(r'webpage', g['zotero']['itemType']):
                continue
        if g['pub_doi']:
            g = getZoteroItemsByDOI(g)
    return g_citations

def removeDatasets(g_citations):
    g_citations_no_datasets = list()
    for i,g in enumerate(g_citations):
        if g['pub_doi'] and (re.search('10.3334', g['pub_doi']) or re.search('10.5067', g['pub_doi']) or re.search('10.7927', g['pub_doi'])):
            continue
        g_citations_no_datasets.append(g)
    return(g_citations_no_datasets)

def addCrossrefType(g_citations):
    for i,g in enumerate(g_citations):
        if g.get('Type', ''):
            continue
        g['Type'] = ""
        pub_doi = None
        if g.get('DOI', ''):
            pub_doi = g['DOI']
        else:
            pub_doi = g['pub_doi']
        if pub_doi:
            print(pub_doi)
            try:
                g['Type'] = works.doi(pub_doi)['type']
                print(g['Type'])
            except:
                print('Cannot get Crossref type')
                continue
    return g_citations

def addDOItoZotero(g_citations):
    for i,g in enumerate(g_citations):
        if not len(g['pub_doi']) or not g.get('zotero', ''):
            continue
        if g['zotero'].get('DOI', '') or (g['zotero'].get('extra', '') and re.search('DOI', g['zotero']['extra'])):
            continue
        print(g['pub_doi'])
        g = getZoteroItemsByDOI(g)
        if g['zotero'].get('DOI', '') or (g['zotero'].get('extra', '') and re.search('DOI', g['zotero']['extra'])):
            continue
        g['zotero']['extra'] = "DOI: "+g['pub_doi']
    return g_citations

def findNewCitations(g_citations_old, g_citations_new):
    g_citations = list()
    old_result_ids = list()
    for i,g in enumerate(g_citations_old):
        old_result_ids.append(g['result_id'])
    for i,g in enumerate(g_citations_new):
        if g['result_id'] in old_result_ids:
            continue
        g_citations.append(g)
    return g_citations

eos_dois = eosutil.getEOSCSV()                              # returns list of dicts with keys = ['DOI_NAME', 'LP_AGENCY', 'SPECIAL']
eos_dois = eosutil.getAcronyms(eos_dois)                    # replaced long LP Agency names to short Acronyms

if byDOI:
    g_citations = eosutil.loadJSON('google_organic_citations_'+new_date+'.incr.json')
else:
    g_citations = eosutil.loadJSON('google_organic_citations_short_name_ges_disc_'+new_date+'.incr.json')


g_citations = getGoogleFromCrossref(g_citations)        # queries crossref for missing pub_doi entries
g_citations = cleanGoogleCrossrefWorks(g_citations)     # for records that have no pub_doi assigns cr_doi to pub_doi 
eosutil.saveJSON(g_citations,'debug_google_citations_wcrossref.json')

g_citations = removeDatasets(g_citations)
eosutil.saveJSON(g_citations,'debug_google_citations_no_datasets.json')

g_citations_dois_only,g_citations_no_doi = removeNoCrossref(g_citations) # removes entires with no DOI
eosutil.saveJSON(g_citations_dois_only,'debug_google_citations_dois_only.json')
g_citations = g_citations_dois_only

g_citations = eosutil.loadJSON('debug_google_citations_dois_only.json')
g_citations = combineDuplicates(g_citations)
eosutil.saveJSON(g_citations,'debug_google_citations_no_dups.json')

g_citations = eosutil.getCrossRefYearAndType(g_citations)
g_citations = eosutil.excludeBadTypes(g_citations)
eosutil.saveJSON(g_citations,'debug_google_citations_no_bad_types.json')

g_citations = matchGoogle_EOS(g_citations, eos_dois)      # reformat records so they could be combined with other sources
eosutil.saveJSON(g_citations,'debug_eos_google_matched.json')

# Find new records since the last time the update was made
if byDOI:
    g_citations_old = eosutil.loadJSON('eos_google_matched_'+old_date+'.json')
    g_citations_incr = eosutil.findNewCitations(g_citations_old, g_citations)

    eosutil.saveJSON(g_citations_incr,'eos_google_matched_'+new_date+'.incr.json')

    # store the entire collection of GS citations
    eosutil.saveJSON((g_citations_old+g_citations_incr),'eos_google_matched_'+new_date+'.json')
else:
    eosutil.saveJSON(g_citations,'google_short_name_ges_disc_'+new_date+'.incr.json')
