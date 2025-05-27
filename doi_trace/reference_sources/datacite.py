from datetime import datetime, timedelta
from .base import ReferenceDataSource
from ..config import config
import json
import requests
from crossref.restful import Works, Etiquette
from habanero import cn
import eosutilities as eosutil
from tqdm import tqdm
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type, retry_if_exception
import requests.exceptions
import unicodedata
from bs4 import BeautifulSoup
from html import unescape
import concurrent.futures
import os
import pandas as pd
import time
from threading import Lock


class RateLimitError(Exception):
    """Exception raised when we hit a rate limit."""
    pass


class DataCite(ReferenceDataSource):
    """DataCite data source implementation.
    
    This class handles fetching and processing citation data from DataCite API.
    """
    
    def __init__(self):
        """Initialize the DataCite data source."""
        super().__init__()
        # Create etiquette from config for Crossref API
        self.etiquette = Etiquette(
            config.data.get('project_name', 'DOI Trace'),
            config.data.get('version', '1.0.0'),
            config.data.get('organization', 'NASA'),
            config.data.get('email', '')
        )
        self.works = Works(etiquette=self.etiquette)
        # Set number of workers based on CPU count, but limit to avoid overwhelming the API
        self.max_workers = min(os.cpu_count() or 4, 8)
        
        # Rate limiting setup, these numbers come from DataCite: https://support.datacite.org/docs/best-practices-for-integrators#:~:text=Our%20firewall%20imposes%20a%20rate,for%20all%20of%20our%20APIs.
        self.rate_limit = 3000  # requests per window
        self.rate_window = 300  # 5 minutes in seconds
        self.tokens = self.rate_limit
        self.last_refill = time.time()
        self.token_lock = Lock()
    
    def _refill_tokens(self):
        """Refill tokens based on time elapsed."""
        now = time.time()
        with self.token_lock:
            time_passed = now - self.last_refill
            new_tokens = int(time_passed * (self.rate_limit / self.rate_window))
            if new_tokens > 0:
                self.tokens = min(self.rate_limit, self.tokens + new_tokens)
                self.last_refill = now
    
    def _consume_token(self):
        """Consume a token, waiting if necessary."""
        while True:
            self._refill_tokens()
            with self.token_lock:
                if self.tokens > 0:
                    self.tokens -= 1
                    return
            time.sleep(0.1)  # Wait a bit before checking again
    
    def get_source_name(self) -> str:
        """Get the name of the data source."""
        return "DataCite"
    
    def fetch_citations(self, dois, start_date=None, end_date=None):
        """Fetch citations from DataCite API."""
        eos_dois = eosutil.getEOSCSV()  # Load EOS DOIs from CSV
        eos_dois = eosutil.getAcronyms(eos_dois)  # Process DOIs
        citations = []
        
        # Fetch citations in parallel
        with tqdm(total=len(eos_dois), desc="Fetching DataCite citations") as pbar:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_doi = {
                    executor.submit(self._get_datacite, doi['EOS DOI']): doi['EOS DOI']
                    for doi in eos_dois
                }
                
                # Process results as they complete
                for future in concurrent.futures.as_completed(future_to_doi):
                    doi = future_to_doi[future]
                    try:
                        results = future.result()
                        if results:
                            citations.extend(results)
                    except Exception as e:
                        print(f"Error processing results for {doi}: {e}")
                    pbar.update(1)
        
        print(f"\nFound {len(citations)} citations. Processing...")
        
        # Extract metadata and combine duplicates
        citations = self._extract_metadata(citations)
        citations = self._combine_duplicates(citations)
        return citations
    
    def _is_rate_limit_error(self, response):
        """Check if the response indicates a rate limit error."""
        try:
            data = response.json()
            return (response.status_code == 403 and 
                   data.get('errors', [{}])[0].get('title') == 'Your request has been rate limited.')
        except:
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        retry=retry_if_exception(lambda e: isinstance(e, RateLimitError))
    )
    def _get_datacite(self, doi: str):
        """Fetch citations from DataCite API for a given DOI.
        
        Args:
            doi: DOI to search for
            
        Returns:
            List of citations or None if error
        """
        try:
            self._consume_token()  # Wait for a token before making the request
            url = f'https://api.datacite.org/dois/{doi}'
            response = requests.get(url)
            
            if self._is_rate_limit_error(response):
                print("\nRate limit hit! Waiting 5 minutes before retrying...")
                time.sleep(300)  # Wait 5 minutes
                raise RateLimitError("Rate limit exceeded")
            
            response.raise_for_status()
            data = response.json()
            
            citations = []
            entries = data['data']['relationships']['citations']['data']
            
            for entry in entries:
                citations.append({
                    'DOI': entry['id'].upper(),
                    'EOS DOI': doi
                })
            
            return citations
        except RateLimitError:
            raise
        except Exception as e:
            print(f"Error fetching DataCite data for {doi}: {e}")
            return None
    
    def _extract_metadata(self, citations):
        """Extract metadata from Crossref for each citation."""
        # First deduplicate DOIs to avoid unnecessary API calls
        unique_dois = set()
        doi_to_citations = {}
        for citation in citations:
            doi = citation['DOI']
            unique_dois.add(doi)
            if doi not in doi_to_citations:
                doi_to_citations[doi] = []
            doi_to_citations[doi].append(citation)
        
        # Fetch metadata for unique DOIs in parallel
        metadata_cache = {}
        with tqdm(total=len(unique_dois), desc="Extracting metadata") as pbar:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_doi = {
                    executor.submit(self._get_metadata_for_doi, doi): doi
                    for doi in unique_dois
                }
                
                # Process results as they complete
                for future in concurrent.futures.as_completed(future_to_doi):
                    doi = future_to_doi[future]
                    try:
                        metadata = future.result()
                        if metadata:
                            metadata_cache[doi] = metadata
                    except Exception as e:
                        print(f"Error processing metadata for {doi}: {e}")
                    pbar.update(1)
        
        # Apply metadata to all citations
        for doi, metadata in metadata_cache.items():
            for citation in doi_to_citations[doi]:
                citation.update(metadata)
        
        return citations
    
    def _get_metadata_for_doi(self, doi: str):
        """Get metadata for a single DOI."""
        try:
            record = self.works.doi(doi)
            if record and record.get('subtype') != 'preprint':
                title = record.get('title', [''])[0]
                title = BeautifulSoup(unescape(title), 'lxml').text
                title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode('ascii')
                
                try:
                    year = record['created'].get('date-parts')[0][0]
                except:
                    try:
                        year = record['published-print'].get('date-parts')[0][0]
                    except:
                        year = ''
                
                return {
                    'Title': title,
                    'Year': str(year),
                    'Type': record.get('type', '')
                }
        except Exception as e:
            print(f"Error extracting metadata for {doi}: {e}")
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