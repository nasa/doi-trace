from datetime import datetime
from .base import ReferenceDataSource
from ..config import config
import json
import requests
from crossref.restful import Works, Etiquette
from habanero import cn
import eosutilities as eosutil
from tqdm import tqdm
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
import requests.exceptions
import unicodedata
from bs4 import BeautifulSoup
from html import unescape
import pandas as pd
import concurrent.futures
import os


class Crossref(ReferenceDataSource):
    """Crossref data source implementation.
    
    This class handles fetching and processing citation data from Crossref API.
    """
    
    def __init__(self):
        """Initialize the Crossref data source."""
        super().__init__()
        # Create etiquette from config
        self.etiquette = Etiquette(
            config.data.get('project_name', 'DOI Trace'),
            config.data.get('version', '1.0.0'),
            config.data.get('organization', 'NASA'),
            config.data.get('email', '')
        )
        self.works = Works(etiquette=self.etiquette)
        self.prefixes = ["10.5067", "10.7927", "10.3334"]
        self.bad_source_ids = [
            'cambia-lens',
            'newsfeed',
            'reddit-links',
            'twitter',
            'wikipedia',
            'wordpressdotcom'
        ]
        # Set number of workers based on CPU count, but limit to avoid overwhelming the API
        self.max_workers = min(os.cpu_count() or 4, 8)
    
    def get_source_name(self) -> str:
        """Get the name of the data source."""
        return "Crossref"
    
    def fetch_citations(self, dois, start_date=None, end_date=None):
        """Fetch citations from Crossref Event Data API."""
        eos_dois = eosutil.getEOSCSV()  # Load EOS DOIs from CSV
        eos_dois = eosutil.getAcronyms(eos_dois)  # Process DOIs
        valid_dois = [d['EOS DOI'] for d in eos_dois]
        citations = []
        
        with tqdm(self.prefixes, desc="Fetching Crossref citations") as pbar:
            for prefix in pbar:
                pbar.set_postfix(prefix=prefix)
                cursor = ''
                while cursor is not None:
                    results = self._get_event_data(prefix, cursor)
                    if not results:
                        break
                        
                    cursor = results.get('message', {}).get('next-cursor')
                    events = results.get('message', {}).get('events', [])
                    
                    for event in events:
                        if event['source_id'] in self.bad_source_ids:
                            continue

                        eos_doi = event['obj_id'].upper()
                        eos_doi = eos_doi.rsplit('HTTPS://DOI.ORG/')[1]
                        subj_id = event['subj_id'].upper()

                        if eos_doi in valid_dois and 'HTTPS://DOI.ORG/' in subj_id:
                            citations.append({
                                'DOI': subj_id.rsplit('HTTPS://DOI.ORG/')[1].upper(),
                                'EOS DOI': eos_doi
                            })

        print(f"\nFound {len(citations)} citations. Processing...")
        
        # Combine duplicates and add metadata
        citations = self._combine_duplicates(citations)
        citations = self._extract_metadata(citations)
        return citations
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        retry=retry_if_exception_type((requests.exceptions.RequestException, requests.exceptions.HTTPError))
    )
    def _get_event_data(self, prefix: str, cursor: str = ''):
        """Fetch data from Crossref Event Data API.
        
        Args:
            prefix: DOI prefix to search for
            cursor: Pagination cursor
            
        Returns:
            API response data
        """
        try:
            url = f'https://api.eventdata.crossref.org/v1/events'
            params = {
                'mailto': self.etiquette.contact_email,
                'obj-id.prefix': prefix,
                'cursor': cursor
            }

            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching Event Data for prefix {prefix}: {e}")
            return None
    
    def _combine_duplicates(self, citations):
        """Combine entries with the same DOI and add agency information."""
        df = pd.DataFrame(eosutil.getEOSCSV())
        unique_dois = set()
        for citation in citations:
            unique_dois.add(citation['DOI'])
            
        combined = []
        with tqdm(total=len(unique_dois), desc="Combining duplicates") as pbar:
            for doi in unique_dois:
                eos_dois = set()
                for citation in citations:
                    if citation['DOI'] == doi:
                        eos_dois.add(citation['EOS DOI'])
                        
                combined.append({
                    'DOI': doi,
                    'Cited-References': [{
                        'EOS DOI': eos_doi,
                        'LP Agency': df.loc[df['EOS DOI'] == eos_doi]['LP Agency'].values[0],
                        'Shortname': df.loc[df['EOS DOI'] == eos_doi]['Shortname'].values[0]
                    } for eos_doi in eos_dois]
                })
                pbar.update(1)
        return combined
    
    def _extract_metadata_for_doi(self, citation):
        """Extract metadata for a single DOI."""
        try:
            record = self.works.doi(citation['DOI'])
            if record and record.get('subtype') != 'preprint':
                title = record.get('title', [''])[0]
                title = BeautifulSoup(unescape(title), 'lxml').text
                title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode('ascii')
                citation['Title'] = title
                
                try:
                    year = record['created'].get('date-parts')[0][0]
                except:
                    try:
                        year = record['published-print'].get('date-parts')[0][0]
                    except:
                        year = ''
                citation['Year'] = str(year)
                
                # Extract type
                citation['Type'] = record.get('type', '')
        except Exception as e:
            print(f"Error extracting metadata for {citation['DOI']}: {e}")
        return citation
    
    def _extract_metadata(self, citations):
        """Extract metadata from Crossref for each citation using parallel processing."""
        with tqdm(total=len(citations), desc="Extracting metadata") as pbar:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_citation = {
                    executor.submit(self._extract_metadata_for_doi, citation): citation 
                    for citation in citations
                }
                
                # Process results as they complete
                for future in concurrent.futures.as_completed(future_to_citation):
                    pbar.update(1)
        
        return citations
    
    def process_results(self, raw_data):
        """Process the raw data to match with EOS data."""
        # Filter out bad types
        processed_data = []
        for citation in raw_data:
            if citation.get('Type') not in eosutil.bad_type_list:
                processed_data.append(citation)
        return processed_data
    
    def save_results(self, processed_data, output_path):
        """Save the processed data to a JSON file."""
        with open(output_path, 'w') as f:
            json.dump(processed_data, f, indent=4) 