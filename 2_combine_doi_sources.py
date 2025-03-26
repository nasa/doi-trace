'''
combine_sources():                       combines all wos / scopus / datacite / google / crossref eos_matched json files
combine_sources_dois(eos_matched):       create unique set of DOIs and covnert to list of dictionaries
addTags(combined_dois):                  create unique sets of Cited-References and tags for each DOI
setsToDicts(combined_dois):              converts sets of Cited-References and tags to lists of dicts
noYear(combined_dois_json):              for DOIs without a year, run through crossref and habanero
'''
import json
import re
from crossref.restful import Works, Etiquette
from habanero import cn
import glob
import pandas as pd
import eosutilities as eosutil

my_etiquette = eosutil.loadJSON('crossref_etiquette.json')
works = Works(etiquette=Etiquette(my_etiquette['project_name'], my_etiquette['version'], my_etiquette['organization'], my_etiquette['email']))

new_date = 'jan2025'
old_date = 'sep2024'


def combine_sources():
    print('init\t\tcombine_sources()', flush=True)
    '''
    combines all wos / scopus / datacite / google / crossref eos_matched json files
    '''
    file_names = glob.glob('data/eos_*_matched_'+new_date+'.incr.json')
    eos_matched = list()
    for f in file_names:
        json_file = f.replace('data/','')
        print(json_file)
        eos_matched.append([json_file,
                            json_file.split('_',2)[1], #source name wos / scopus / datacite / google / crossref
                            eosutil.loadJSON(json_file)
                           ])
    # ['wos_eos_matched.json', 'db:wos', json]

    #non unique DOIS:
    count = 0
    for db in eos_matched:
        print(db[0]+': '+str(len(db[2])))
        count += len(db[2])
    print('Total:',count)
    print('complete\tcombine_sources()\n', flush=True)
    return eos_matched

def combine_sources_dois(eos_matched):
    '''
    create unique set of DOIs and convert to list of dictionaries
    '''
    print('init\t\tcombine_sources_dois(eos_matched)', flush=True)
    dois = set()
    for i,source in enumerate(eos_matched):
        for j,publication in enumerate(source[2]):
            try:
                dois.add(publication['DOI'].upper())
            except:
                pass
    combined_dois = list()
    for i,d in enumerate(list(dois)):
        combined_dois.append({
            'DOI' : d.upper(),
            'Title' : None,
            'Year' : None,
            'Cited-References' : set(),
            'tags' : set()
        })
        print(d.upper())
    print('unique DOIs:',len(combined_dois))
    print('complete\tcombine_sources_dois(eos_matched)\n', flush=True)
    return combined_dois

def addTags(combined_dois,eos_matched):
    '''
    create unique sets of Cited-References and tags for each DOI
    '''
    print('init\t\taddTagsToDOIS(combined_dois)', flush=True)
    for i,d in enumerate(combined_dois):
        if i % 1000 == 0:
            print('batch:',i,'/',len(combined_dois))
        for j,source in enumerate(eos_matched):
            for k,publication in enumerate(source[2]):
                #print(i,j,k)

                if d.get('DOI') and publication.get('DOI'):
                    if d['DOI'].upper() == publication['DOI'].upper():
                        if publication.get('Year') and not re.search('None', str(publication['Year'])):
                            d['Year'] = publication['Year']
                            if re.search('"', str(d['Year'])):
                                d['Year'] = re.sub('"', '', str(d['Year']))
                        if not d.get('Title'):
                            d['Title'] = publication.get('Title')
#                         elif len(d.get('Title')) < len(publication.get('Title')):
#                             d['Title'] = publication.get('Title')
                        for ref in publication['Cited-References']:
                            d['Cited-References'].add(tuple(ref.items()))
                            tag = ref.get('EOS DOI')
                            agency = ref.get('LP Agency')
                            if tag:
                                d['tags'].add(tuple(('tag','doi:'+str(tag).upper())))
                                d['tags'].add(tuple(('tag','db:'+str(source[1])))) #source[1] is the name of the db
                            if agency:
                                d['tags'].add(tuple(('tag','DAAC:'+str(agency))))
    print('complete\taddTagsToDOIS(combined_dois)\n', flush=True)
    return combined_dois

