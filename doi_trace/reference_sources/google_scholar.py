from datetime import datetime
from .base import ReferenceDataSource
from ..config import config
import json
import requests
from serpapi import GoogleSearch
import eosutilities as eosutil
from tqdm import tqdm
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
import requests.exceptions
import unicodedata
from bs4 import BeautifulSoup
from html import unescape
import concurrent.futures
import os
import pandas as pd
import re
import jellyfish
from crossref.restful import Works, Etiquette
import time
from urllib.parse import parse_qsl, urlsplit


class GoogleScholar(ReferenceDataSource):
    """Google Scholar data source implementation.
    
    This class handles fetching and processing citation data from Google Scholar via SerpAPI.
    """
    
    def __init__(self):
        """Initialize the Google Scholar data source."""
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

        # Load SerpAPI key from config
        self.api_key = config.data.get('api', {}).get('serp_api_key')
        if not self.api_key:
            raise ValueError("SerpAPI key not found in config.toml")
        
        # Configuration
        self.exclude_preprints = True
        self.exclude_pdf = True
        self.bad_type_list = [
            'peer-review',
            'posted-content',
            'component',
            'dataset'
        ]
    
    def get_source_name(self) -> str:
        """Get the name of the data source."""
        return "Google Scholar"
    
    def fetch_citations(self, dois, start_date=None, end_date=None):
        """Fetch citations from Google Scholar via SerpAPI."""
        eos_dois = eosutil.getEOSCSV()  # Load EOS DOIs from CSV
        eos_dois = eosutil.getAcronyms(eos_dois)  # Process DOIs
        citations = []
        
        # Load previously searched DOIs if they exist
        searched_dois_file = 'data/searched_dois.json'
        searched_dois = []
        if os.path.exists(searched_dois_file):
            with open(searched_dois_file) as f:
                searched_dois = json.load(f)
            print(f"Already searched {len(searched_dois)} DOIs")
        
        # Process DOIs sequentially with rate limiting
        with tqdm(total=len(eos_dois), desc="Fetching Google Scholar citations") as pbar:
            for i, doi in enumerate(eos_dois):
                doi_str = doi['EOS DOI']
                
                if doi_str in searched_dois:
                    pbar.update(1)
                    continue
                
                # Fetch citations for this DOI
                results = self._get_scholar(doi_str, start_date)
                if results:
                    citations.extend(results)
                
                # Save progress
                searched_dois.append(doi_str)
                with open(searched_dois_file, 'w') as f:
                    json.dump(searched_dois, f, indent=4)
                
                pbar.update(1)
                
                # Rate limiting: sleep after every 50 DOIs
                if (i + 1) % 50 == 0:
                    print("\nRate limit pause: sleeping for 60 seconds...")
                    time.sleep(60)
        
        print(f"\nFound {len(citations)} citations. Processing...")
        
        # Process results
        citations = self._process_urls(citations)
        citations = self._get_crossref_metadata(citations)
        citations = self._match_with_eos(citations, eos_dois)
        citations = self._combine_duplicates(citations)
        
        return citations
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        retry=retry_if_exception_type((requests.exceptions.RequestException, requests.exceptions.HTTPError))
    )
    def _get_scholar(self, doi: str, start_date=None):
        """Fetch citations from Google Scholar for a given DOI."""
        try:
            params = {
                "api_key": self.api_key,
                "engine": "google_scholar",
                "q": doi,
                "hl": "en",
                "lr": "lang_en",
                "as_vis": "1"
            }
            
            if start_date:
                params["as_ylo"] = start_date.year
            
            search = GoogleSearch(params)
            page = 1
            citations = []
            
            while True:
                search_results = search.get_dict()
                
                # Check for rate limit error
                if 'error' in search_results and 'Your account has run out of searches' in search_results['error']:
                    print("\nRate limit reached. Please wait an hour before trying again.")
                    return None
                
                # Only show errors that aren't "no results" messages
                if 'error' in search_results and not search_results['error'].startswith('Google hasn\'t returned any results'):
                    print(f"Error: {search_results['error']}")
                    break
                    
                if 'organic_results' not in search_results or not search_results['organic_results']:
                    break
                    
                for result in search_results['organic_results']:
                    result['doi'] = doi
                    citations.append(result)
                
                if 'serpapi_pagination' not in search_results or 'next' not in search_results['serpapi_pagination']:
                    break
                    
                search.params_dict.update(dict(parse_qsl(urlsplit(search_results["serpapi_pagination"]["next"]).query)))
                page += 1
                
                # Rate limiting: sleep after every 10 pages
                if page % 10 == 0:
                    time.sleep(60)
            
            return citations
            
        except Exception as e:
            if not str(e).startswith('Google hasn\'t returned any results'):
                print(f"Error fetching Google Scholar data for {doi}: {e}")
            return None
    
    def _process_urls(self, citations):
        """Process URLs and extract metadata from citations."""
        processed = []
        
        for citation in citations:
            # Skip if it's a PDF or preprint
            if self.exclude_pdf and (
                citation.get('type') == 'Pdf' or 
                '.pdf' in citation.get('link', '')
            ):
                continue
                
            if self.exclude_preprints and any(x in citation.get('link', '') for x in [
                'preprint', 'researchsquare.com', 'essopenarchive.org', 
                'biorxiv.org', 'medrxiv.org', 'authorea.com', 'techrxiv.org'
            ]):
                continue
            
            # Extract metadata
            title = self._clean_title(citation.get('title', ''))
            author = self._extract_author(citation)
            year = self._extract_year(citation)
            pub_doi = self._extract_doi_from_url(citation.get('link', ''))
            
            processed.append({
                'result_id': citation['result_id'],
                'link': citation.get('link', ''),
                'pub_doi': pub_doi,
                'author': author,
                'year': year,
                'title': title,
                'dois': [citation['doi']]
            })
        
        return processed
    
    def _get_crossref_metadata(self, citations):
        """Get metadata from Crossref for citations without DOIs."""
        for citation in citations:
            if not citation['pub_doi']:
                query = f"{citation['author']} + {citation['year']} + {citation['title']}"
                query = query.replace('+  +', '+')
                
                works = self.works.query(bibliographic=query).select('DOI', 'title', 'published-print', 'issue', 'type')
                
                best_match = None
                best_score = 0
                
                for work in works:
                    if work.get('type') in self.bad_type_list:
                        continue
                        
                    cr_title = self._clean_title(work.get('title', [''])[0])
                    score = jellyfish.jaro_winkler_similarity(
                        citation['title'].upper(),
                        cr_title.upper()
                    )
                    
                    if score > best_score:
                        best_score = score
                        best_match = work
                
                if best_match and best_score > 0.95:
                    citation['pub_doi'] = best_match['DOI']
                    if len(citation['title']) < len(best_match['title'][0]):
                        citation['title'] = best_match['title'][0]
        
        return citations
    
    def _match_with_eos(self, citations, eos_dois):
        """Match citations with EOS data."""
        matched = []
        
        for citation in citations:
            cited_references = []
            
            for eos_doi in eos_dois:
                if eos_doi['EOS DOI'] in citation['dois']:
                    cited_references.append(eos_doi)
            
            if cited_references:
                matched.append({
                    'DOI': citation['pub_doi'].upper() if citation['pub_doi'] else '',
                    'Title': citation['title'],
                    'Author': citation['author'],
                    'Year': citation['year'].strip('()') if citation['year'] else '',
                    'Cited-References': cited_references
                })
        
        return matched
    
    def _combine_duplicates(self, citations):
        """Combine citations with the same DOI."""
        doi_to_citation = {}
        
        for citation in citations:
            doi = citation['DOI']
            if doi not in doi_to_citation:
                doi_to_citation[doi] = citation
            else:
                # Combine cited references
                existing_refs = {ref['EOS DOI'] for ref in doi_to_citation[doi]['Cited-References']}
                new_refs = {ref['EOS DOI'] for ref in citation['Cited-References']}
                all_refs = existing_refs.union(new_refs)
                
                doi_to_citation[doi]['Cited-References'] = [
                    ref for ref in citation['Cited-References']
                    if ref['EOS DOI'] in all_refs
                ]
        
        return list(doi_to_citation.values())
    
    def _clean_title(self, title):
        """Clean and normalize a title."""
        title = BeautifulSoup(unescape(title), 'lxml').text
        title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode('ascii')
        return title.replace('...', '')
    
    def _extract_author(self, citation):
        """Extract author name from citation."""
        try:
            return citation['authors'][0]['name']
        except:
            try:
                pub_info = BeautifulSoup(unescape(citation['publication_info']['summary']), 'lxml').text
                match = re.match(r'^((?:\S+\s+){1}[^\r\n\t\f\v ,]+).*', pub_info)
                return match.group(1) if match else ''
            except:
                return ''
    
    def _extract_year(self, citation):
        """Extract year from citation."""
        try:
            pub_info = BeautifulSoup(unescape(citation['publication_info']['summary']), 'lxml').text
            match = re.search(r'\s+(\d{4})\s+', pub_info)
            return f"({match.group(1)})" if match else ''
        except:
            return ''
    
    def _extract_doi_from_url(self, url):
        """Extract DOI from various URL formats."""
        if not url:
            return ''
            
        # Direct DOI in URL
        match = re.search(r'\/(10\.\d+.*)$', url)
        if match:
            doi = match.group(1)
            return re.sub(r'(\/full|\/meta|\.pdf|\.abstract|\.short|\&.*|\/download|\/html|\?.*|\#.*|\;|\)|\/$|\.$)', '', doi)
        
        # Copernicus
        if 'copernicus.org' in url:
            match = re.search(r'\//(\S+)\.copernicus\.org\/articles\/(\d+)\/(\d+)\/(\d+)', url)
            if match:
                return f"10.5194/{match.group(1)}-{match.group(2)}-{match.group(3)}-{match.group(4)}"
        
        # Nature
        if 'nature.com/articles/' in url:
            match = re.search(r'nature\.com\/articles\/(\S+)', url)
            if match:
                doi = f"10.1038/{match.group(1)}"
                doi = re.sub(r'(\?.*|\/briefing.*)', '', doi)
                doi = re.sub(r'%E2%80%', '-', doi)
                match = re.match(r'10.1038\/sdata(\d{4})(\d+)', doi)
                if match:
                    return f"10.1038/sdata.{match.group(1)}.{match.group(2)}"
                return doi
        
        # AMS
        if 'journals.ametsoc.org' in url:
            match = re.search(r'\/((\w+|\.+|\-+|_+)*)\.xml', url)
            if match:
                doi = f"10.1175/{match.group(1)}"
                doi = re.sub(r'_1', '.1', doi)
                if not '-' in doi:
                    match = re.match(r'10.1175\/(\w+)(d|D)(\d{2})(\d{4})', doi)
                    if match:
                        return f"10.1175/{match.group(1)}-{match.group(2)}-{match.group(3)}-{match.group(4)}.1"
                return doi
        
        return ''
    
    def process_results(self, raw_data):
        """Process the raw data to match with EOS data."""
        # Filter out bad types
        processed_data = []
        for citation in raw_data:
            if citation.get('Type') not in self.bad_type_list:
                processed_data.append(citation)
        return processed_data
    
    def save_results(self, processed_data, output_path):
        """Save the processed data to a JSON file."""
        os.makedirs('data', exist_ok=True)
        
        output_path = os.path.join('data', os.path.basename(output_path))
        with open(output_path, 'w') as f:
            json.dump(processed_data, f, indent=4) 