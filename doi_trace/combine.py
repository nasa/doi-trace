import json
import re
import glob
import os
from datetime import datetime
from crossref.restful import Works, Etiquette
from habanero import cn
from doi_trace.config import config
from tqdm import tqdm

class CitationCombiner:
    """Combines citation data from multiple sources."""
    
    def __init__(self):
        """Initialize the citation combiner."""
        # Create etiquette from config for Crossref API
        self.etiquette = Etiquette(
            config.data.get('project_name', 'DOI Trace'),
            config.data.get('version', '1.0.0'),
            config.data.get('organization', 'NASA'),
            config.data.get('email', '')
        )
        self.works = Works(etiquette=self.etiquette)
    
    def combine_sources(self, sources, date=None):
        """Combine citation data from specified sources.
        
        Args:
            sources (list): List of source names to combine (e.g., ['wos', 'scopus'])
            date (str, optional): Date string to use in filenames. Defaults to current date.
        """
        if not date:
            date = datetime.now().strftime("%Y%m%d")
            
        # Load and combine data from each source
        eos_matched = []
        print("\nLoading source files...")
        for source in tqdm(sources, desc="Loading sources"):
            pattern = f'data/{source}_citations_*.json'
            files = glob.glob(pattern)
            if not files:
                print(f"No files found for source: {source}")
                continue
                
            # Use most recent file for each source
            latest_file = max(files, key=os.path.getctime)
            print(f"Loading {latest_file}")
            
            with open(latest_file) as f:
                data = json.load(f)
                eos_matched.append([latest_file, source, data])
        
        if not eos_matched:
            print("No data found to combine")
            return None
            
        print("\nProcessing citations...")
        # Create unique set of DOIs
        combined_dois = self._create_unique_dois(eos_matched)
        
        # Add tags and references
        combined_dois = self._add_tags_and_references(combined_dois, eos_matched)
        
        # Convert sets to lists
        combined_dois = self._convert_sets_to_lists(combined_dois)
        
        # Fill in missing years
        combined_dois = self._fill_missing_years(combined_dois)
        
        # Save combined results
        output_path = f'data/combined_citations_{date}.json'
        with open(output_path, 'w') as f:
            json.dump(combined_dois, f, indent=4)
            
        print(f"\nCombined results saved to {output_path}")
        return combined_dois
    
    def _create_unique_dois(self, eos_matched):
        """Create unique set of DOIs and convert to list of dictionaries."""
        dois = set()
        for source in tqdm(eos_matched, desc="Creating unique DOIs"):
            for publication in source[2]:
                try:
                    dois.add(publication['DOI'].upper())
                except:
                    pass
                    
        combined_dois = []
        for doi in tqdm(list(dois), desc="Initializing DOI records"):
            combined_dois.append({
                'DOI': doi.upper(),
                'Title': None,
                'Year': None,
                'Cited-References': set(),
                'tags': set()
            })
            
        print(f"Found {len(combined_dois)} unique DOIs")
        return combined_dois
    
    def _add_tags_and_references(self, combined_dois, eos_matched):
        """Add tags and references to each DOI."""
        for doi in tqdm(combined_dois, desc="Adding tags and references"):
            for source in eos_matched:
                for publication in source[2]:
                    if doi['DOI'] == publication.get('DOI', '').upper():
                        # Update year if available
                        if publication.get('Year') and not re.search('None', str(publication['Year'])):
                            doi['Year'] = publication['Year']
                            if re.search('"', str(doi['Year'])):
                                doi['Year'] = re.sub('"', '', str(doi['Year']))
                                
                        # Update title if not set
                        if not doi.get('Title'):
                            doi['Title'] = publication.get('Title')
                            
                        # Add references and tags
                        for ref in publication.get('Cited-References', []):
                            doi['Cited-References'].add(tuple(ref.items()))
                            tag = ref.get('EOS DOI')
                            agency = ref.get('LP Agency')
                            if tag:
                                doi['tags'].add(tuple(('tag', f'doi:{tag.upper()}')))
                                doi['tags'].add(tuple(('tag', f'db:{source[1]}')))
                            if agency:
                                doi['tags'].add(tuple(('tag', f'DAAC:{agency}')))
        
        return combined_dois
    
    def _convert_sets_to_lists(self, combined_dois):
        """Convert sets to lists for JSON serialization."""
        for doi in tqdm(combined_dois, desc="Converting sets to lists"):
            refs = [dict(ref) for ref in doi['Cited-References']]
            tags = [dict([tag]) for tag in doi['tags']]
            doi['Cited-References'] = refs
            doi['tags'] = tags
        return combined_dois
    
    def _fill_missing_years(self, combined_dois):
        """Fill in missing years using Crossref and Habanero."""
        for doi in tqdm(combined_dois, desc="Filling missing years"):
            if not doi.get('Year') or doi['Year'] in ('', 'None'):
                # Try Crossref first
                try:
                    record = self.works.doi(doi['DOI'])
                    if record and record.get('published', {}).get('date-parts'):
                        year = record['published']['date-parts'][0][0]
                        doi['Year'] = str(year)
                        continue
                except:
                    pass
                
                # Try Habanero if Crossref fails
                try:
                    bib = cn.content_negotiation(ids=doi['DOI'], format="bibentry")
                    year = re.search(r'year = (\S+),', bib).group(1)
                    doi['Year'] = year.replace('{', '').replace('}', '')
                except:
                    pass
        
        return combined_dois 