def setsToDicts(combined_dois):
    '''
    converts sets of Cited-References and tags to lists of dicts
    '''
    print('init\t\tsetsToDicts(combined_dois)', flush=True)
    for i,d in enumerate(combined_dois):
        #print(i)
        refs = list()
        tags = list()
        for ref in d['Cited-References']:
            refs.append(dict(ref))
        for tag in d['tags']:
            tags.append(dict([tag]))
        del d['Cited-References']
        del d['tags']
        d['Cited-References'] = refs
        d['tags'] = tags
    print('complete\tsetsToDicts(combined_dois)\n', flush=True)
    return combined_dois

def noYear(combined_dois_json):
    '''
    for DOIs without a year, run through crossref and habanero
    '''
    print('init\t\t noYear(combined_dois_json)', flush=True)
    combined = combined_dois_json.copy()
    for d in combined:
        if d.get('Year') == 'None':
            d['Year'] = None
        if d.get('Year'):
            d['Year'] = str(d['Year']).replace('{','')
            d['Year'] = d['Year'].replace('}','')
            d['Year'] = int(d['Year'])
    for i,d in enumerate(combined):
        if not d['Year'] or d['Year'] == '' or d['Year'] == 'None':
            #print(i)
            year = None
            try:
                record = works.doi(d['DOI'])
                if record:
                    try:
                        year = record['published']['date-parts'][0][0]
                        year = year.replace('{','')
                        year = year.replace('}','')
                    except:
                        pass
            except:
                pass
            d['Year'] = year

    from habanero import cn
    for i,d in enumerate(combined):
        if not d['Year'] or d['Year'] == '' or d['Year'] == 'None':
            #print(i)
            year = None
            try:
                bib = cn.content_negotiation(ids = d['DOI'], format = "bibentry")
                year = re.search(r'year = (\S+),', bib).group(1) #year  = 10.1016/j.ecoleng.2021.106488,
                year = year.replace('{','')
                year = year.replace('}','')
            except:
                pass
            d['Year'] = year

    for d in combined:
        if d.get('Year'):
            d['Year'] = str(d['Year'])
    print('complete\tnoYear(combined_dois_json)\n', flush=True)
    return combined

def get_publisher(combined):
    publishers = list()
    for i,d in enumerate(combined):
        try:
            record = works.doi(d['DOI'])
            if record:
                print(i, record['DOI'])
                if record.get('publisher', ''):
                    d['publisher'] = record['publisher']
                    added = 0
                    for publisher in publishers:
                        if publisher['publisher'].upper() == record['publisher'].upper():
                            publisher['count'] += 1
                            added = 1
                            break
                    if not added:
                        publishers.append({'publisher':record['publisher'], 'count':1})
        except:
            pass
    df = pd.DataFrame(publishers)
    df.to_csv('publishers.csv')
    return combined

def get_journal_name(combined):
    publishers = list()
    for i,d in enumerate(combined):
        try:
            record = works.doi(d['DOI'])
            if record:
                print(i, record['DOI'])
                if record.get('container-title', ''):
                    d['journal'] = record['container-title']
                    added = 0
                    for publisher in publishers:
                        if publisher['container-title'].upper() == record['container-title'].upper():
                            publisher['count'] += 1
                            added = 1
                            break
                    if not added:
                        publishers.append({'publisher':record['container-title'], 'count':1})
        except:
            pass
    df = pd.DataFrame(publishers)
    df.to_csv('journals.csv')
    return combined

def crossref_overlap1(combined):
    combined_dois_json = combined.copy()
    for i,d in enumerate(combined_dois_json):
        d['cr_references'] = 0
        try:
            record = works.doi(d['DOI'])
            if record:
                print(i, record['DOI'])
                if record.get('reference', ''):
                    print(len(record['reference']), ' references')
                    d['cr_references'] = len(record['reference'])
        except:
            pass
    return combined_dois_json

