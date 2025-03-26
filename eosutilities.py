import glob
import csv
import json
import os
import pandas as pd
import re
import unicodedata # used to transform unicode to ascii such as '\u2026' to '...'
from bs4 import BeautifulSoup # used together with unescape to remove html tags such as &lt;
from html import unescape # used together with unescape to remove html tags such as &lt;
from jellyfish import jaro_winkler_similarity # used to find google & crossref title similarities
from crossref.restful import Works, Etiquette

data_path = 'data'

#crossref
with open(os.path.join(data_path+'/crossref_etiquette.json'), 'r') as fp: # read wos_eos_matched to json
    my_etiquette = json.load(fp)
#my_etiquette = loadJSON('crossref_etiquette.json')
#project_name = 'EOS DOI References Collection'
#version = 'v3 May 2022'
#organization = 'NASA GESDISC'
#email = 'irina.gerasimov@nasa.gov'
#my_etiquette = Etiquette(project_name, version, organization, email)

bad_type_list = [ # list of publication types to ignore
        'peer-review', 
        'posted-content',
        'component',
        'dataset',
        'grant'
    ]
#data_path = 'data'

def saveJSON(list_of_dicts,filename):
    '''
    saves list of dicts as a json file in configured data_path folder (should be /data/)
    '''
    with open(os.path.join(data_path+'/'+filename), "w") as fp:
        json.dump(list_of_dicts, fp, indent=4)
    print(filename,'saved into /'+data_path+'/ folder')

def loadJSON(filename):
    '''
    reads json file in data_path folder (should be /data/)
    '''
    with open(os.path.join(data_path+'/'+filename), 'r') as fp: # read wos_eos_matched to json
        json_file = json.load(fp)
    return json_file
    
def saveCSV(list_of_dicts,filename):
    '''
    saves list as CSV file in configured data_path folder (should be /data/)
    '''
    with open(os.path.join(data_path+'/'+filename), 'w', newline='\n', encoding='utf-8') as fp:
        write = csv.writer(fp)
        write.writerows(list_of_dicts)
        print(filename,'saved into /'+data_path+'/ folder')

# def getCSV():
    # '''
    # Create pandas DataFrame from the LAST CREATED csv file placed in the '/eosdis_CSV_FILES/' folder.
    # renames DOI_NAME to EOS DOI, SPECIAL TO Special
    # returns a pd DataFrame with Columns ['EOS DOI', 'Agency', 'Shortname']
    # '''
    # column_names = ['DOI_NAME', 'LP_AGENCY', 'SPECIAL']
    
    # files = glob.glob('eosdis_CSV_FILES/*.csv')
    # latest_file = str(max(files , key=os.path.getctime))
    # df = pd.read_csv(latest_file) # note to self: change to variable filename
    # df = df[column_names]
    # df = df.rename(columns={'DOI_NAME': 'EOS DOI',
                            # 'LP_AGENCY': 'LP Agency',
                            # 'SPECIAL': 'Shortname'})
    # print('Retreived file: ',latest_file)
    # return df.to_dict('records')

def getEOSCSV():
    '''
    Create pandas DataFrame from the LAST CREATED csv file placed in the '/eosdis_CSV_FILES/' folder.
    renames DOI_NAME to EOS DOI, SPECIAL TO Special
    returns a pd DataFrame with Columns ['EOS DOI', 'Agency', 'Shortname']
    '''
    column_names = ['DOI_NAME', 'LP_AGENCY', 'SPECIAL']
    
    files = glob.glob('eosdis_csv_files/*.csv')
    df_all = pd.DataFrame()
    for file in files:
        print("reading: "+file)
        df = pd.read_csv(file, encoding='unicode_escape') # note to self: change to variable filename
        try: # for EOS DOIS
            column_names = ['DOI_NAME', 'LP_AGENCY', 'SPECIAL']
            df = df[column_names]
            df = df.rename(columns={'DOI_NAME': 'EOS DOI',
                                    'LP_AGENCY': 'LP Agency',
                                    'SPECIAL': 'Shortname'})
        except KeyError:
            pass
        try: #for ORNL & SEDAC
            column_names = ['DOI_NAME', 'PROVIDER', 'DOI_SPECIAL']
            df = df[column_names]
            df = df.rename(columns={'DOI_NAME': 'EOS DOI',
                                    'PROVIDER': 'LP Agency',
                                    'DOI_SPECIAL': 'Shortname'})
        except KeyError:
                pass
        print('Loading', file)
        df_all = pd.concat([df_all, df])
    print('Total',df_all.shape[0],'EOS DOIS')
    df_all['EOS DOI'] = df_all['EOS DOI'].str.upper()
    return df_all.to_dict('records')

