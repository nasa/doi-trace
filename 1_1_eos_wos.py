'''
   Execute WoS search at https://www.webofscience.com/wos/woscc/cited-reference-search for 'Cited DOI' prefixes 10.5067, 10.7927, 10.3334.
   Specify 'Publication Date' that covers the latest year or two.
   Inspect WoS/ directory -- move old .bib files out of the way.
   Export search results in BibTex format with 'Full Record and Cited References' into WoS/ directory (one .bib file contains <=500 citations).

   Before running script specify 
    * new_date - this is when this script is being executed (month+year)
    * old_date - the last time this script was executed (month+year) 

bibToDict()                         reads all .bib files in /WoS/. returns wos_dois with keys ['WOS', 'DOI', 'Cited-References', 'Year', 'ISBN', 'ISSN', 'Title'] 
removeDuplicates(wos_dois)          removes duplicates based on WOS. returns wos_dois
getDataFrameFromCSV()               reads _last created_ csv file in /eosdis_CSV_FILES/, renames column names. returns eos_dois
validateDOIS(wos_dois,eos_dois)     keeps only valid DOIS from csv file. returns wos_dois and wos_invalid_dois
matchWOStoEOS(wos_dois, eos_dois)   converts Cited-References list of 10.5067 DOIS into a dictionary of {'tag', 'LP Agency', 'Shortname'}
getAcronyms(wos_dois)               replaced long LP Agency names to short Acronyms
'''
import os
import re
import eosutilities as eosutil

new_date = 'jan2025'
old_date = 'sep2024'

