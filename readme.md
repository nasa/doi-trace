Creating and updating collection of EOSDIS dataset citing publication citations (Updated: 3-26-2025)
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

5) Combine all dois into one file
	* 2_combine_doi_sources.py