def getAcronyms(eos_dict):
    '''
    replaced long LP Agency names to short Acronyms
    '''
    for row in eos_dict:
        row['LP Agency'] = row['LP Agency'].replace('Alaska Satellite Facility DAAC','ASF DAAC')
        row['LP Agency'] = row['LP Agency'].replace('Crustal Dynamics Data Information System','CDDIS')
        row['LP Agency'] = row['LP Agency'].replace('Earth Science Data and Information System Standards Office','ESDIS Standards Office')
        row['LP Agency'] = row['LP Agency'].replace('Earth Science Project Office, Ames Research Center','EPSO ARC')
        row['LP Agency'] = row['LP Agency'].replace('Goddard Earth Sciences Data and Information Services Center','GES DISC')
        row['LP Agency'] = row['LP Agency'].replace('Global Hydrometeorology Resource Center DAAC','GHRC DAAC')
        row['LP Agency'] = row['LP Agency'].replace('LANCE AMSR2 at the GHRC DAAC','GHRC DAAC')
        row['LP Agency'] = row['LP Agency'].replace('LANCE MODIS at the MODAPS','LANCE MODIS')
        row['LP Agency'] = row['LP Agency'].replace('Land Atmosphere Near real-time Capability for EOS Fire Information for Resource Management System','LANCE for EOS')
        row['LP Agency'] = row['LP Agency'].replace('Land Processes DAAC','LP DAAC')
        row['LP Agency'] = row['LP Agency'].replace('Langley Atmospheric Science Data Center DAAC','ASDC DAAC')
        row['LP Agency'] = row['LP Agency'].replace('Level 1 and Atmosphere Archive and Distribution System','LAADS')
        row['LP Agency'] = row['LP Agency'].replace('NASA Center for Climate Simulation','NCCS')
        row['LP Agency'] = row['LP Agency'].replace('NASA Terrestrial Systems Laboratory','LPVS')
        row['LP Agency'] = row['LP Agency'].replace('National Snow and Ice Data Center DAAC','NSIDC DAAC')
        row['LP Agency'] = row['LP Agency'].replace('Ocean Biology DAAC','OB.DAAC')
        row['LP Agency'] = row['LP Agency'].replace('Oak Ridge National Laboratory DAAC','ORNL DAAC')
        row['LP Agency'] = row['LP Agency'].replace('Oceans Melting Greenland Mission','OMG')
        #ref['LP Agency'] = row['LP Agency'].replace('Ozone PEATE','')
        row['LP Agency'] = row['LP Agency'].replace('Physical Oceanography DAAC','PO.DAAC')
        row['LP Agency'] = row['LP Agency'].replace('Precipitation Processing System','PPS')
        row['LP Agency'] = row['LP Agency'].replace('Socioeconomic Data and Applications Center','SEDAC')
        row['LP Agency'] = row['LP Agency'].replace('VIIRS Atmosphere SIPS','VIIRS ATM SIPS')
    return eos_dict