def bibToDict(prefix):
    '''
    reads all .bib files in /WoS/. returns wos_dois with keys ['WOS', 'DOI', 'Cited-References', 'Year', 'ISBN', 'ISSN', 'Title']
    '''
    parsed_bibs = []
    WoS_files = [f for f in os.listdir('WoS') if os.path.isfile(os.path.join('WoS', f))]
    for wos_file_name in WoS_files :
        print('Processing',wos_file_name, flush=True)
        text_file =	open('WoS/'+wos_file_name, 'r', encoding='utf-8')
        data = text_file.read()
        text_file.close()
        data = data.replace('inproceedings', 'article')
        data = data.replace('incollection','article')
        data = data.replace('EISSN','XXXX')
        data = data.replace('%2D','-')
        data = data.replace('%2B','+')
        data = data.replace('%5F','_')
        data = data.replace('M0D','MOD')
        data = data.replace('(Terra)', '') # 10.5067/MODIS/MOD06_L2.006 (Terra)
        data = data.replace('0BBHQ5W22HME', 'OBBHQ5W22HME')
        data = data.replace('2XX6ZY3DUGNQ', '2XXGZY3DUGNQ')
        data = data.replace('3420HQM9AK6Q', '342OHQM9AK6Q')
        data = data.replace('3MJC62', '3MJC6')
        data = data.replace('3RQ5YS674DG', '3RQ5YS674DGQ')
        data = data.replace('6116VW8LLWJ7', '6II6VW8LLWJ7')
        data = data.replace('6J5LHH0HZHN4', '6J5LHHOHZHN4')
        data = data.replace('7MCPBJ41YOK6', '7MCPBJ41Y0K6')
        data = data.replace('7Q8HCCWS410R', '7Q8HCCWS4I0R')
        data = data.replace('8GQ8LZQVLOVL', '8GQ8LZQVL0VL')
        data = data.replace('9EBR2T0VXUFG', '9EBR2T0VXUDG')
        data = data.replace('9EBR2TOVXUDG', '9EBR2T0VXUDG')
        data = data.replace('AOPMUXXVUYNH', 'A0PMUXXVUYNH')
        data = data.replace('AD7B-0HQNSJ29', 'AD7B0HQNSJ29')
        data = data.replace('AJMZ0503TGUR', 'AJMZO5O3TGUR')
        data = data.replace('C98E2L0ZTWO', 'C98E2L0ZTWO4')
        data = data.replace('CRY0SPHERE', 'CRYOSPHERE')
        data = data.replace('CYGNSL1X20', 'CYGNS-L1X20')
        data = data.replace('D7GK8F5J8M8', 'D7GK8F5J8M8R')
        data = data.replace('D7GK8F5J8M8RR', 'D7GK8F5J8M8R')
        data = data.replace('FCCZIIFRPZ30', 'FCCZIIFRPZ3O')
        data = data.replace('FQPTQ40J22TL', 'FQPTQ4OJ22TL')
        data = data.replace('G0ZCARDS', 'GOZCARDS')
        data = data.replace('GDQOCUCVTE2Q', 'GDQ0CUCVTE2Q')
        data = data.replace('GESAD/GESAD', 'GFSAD/GFSAD')
        data = data.replace('GRSAD/GRSAD', 'GFSAD/GFSAD')
        # data = data.replace('GPM/IMERG/3B', 'GPM/IMERG/3B-')
        # data = data.replace('GPM/IMERG/3B--', 'GPM/IMERG/3B-')
        data = data.replace('NEW-TOCOKVZHF', 'NEWTOCOKVZHF')
        data = data.replace('NPZYNEEGQUO', 'NPZYNEEUGQUO')
        data = data.replace('04HAQJEWWUU8', 'O4HAQJEWWUU8')
        data = data.replace('057VAIT2AYYY', 'O57VAIT2AYYY')
        data = data.replace('0C7B04ZM9G6Q', 'OBBHQ5W22HME')
        data = data.replace('0MGEV', 'OMGEV')
        data = data.replace('OFTBVIEW', 'ORBVIEW')
        data = data.replace('0RBVIEW', 'ORBVIEW')
        data = data.replace('0SCT2-L2BV2', 'OSCT2-L2BV2')
        data = data.replace('LOU3HJDS97300', 'OU3HJDS973O0')
        data = data.replace('Q0310G10G1XULZS', 'Q0310G1XULZS')
        data = data.replace('Q5GVUVUIVG07', 'Q5GVUVUIVGO7')
        data = data.replace('SEAVVIFS', 'SEAWIFS')
        data = data.replace('SEAWIF-S', 'SEAWIFS')
        data = data.replace('SEAWIFSOC', 'SEAWIFS_OC')
        data = data.replace('SEAWIFS_0C', 'SEAWIFS_OC')
        data = data.replace('SMAP20', 'SMP20')
        data = data.replace('SYN1DEG3H0UR', 'SYN1DEG3HOUR')
        data = data.replace('TEMSC2LCR5', 'TEMSC-2LCR5')
        data = data.replace('TERRA1AQUA', 'TERRA+AQUA')
        data = data.replace('TERRATHORN+AQUA', 'TERRA+AQUA')
        data = data.replace('TRMM/TMPAOH-E/7', 'TRMM/TMPA/3H/7')
        data = data.replace('UBKO5ZUI715V', 'UBKO5ZUI7I5V')
        data = data.replace('VFMSTANDARD', 'VFM-STANDARD')
        data = data.replace('VJAPPLI1CSIV', 'VJAFPLI1CSIV')
        data = data.replace('VJAPPLI1CSIV', 'VJAFPLI1CSIV')
        data = data.replace('ZR07EXJ803XI', 'ZRO7EXJ8O3XI')
        data = data.replace('ZRO7EXJ803X1', 'ZRO7EXJ8O3XI')
        data = data.replace('L3CLOUDOCCURRENCE', 'L3_CLOUD_OCCURRENCE')
        data = data.replace('LIS-0TD', 'LIS-OTD')
        data = data.replace('MODO8', 'MOD08')
        data = data.replace('MODO9GA006', 'MODO9GA.006')
        data = data.replace('MODI3', 'MOD13')
        data = data.replace('MOD15A2.006', 'MOD15A2H.006')
        data = data.replace('MOD17A3.006', 'MOD17A3H.006')
        data = data.replace('MQD35', 'MOD35')
        data = data.replace('MODATML2.06', 'MODATML2.006')
        data = data.replace('MODIS?L3B', 'MODIS/L3B')
        data = data.replace('MYD06_GL2', 'MYD06_L2')
        data = data.replace('MYD08-M3', 'MYD08_M3')
        data = data.replace('MODO9', 'MOD09')


        data_entry = data.split('@article')
        data_entry.pop(0);
        for i, entry in enumerate(data_entry):
            wos = doi = isbn = issn = title = author = year = earlyAccessDate = None
            citedReferences = []
            #print(entry)
            #print('\n\n')
            #print('newline')
            for sentence in re.split(r'\n', entry):
                sentence = sentence.replace('{','') #strip all entries from the curly brackets
                sentence = sentence.replace('},','')
                sentence = sentence.replace('}','')
                #print(sentence,'\n') 
                #WOS
                try:
                    wos = re.search(r'Unique-ID = WOS:(\S+)', sentence).group(1) # 
                    #print(wos)
                except:
                    pass
                #Year 
                try:
                    year = re.search(r'Year = (\S+)', sentence).group(1) #Year = {{2022}},
                except:
                    pass
                #EarlyAccessDate 
                try:
                    earlyAccessDate = re.search(r'EarlyAccessDate = (.*)', sentence).group(1) #EarlyAccessDate = {{NOV 2022}},
                    earlyAccessDate = re.findall(r'\d{4}', earlyAccessDate)[0] #2022,
                except:
                    pass
                #DOI 
                try:
                    doi = re.search(r'DOI = (\S+)', sentence).group(1).upper() #DOI = {{10.1016/j.ecoleng.2021.106488}},
                    doi = doi.replace('\_','_')
                    doi = doi.upper()
                except:
                    pass
                #ISBN 
                try:
                    isbn = re.search(r'ISBN = (\S+)', sentence).group(1) #ISBN
                    isbn = re.sub(r'{','',isbn)
                    isbn = re.sub(r'}','',isbn)
                except:
                    pass
                #ISSN 
                try:
                    issn = re.search(r'ISSN = (\S+)', sentence).group(1) #ISSN
                    issn = re.sub(r'{','',issn)
                    issn = re.sub(r'}','',issn)
                except:
                    pass

                #Title 
                try:
                    title = re.search(r'Title = (.*)', sentence).group(1) # Title = {{ ... or line splits
                    title = re.sub(r'\\','',title)
                    if title[-1] == ',':
                        title = title[:-1]
                except:
                    pass
                #Author 
                try:
                    tempauthor = re.search(r'Author = (.*)', sentence).group(1) # Author = { ... }
                    author = tempauthor.split(' and',1)[0]
                except:
                    pass
                #Cited References
                for sub in prefix:
                    sub_prefix = sub.split('10.',1)[1]
                    try:
                        citedReference = re.search(r'(10\.'+str(sub_prefix)+'.*)(,|])*', sentence)	 # Cited-References = {{

                        if citedReference:
                            #print('if citedReference:')
                            citedReference = citedReference.group(0).split(',')				 # get ALL doi references in the line
                            # print('start:')
                            for i,c in enumerate(citedReference):
                                #c = re.sub(r'(\s+|\\|}|\)|]|DOI)', '', c)						 # remove 'DOI', spaces, \, ), 'and' or } from the DOI
                                c = re.sub(r'(\s+|DOI|\\|}|\)|]|)', '', c)						 # remove 'DOI', spaces, \, ), 'and' or } from the DOI
                                #c = re.sub('\/$', '', c)	
                                c = re.sub('\.$', '', c)	
                                citedReference[i] = c
                            #	 print(i,c)
                            # print('end.')
                            for c in citedReference:
                                if c.upper() not in citedReferences:
                                    citedReferences.append(c.upper())

                    except:
                        pass
            if year is None or year == '':
                        year = earlyAccessDate
            parsed_bibs.append({'WOS': wos,
                                'Year': year,
                                'Author': author,
                                'DOI': doi,
                                'ISBN': isbn,
                                'ISSN': issn,
                                'Title': title,
                                'Cited-References': citedReferences})

            #break
    return parsed_bibs