def crossref_overlap(combined):
    combined_dois_json = combined.copy()
    total = len(combined_dois_json)
    cr_overlap = 0
    cr_in_unstr = 0
    cr_in_doi = 0
    cr_event_in_doi = 0
    cr_event_in_unstr = 0
    
    for i,d in enumerate(combined_dois_json):
        counted = 0
        #print(d['tags'])
        for tag in d['tags']:
            if tag['tag'] == "db:crossref":
                counted = 1
                break
        try:
            record = works.doi(d['DOI'])
            if record:
                print(i, record['DOI'])
                cr_overlap += 1
                if record.get('reference', ''):
                    print(len(record['reference']), ' references')
                    #cr_wrefs += 1
                    found_doi = 0
                    for j,r in enumerate(record['reference']):
                        if found_doi:
                            break
                        if record['reference'][j].get('DOI', ''):
                            if '10.5067/' in record['reference'][j]['DOI'] or '10.3334/' in record['reference'][j]['DOI'] or '10.7927/' in record['reference'][j]['DOI']:
                                record['reference'][j]['DOI'] = re.sub('\u2010', '-', record['reference'][j]['DOI'])
                                for tag in d['tags']:
                                    if 'doi:' in tag['tag']:
                                        doi = tag['tag'].split(':')[1]
                                        if doi.upper() in record['reference'][j]['DOI'].upper():
                                            if counted:
                                                cr_event_in_doi += 1
                                            else:
                                                cr_in_doi += 1
                                                d['tags'].append({'tag':"db:crossref"})
                                            found_doi = 1
                                            break
                        if record['reference'][j].get('unstructured', ''):
                            if '10.5067/' in record['reference'][j]['unstructured'] or '10.3334/' in record['reference'][j]['unstructured'] or '10.7927/' in record['reference'][j]['unstructured']:   
                                record['reference'][j]['unstructured'] = re.sub('\u2010', '-', record['reference'][j]['unstructured'])
                                for tag in d['tags']:
                                    if 'doi:' in tag['tag']:
                                        doi = tag['tag'].split(':')[1]
                                        if doi.upper() in record['reference'][j]['unstructured'].upper():
                                            if counted:
                                                cr_event_in_unstr += 1
                                            else:
                                                cr_in_unstr += 1
                                                d['tags'].append({'tag':"db:crossref"})
                                            found_doi = 1
                                            break
        except:
            pass
    print('Crossref overlap: ', cr_overlap)
    print('Crossref Event data in DOI: ', cr_event_in_doi)
    print('Crossref Event data in unstructured: ', cr_event_in_unstr)
    print('Crossref record data in DOI: ', cr_in_doi)
    print('Crossref record data in unstructured: ', cr_in_unstr)
    return combined_dois_json

def doisForZotero(combined_dois):
    '''
    create a list of dois for Zotero Identifier Tool
    List is broken up into batches of 1000
    '''
    l = list()
    s = set()
    c = 0
    for d in combined_dois:
        c += 1
        l.append(d['DOI'])
        s.add(d['DOI'])
        if c % 1000 == 0:
            l.append('')
            l.append('')
            l.append('')
    eosutil.saveJSON(l,'zotero_identifier_doi_list.json')  
   
eos_matched = combine_sources() # combines all wos / scopus / datacite / google / crossref eos_matched json files
combined_dois_eos_matched = combine_sources_dois(eos_matched) # create unique set of DOIs and convert to list of dictionaries
combined_dois_with_tags = addTags(combined_dois_eos_matched,eos_matched) # create unique sets of Cited-References and tags for each DOI
combined_dois_json = setsToDicts(combined_dois_with_tags) # converts sets of Cited-References and tags to lists of dicts
eos_combined_dois = noYear(combined_dois_json) # for DOIs without a year, run through crossref and habanero
eosutil.saveJSON(eos_combined_dois,'debug_eos_1_combined_dois_'+new_date+'.json')

# Find new records since the last time the update was made
g_citations_old = eosutil.loadJSON('eos_1_combined_dois_'+old_date+'.json')
g_citations_incr = eosutil.findNewCitations(g_citations_old, eos_combined_dois)
eosutil.saveJSON(g_citations_incr,'eos_1_combined_dois_'+new_date+'.incr.json')

#save all citation in a new file
eosutil.saveJSON((g_citations_old+g_citations_incr),'eos_1_combined_dois_'+new_date+'.json')

#doisForZotero(g_citations)

#eos_matched = get_publisher(combined_dois_json)
#eos_matched = get_journal_name(combined_dois_json)
#eosutil.saveJSON(eos_matched,'eos_1_combined_dois_cr_journals.json')

#combined_dois_json=eosutil.loadJSON('eos_1_combined_dois_cr.json')
#eos_matched = crossref_overlap1(combined_dois_json)
#eosutil.saveJSON(eos_matched,'eos_1_combined_dois_cr1.json')

