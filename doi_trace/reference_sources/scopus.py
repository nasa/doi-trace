import re
from datetime import datetime
from .base import ReferenceDataSource
from ..config import config
import json
from elsapy.elsclient import ElsClient
from elsapy.elssearch import ElsSearch
import eosutilities as eosutil


class Scopus(ReferenceDataSource):
    def __init__(self):
        super().__init__()
        self.scopus_api_key = config.get('api', {}).get('scopus_api_key')

    def fetch_citations(self, dois, start_date=None, end_date=None):
        """Fetch citations from Scopus."""
        if not self.scopus_api_key:
            raise ValueError("Scopus API key is not set. Please check your configuration.")
        
        eos_dois = eosutil.getEOSCSV()  # Load EOS DOIs from CSV
        eos_dois = eosutil.getAcronyms(eos_dois)  # Process DOIs
        citations = []

        for doi in eos_dois:
            results = self._get_scopus(doi['EOS DOI'])
            citations.extend(results)
        return citations

    def process_results(self, raw_data):
        """Process the raw data to match with EOS data."""
        return self._match_scopus_eos(raw_data)

    def save_results(self, processed_data, output_path):
        """Save the processed data to a JSON file."""
        with open(output_path, 'w') as f:
            json.dump(processed_data, f, indent=4)

    def get_source_name(self):
        """Return the name of the source."""
        return "Scopus"

    def _get_scopus(self, term):
        """Fetch Scopus citations for a given term."""
        term = f'"{term}"'
        term = term.split('(', 1)[0]  # for ORNLS that have parenthesis in the doi name
        client = ElsClient(self.scopus_api_key)
        
        print('here with ' + self.scopus_api_key)
        print(term)
        
        doc_srch = ElsSearch(term, 'scopus')
        doc_srch.execute(client, get_all=True)
        return doc_srch.results

    def _match_scopus_eos(self, eos_dois):
        """Match Scopus citations with EOS data."""
        full_scopus = []
        scopus_and_refs = []
        scopus_errors = []
        for i, e in enumerate(eos_dois):
            if i % 100 == 0:
                print(i, '/', len(eos_dois), '\t', datetime.now().strftime("%H:%M:%S"), flush=True)
            try:
                results = self._get_scopus(e['EOS DOI'])
            except:
                print(e['EOS DOI'], 'could not be pulled from SCOPUS ElsSearch')
                results = [{'error': None}]
                pass
            if not results[0].get('error', None) and (results[0].get('error', None) != 'Result set was empty'):
                for result in results:
                    try:
                        isbn = result.get('prism:isbn', None)
                        if isbn:
                            isbn = isbn[0].get('$', None)
                    except:
                        pass
                    try:
                        scopus_id = result['dc:identifier']
                        full_scopus.append({'SCOPUS_ID': re.sub('SCOPUS_ID:', '', result.get('dc:identifier', '')),
                                           'DOI': result.get('prism:doi', None),
                                           'Title': result.get('dc:title', None),
                                           'Year': re.search(r'\d{4}', result.get('prism:coverDate')).group(0),
                                           'ISBN': isbn,
                                           'ISSN': result.get('prism:issn', None),
                                           'EISSN': result.get('prism:eIssn', None),
                                           'Cited-References': [e]
                                          })
                        scopus_and_refs.append({'SCOPUS_ID': re.sub('SCOPUS_ID:', '', result.get('dc:identifier', '')),
                                                'Cited-References': [e]
                                          })
                    except:
                        print(e['EOS DOI'], 'missing scopus_id')
                        scopus_errors.append(e['EOS DOI'])
        # create unique list of scopus DOIs
        unique = set()
        for doi in full_scopus:
            unique.add(tuple(doi.items()))
        unique_list = []
        for u in unique:
            unique_list.append(dict(u))
        # add citation list to each scopus DOI
        for u in unique_list:
            u['Cited-References'] = []
            for sr in scopus_and_refs:
                if u['SCOPUS_ID'] == sr['SCOPUS_ID']:
                    u['Cited-References'].append(sr['Cited-References'][0])
        # uppercases DOIS
        for u in unique_list:
            if u['DOI']:
                u['DOI'] = u['DOI'].upper()
        return unique_list 