def removeDuplicates(wos_dois):
    '''
    removes duplicates based on WOS
    '''
    list_of_unique_wos = set()
    wos = list()
    for e in wos_dois:
        if e['WOS'] not in list_of_unique_wos:
            list_of_unique_wos.add(e['WOS'])
            wos.append(e)
    print('removeDuplicates(wos_dois):',len(list_of_unique_wos),'unique WOS')
    return wos



def validateDOIS(wos_dois,eos_dois):
    '''
    keeps only valid DOIS from csv file
    returns wos_dois and missing/invalid doi list
    '''
    valid_gesdisc = [d['EOS DOI'] for d in eos_dois]
    wos_with_valid_eos_refs = list()
    wos_without_valid_eos_refs = list()
    for w_row in wos_dois:
        eos_valid_refs = list()
        eos_invalid_refs = list()
        for ref in w_row['Cited-References']:
            if ref in valid_gesdisc:
                eos_valid_refs.append(ref)
            elif ref != '':
                eos_invalid_refs.append(ref)
        w_row['Cited-References'] = eos_valid_refs
        if w_row['Cited-References']: # if cited-references exists (not empty list)
            wos_with_valid_eos_refs.append(w_row)
        if not w_row['Cited-References']: # if Cited-References is empty, then pass to wos_invalid_dois the WOS and invalid DOIs
            #print(w_row['WOS'],'\t','\t', localInvalidList)
            for invalid_ref in eos_invalid_refs:
                wos_without_valid_eos_refs.append([w_row['WOS'], w_row['DOI'], invalid_ref])
    return wos_with_valid_eos_refs, wos_without_valid_eos_refs