def crossrefREST(author, year, title,jaro_desired = 0.95,jaro_min = 0.9):
    '''
    
    '''
    #print('init\t\tcrossrefREST(author,year,title)', flush=True)
    #my_etiquette = loadJSON('crossref_etiquette.json')
    works = Works(etiquette=Etiquette(my_etiquette['project_name'], my_etiquette['version'], my_etiquette['organization'], my_etiquette['email']))
    #works = Works(etiquette=my_etiquette)

    #jaro_desired = 0.95 # desired jaro_wrinkler_score
    #jaro_min = 0.9 # break loop if score less thanjaro_min
    
    bad_type_list = [ # list of publication types to ignore
        'peer-review', 
        'posted-content',
        'component',
        'dataset'
    ]
    year = '('+str(year)+')'
    year = year.replace('((','(')
    year = year.replace('))',')')
    title = BeautifulSoup(unescape(title), 'lxml').text #sanitize title from html tags
    title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode('ascii') # sanitize title from unicode
    title = title.replace('...','')
    query = str(author)+' + '+str(year)+' + '+str(title) # create query for works.Works
    query = query.replace('+  +','+') # when year is empty, remove extra + sign
    query = query.replace('+  +','+') # when author is empty, remove extra + sign
    w = works.query(bibliographic=query).select('DOI, title','published-print','issue','type') # keys to retrieve
    CR_works = list()
    works_iter = 0.
    cr_return = None
    for j,item in enumerate(w): # iterate over the queried list, break after 5 results pulled
        item_type = item.get('type',None)
        if j > 5:
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
            except:
                pass
            if not cr_year:
                try:
                    item['issue']['date-parts'][0][0]
                except:
                    pass
            if not cr_year:
                cr_year = re.sub(r'\W+', '', year)
            #print(i,j,jaro_winkler_s)
            score = 0
            if jaro_winkler_s > jaro_desired: # if the jaro score is above 0.9, add it to the list of cited-references
                score = 1 if item_type == 'journal-article' else 0 # priority for journal-articles
            #print(jaro_winkler_s,score,cr_doi,cr_title)
            CR_works.append(
                {
                    
                    'score' : [jaro_winkler_s,score],
                    'cr doi': cr_doi,
                    'cr title': cr_title,
                    'cr year': cr_year,
                    'type' : item_type,
                    'original title': title,
                    'original year' : re.sub(r'\W+', '', year)
                }
            )
            if score == 1: #if score = 1 (journal-article)
                cr_return = [CR_works.pop()]
                break
            if jaro_winkler_s < jaro_min: #if score below minimum
                break
            if len(CR_works) > 3: # break after 3 valid dois added
                break
    if cr_return:
        pass
    else:
        cr_return = CR_works.copy()
    #print('complete\tcrossrefREST(author,year,title)', flush=True)
    return cr_return
    
def noDOISoSearchCrossref(source,key,jaro_score):
    '''
    for source entries with no DOI , run through CrossrefREST and fill DOI
    jaro_score is the treshhold of title similarity
    '''
    source_set = set()
    source_dupes = list()
    print('init\t\tnoDOISoSearchCrossref(source,key,jaro_score)', flush=True)
    for i,s in enumerate(source):
        if s['DOI'] and s['DOI'] not in source_set:
            source_set.add(s['DOI'])
        else:
            source_dupes.append([i,s[key],s['DOI'],s['ISBN'],s['ISSN']])
    print('Searching Crossref for',len(source_dupes),key,'with no DOI')

    for h,dup in enumerate(source_dupes):
        i = dup[0]
        x = crossrefREST(source[i].get('Author'), source[i].get('Year'), source[i].get('Title'),0.9,0.9)
        #print(h,'/',len(source_dupes))
        for j,e in enumerate(x):
            if e['score'][0] > jaro_score:
                #print(source[i]['Title'],'\n',e['cr title'])
                source[i]['DOI'] = e['cr doi'].upper()
    print('complete\t\tnoDOISoSearchCrossref(source,key,jaro_score)', flush=True)
    return source

def getDOIfromURL(link):
    pub_doi = ""
    resp = re.search(r'\/(10\.\d+.*)$', link)
    if resp:
      pub_doi = resp[0]
      pub_doi = re.sub(r'(\/full|\/meta|\.pdf|\.abstract|\.short|\&.*|\/download|\/html|\?.*|\#.*|\;|\)|\/$|\.$)','',pub_doi)
    elif re.search(r'copernicus\.org', link):
      resp = re.search(r'\//(\S+)\.copernicus\.org\/articles\/(\d+)\/(\d+)\/(\d+)', link)
      if resp:
        pub_doi = '10.5194/'+resp[1]+'-'+resp[2]+'-'+resp[3]+'-'+resp[4]
    elif re.search(r'nature\.com\/articles\/', link):
      resp = re.search(r'nature\.com\/articles\/(\S+)', link)
      if resp:
        pub_doi = '10.1038/'+resp[1]
        pub_doi = re.sub(r'(\?.*|\/briefing.*)', '', pub_doi)
        pub_doi = re.sub(r'%E2%80%', '-', pub_doi)
        resp = re.match(r'10.1038\/sdata(\d{4})(\d+)', pub_doi)
        if resp:
          pub_doi = '10.1038/sdata.'+resp[1]+'.'+resp[2]
        # https://www.nature.com/articles/s41558%E2%80%92019%E2%80%920592%E2%80%928 should translate to 10.1038/s41558-019-0592-8
        # https://www.nature.com/articles/s41586%E2%80%93020%E2%80%932780%E2%80%930 should translate to 10.1038/s41586-020-2780-0
    elif re.search(r'journals\.ametsoc\.org', link):
      resp=re.search(r'\/((\w+|\.+|\-+|_+)*)\.xml', link)
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
      if re.search(r'elementa', pub_doi):
        pub_doi = re.sub(r'\/\d+$', '', pub_doi)
      elif re.search(r'10.1201\/(\S+)\/', pub_doi):
        resp=re.match(r'10.1201\/(\S+)\/', pub_doi)
        pub_doi = '10.1201/'+resp[1]
    return pub_doi

