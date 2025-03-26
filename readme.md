HQ quarterly meeting in first Thursday of the month in Feb, May, August and Nov.
Creating and updating EOS dataset DOI citation library (Updated: 9-10-2024)
-------------

JSON files are placed in data/ directory
EOSDIS CSV files are in eosdis_csv_files/ directory
WoS .bib files are in WoS/ directory
eosutilities.py - our own library with the most common functions 

Follow steps sequentially:

1) Obtain latest dataset DOIs from EOSDIS DOI server https://doiserver.eosdis.nasa.gov/ords/f?p=100:8:::NO:::  and place the csv file into eosdis_csv_files/ directory.
   For all 10.5067 : Provider -> Data, Status=Registered, Query
   For ORNL and SEDAC Home->Monthly Report->'ORNL DAAC' or 'SEDAC'. ORNL and SEDAC csv files can be combined. The csv with 10.5067 DOI has more extended format. 
   Keep two latest .csv files in eosdis_csv_files/ directory.

2) Execute WoS search at https://www.webofscience.com/wos/woscc/cited-reference-search for 'Cited DOI' prefixes 10.5067, 10.7927, 10.3334.
   Specify 'Publication Date' that covers the latest year or two.
   Inspect WoS/ directory -- move old .bib files out of the way.
   Export search results in BibTex format with 'Full Record and Cited References' into WoS/ directory (one .bib file contains <=500 citations).
        * 1_1_eos_wos.py

3) Run updates for Scopus, Crossref and Datacite for the full date range. Scopus has limits on API requests, may need to create a new key. 
	* 1_2_eos_scopus.py				
	* 1_3_eos_crossref.py
	* 1_4_eos_datacite.py

4) Run GS DOI searches by the specified earliest year (need SerpAPI key). It outputs GS URLs and linked dataset DOIs. The program needs serp_api_key.json which contains serp_api_key.
        * 1_5_1_gs_serpapi.py
        * 1_5_2_gs_get_increment.py
        * 1_5_3_gs_process_urls.py
	* 1_5_4_eos_google.py

5) Combine all dois to one file with proper Zotero tags
	* 2_combine_doi_sources.py

6) Create list of DOIs that were added since last update. In Zotero add these DOIs to 'znew' folder
	* grep '"DOI"' eos_1_combined_dois_<date>.incr.json|awk -F'"' '{print $4}' > dois.txt

7) Pull Zotero items from znew folder and then push the tags contained in eos_1_combined_dois.json
	* 3_zotero_pull_push.py				


To update GES DISC library

1) Make sure that ShortNames do not have versions in them and have new GES DISC citations placed in a separate file:
	* get_gesdisc_citations.py

2) Copy citations with tag 'GES DISC' to Scopus+WoS+GS+COCI folder and get its content by running:
	* get_zot_pubs_and_notes.py

3) Run Scopus+WoS+GS+COCI update, set byDOI = True:
	* 3_add_eos_to_gesdisc.py 


To create/update GES DISC library of citations collected by ShortName search.

1) Place new DIFs into /home/igerasim/allenai/PROD_DATE/. Put MERRA additional MERRA terms into merra1.txt. Create search terms:
	* create_gscholar_search_terms.py

2) Get GS URLs by ShortName and keywords search by the specified earliest year (need SerpAPI key).
	* gscholar_pull_by_short_name.py

3) Get the difference between new and old URLs
	* gscholar_get_increment.py

4) Start Zotero server and process Google Scholar URLs collected by SerpAPI (output of gscholar_get_increment.py)
	* 1_5_1_serpapi.py
	* 1_5_3_eos_google.py 

5) Get list of DOIs and add them to Zotero to Gscholar.temp folder and get its content:
	* get_zot_pubs_and_notes.py

6) Run Gscholar.temp update, set byDOI = False:
	* 3_add_eos_to_gesdisc.py