def matchWOStoEOS(wos_dois, eos_dois):
    '''
    converts Cited-References list of EOS DOIS into a dictionary of {'tag', 'LP Agency', 'Shortname'}
    returns wos_dois
    '''
    print('init\t\tmatchWOStoEOS(wos_dois, eos_dois)', flush=True)
    for e_row in eos_dois:
        for w_row in wos_dois:
            for i,ref in enumerate(w_row['Cited-References']):
                if e_row['EOS DOI'] == ref:
                    w_row['Cited-References'][i] = {'EOS DOI': e_row['EOS DOI'], 'LP Agency': e_row['LP Agency'], 'Shortname': e_row['Shortname']}
    print('complete\tmatchWOStoEOS(wos_dois, eos_dois)', flush=True)
    return wos_dois

def statusReport(wos_dois, wos_invalid_dois):
    '''
    prints stats on the bib parsing
    '''
    #status report
    print('\n') 
    unique_invalid = set()
    for w in wos_invalid_dois:
        unique_invalid.add(w[0])
    tags = 0
    journals = 0
    no_eos_doi_list = []
    for w in wos_dois:
        if w['Cited-References']:
            journals += 1
            tags += len(w['Cited-References'])
#         elif w['WOS'] not in [item for sublist in wos_invalid_dois for item in sublist]:        # note to self: one liners are bad practice without adding comments in real-time
#             no_eos_doi_list.append([w['WOS']])

    print(len(wos_dois),'total entries')
    print(journals,'journals with',tags,'EOS DOIs\n')
    print(len(unique_invalid),'journals had',len(wos_invalid_dois),'invalid EOS prefix citedReference.group(0).split(",") lines\n')
    #print(len(no_eos_doi_list),'journals with no EOS citation tags')
    #eosutil.saveJSON(no_eos_doi_list, 'debug_wos_no_eos_doi1.json')

eos_dois = eosutil.getEOSCSV()                                                 # returns list of dicts with keys = ['DOI_NAME', 'LP_AGENCY', 'SPECIAL']
eos_dois = eosutil.getAcronyms(eos_dois)                                       # replaced long LP Agency names to short Acronyms
wos_bibs = bibToDict(['10.5067','10.3334','10.7927'])                          # returns a dictionary with keys ['WOS', 'DOI', 'Cited-References', 'Year', 'ISBN', 'ISSN', 'Title']
wos_bibs_no_duplicates = removeDuplicates(wos_bibs)                            # removes duplicates based on WOS
wos_with_valid_eos_refs, wos_without_valid_eos_refs = validateDOIS(wos_bibs_no_duplicates,eos_dois)    # keeps only valid DOIS from csv file
wos_dois = eosutil.noDOISoSearchCrossref(wos_with_valid_eos_refs,'WOS',0.95)                      # if no DOI, search Crossref, match based on author, year & title
eos_wos_matched = matchWOStoEOS(wos_dois, eos_dois)                            # converts Cited-References list of 10.5067 DOIS into a dictionary of {'tag', 'LP Agency', 'Shortname'}
statusReport(eos_wos_matched, wos_without_valid_eos_refs)                                # prints stats on the bib parsing
eosutil.saveJSON(wos_without_valid_eos_refs, 'debug_wos_without_valid_eos_refs.json')
eosutil.saveJSON(eos_wos_matched, 'eos_wos_matched_'+new_date+'.json')

# Find new records since the last time the update was made
g_citations_new = eosutil.loadJSON('eos_wos_matched_'+new_date+'.json')
g_citations_old = eosutil.loadJSON('eos_wos_matched_'+old_date+'.json')
g_citations = eosutil.findNewCitations(g_citations_old, g_citations_new)
g_citations = eosutil.addCrossrefType(g_citations)

# save increment of citations
eosutil.saveJSON(g_citations,'eos_wos_matched_'+new_date+'.incr.json')

# write all citations into data/eos_wos_matched_'+new_date+'.json
all_citations = g_citations_old + g_citations
eosutil.saveJSON(all_citations,'eos_wos_matched_'+new_date+'.json')