def getZoteroItemsByDOI(g):
    if not g['DOI']:
        return g
    stream = os.popen('curl -d \"'+g['DOI']+'\" -H \'Content-Type: text/plain\' http://127.0.0.1:1969/search')
    output = stream.read()
    print(output)
    if re.match('No items returned from any translator', output):
        return g
    try:
        json_object = json.loads(output)
        g['zotero'] = json_object[0]
        if g['zotero'].get('DOI', ''):
            g['DOI'] = g['zotero']['DOI']
        elif g['zotero'].get('extra', '') and re.search('DOI', g['zotero']['extra']):
            resp = re.search(r'(10\.\d+.*)$', g['zotero']['extra'])
            if resp:
                g['DOI'] = resp[0]
        if g['zotero'].get('date' ,''):
            g['Year'] = re.search(r'\d{4}', g['zotero']['date'])[0]
    except:
        pass
    return g

def addCrossrefType(g_citations):
    #my_etiquette = eosutil.loadJSON('crossref_etiquette.json')
    works = Works(etiquette=Etiquette(my_etiquette['project_name'], my_etiquette['version'], my_etiquette['organization'], my_etiquette['email']))
    #works = Works(etiquette=my_etiquette)
    for i,g in enumerate(g_citations):
        if g.get('Type', ''):
            continue
        g['Type'] = ""
        if g['DOI']:
            print(g['DOI'])
            try:
                g['Type'] = works.doi(g['DOI'])['type']
                print(g['Type'])
            except:
                continue
    return g_citations

def excludeBadTypes(g_citations):
    g_cleaned = list()
    for i,g in enumerate(g_citations):
        if g.get('DOI') and re.search('PANGAEA|ZENODO|DRYAD|ESSOAR', g['DOI']): # those are dataset and ESSOAR is for preprints egistries
            continue
        if not g.get('Type', ''):
            g_cleaned.append(g)
            continue
        if g['Type'] not in bad_type_list:
            g_cleaned.append(g)

    return g_cleaned

def getCrossRefYear(g_citations):
    #my_etiquette = eosutil.loadJSON('crossref_etiquette.json')
    works = Works(etiquette=Etiquette(my_etiquette['project_name'], my_etiquette['version'], my_etiquette['organization'], my_etiquette['email']))
    #works = Works(etiquette=my_etiquette)
    for i,g in enumerate(g_citations):
        if g.get('Year', '') and len(str(g['Year'])):
            continue
        try:
            g['Year'] = str(works.doi(g['DOI'])['created']['date-parts'][0][0])
            print(g['Year'])
        except:
            continue
    return g_citations

def getCrossRefYearAndType(g_citations):
    #my_etiquette = eosutil.loadJSON('crossref_etiquette.json')
    works = Works(etiquette=Etiquette(my_etiquette['project_name'], my_etiquette['version'], my_etiquette['organization'], my_etiquette['email']))
    #works = Works(etiquette=my_etiquette)
    for i,g in enumerate(g_citations):
        if g.get('Type', '') and g.get('Year', '') and len(str(g['Year'])):
            continue
        try:
            g['Type'] = works.doi(g['DOI'])['type']
            print(g['Type'])
            g['Year'] = str(works.doi(g['DOI'])['created']['date-parts'][0][0])
            print(g['Year'])
        except:
            continue
    return g_citations


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

def addCrossrefTypeTitleYear(g_citations):
    #works = Works(etiquette=my_etiquette)
    works = Works(etiquette=Etiquette(my_etiquette['project_name'], my_etiquette['version'], my_etiquette['organization'], my_etiquette['email']))
    for i,g in enumerate(g_citations):
        if g.get('Year', '') and len(g['Year']) and g.get('Type', '') and g.get('Title', ''):
            continue
        g['Type'] = ""
        try:
            record = works.doi(g['DOI'])
            record.get('subtype')
            g['Year'] = str(works.doi(g['DOI'])['created']['date-parts'][0][0])
            print(g['Year'])
        except:
            pass

    return g_citations
