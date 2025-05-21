import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd

from .base import ReferenceDataSource


class WebOfScience(ReferenceDataSource):
    """Web of Science data source implementation.
    
    This class handles fetching and processing citation data from Web of Science
    BibTeX files.
    """
    
    def __init__(self, wos_dir: str = "WoS", eosdis_csv_dir: str = "eosdis_csv_files"):
        """Initialize the Web of Science data source.
        
        Args:
            wos_dir: Directory containing Web of Science BibTeX files
            eosdis_csv_dir: Directory containing EOSDIS CSV files
        """
        self.wos_dir = Path(wos_dir)
        self.eosdis_csv_dir = Path(eosdis_csv_dir)
        self.prefixes = ["10.5067", "10.7927", "10.3334"]
    
    def get_source_name(self) -> str:
        """Get the name of the data source.
        
        Returns:
            Name of the data source
        """
        return "Web of Science"
    
    def fetch_citations(self, dois: List[str], start_date: Optional[str] = None, 
                       end_date: Optional[str] = None) -> Dict[str, Any]:
        """Fetch citations from Web of Science BibTeX files.
        
        Args:
            dois: List of DOIs to search for citations
            start_date: Optional start date for the search (format: YYYY-MM-DD)
            end_date: Optional end date for the search (format: YYYY-MM-DD)
            
        Returns:
            Dictionary containing the raw citation data
        """
        # Read all BibTeX files in the WoS directory
        wos_files = [f for f in self.wos_dir.glob("*.bib")]
        if not wos_files:
            raise FileNotFoundError(f"No BibTeX files found in {self.wos_dir}")

        all_entries = []
        for wos_file in wos_files:
            print(f"Processing {wos_file.name}")
            with open(wos_file, 'r', encoding='utf-8') as f:
                data = f.read()
            
            data = self._clean_bibtex_data(data)
            entries = self._parse_bibtex_entries(data)
            
            all_entries.extend(entries)
        
        return {
            "entries": all_entries,
            "metadata": {
                "source": "Web of Science",
                "start_date": start_date,
                "end_date": end_date,
                "total_entries": len(all_entries)
            }
        }
    
    def process_results(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the raw Web of Science data into a standardized format.
        
        Args:
            raw_data: Raw data from Web of Science
            
        Returns:
            Processed data in a standardized format
        """
        entries = raw_data["entries"]
        unique_entries = self._remove_duplicates(entries)
        eosdis_data = self._get_eosdis_data()
        valid_entries, invalid_entries = self._validate_dois(unique_entries, eosdis_data)
        matched_entries = self._match_to_eosdis(valid_entries, eosdis_data)
        
        return {
            "valid_entries": matched_entries,
            "invalid_entries": invalid_entries,
            "metadata": {
                "source": "Web of Science",
                "total_entries": len(matched_entries),
                "invalid_entries": len(invalid_entries)
            }
        }
    
    def save_results(self, processed_data: Dict[str, Any], output_path: Path) -> None:
        """Save the processed results to a JSON file.
        
        Args:
            processed_data: Processed data to save
            output_path: Path to save the results to
        """
        # Convert to DataFrame for easier handling
        df = pd.DataFrame(processed_data["valid_entries"])
        
        # Save to JSON
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_json(output_path, orient="records", indent=2)
    
    def _clean_bibtex_data(self, data: str) -> str:
        """Clean up BibTeX data by replacing problematic characters and formats.
        
        Args:
            data: Raw BibTeX data
            
        Returns:
            Cleaned BibTeX data
        """
        replacements = {
            'inproceedings': 'article',
            'incollection': 'article',
            'EISSN': 'XXXX',
            '%2D': '-',
            '%2B': '+',
            '%5F': '_',
            'M0D': 'MOD',
            '(Terra)': '',
            '0BBHQ5W22HME': 'OBBHQ5W22HME',
            '2XX6ZY3DUGNQ': '2XXGZY3DUGNQ',
            '3420HQM9AK6Q': '342OHQM9AK6Q',
            '3MJC62': '3MJC6',
            '3RQ5YS674DG': '3RQ5YS674DGQ',
            '6116VW8LLWJ7': '6II6VW8LLWJ7',
            '6J5LHH0HZHN4': '6J5LHHOHZHN4',
            '7MCPBJ41YOK6': '7MCPBJ41Y0K6',
            '7Q8HCCWS410R': '7Q8HCCWS4I0R',
            '8GQ8LZQVLOVL': '8GQ8LZQVL0VL',
            '9EBR2T0VXUFG': '9EBR2T0VXUDG',
            '9EBR2TOVXUDG': '9EBR2T0VXUDG',
            'AOPMUXXVUYNH': 'A0PMUXXVUYNH',
            'AD7B-0HQNSJ29': 'AD7B0HQNSJ29',
            'AJMZ0503TGUR': 'AJMZO5O3TGUR',
            'C98E2L0ZTWO': 'C98E2L0ZTWO4',
            'CRY0SPHERE': 'CRYOSPHERE',
            'CYGNSL1X20': 'CYGNS-L1X20',
            'D7GK8F5J8M8': 'D7GK8F5J8M8R',
            'D7GK8F5J8M8RR': 'D7GK8F5J8M8R',
            'FCCZIIFRPZ30': 'FCCZIIFRPZ3O',
            'FQPTQ40J22TL': 'FQPTQ4OJ22TL',
            'G0ZCARDS': 'GOZCARDS',
            'GDQOCUCVTE2Q': 'GDQ0CUCVTE2Q',
            'GESAD/GESAD': 'GFSAD/GFSAD',
            'GRSAD/GRSAD': 'GFSAD/GFSAD',
            'NEW-TOCOKVZHF': 'NEWTOCOKVZHF',
            'NPZYNEEGQUO': 'NPZYNEEUGQUO',
            '04HAQJEWWUU8': 'O4HAQJEWWUU8',
            '057VAIT2AYYY': 'O57VAIT2AYYY',
            '0C7B04ZM9G6Q': 'OBBHQ5W22HME',
            '0MGEV': 'OMGEV',
            'OFTBVIEW': 'ORBVIEW',
            '0RBVIEW': 'ORBVIEW',
            '0SCT2-L2BV2': 'OSCT2-L2BV2',
            'LOU3HJDS97300': 'OU3HJDS973O0',
            'Q0310G10G1XULZS': 'Q0310G1XULZS',
            'Q5GVUVUIVG07': 'Q5GVUVUIVGO7',
            'SEAVVIFS': 'SEAWIFS',
            'SEAWIF-S': 'SEAWIFS',
            'SEAWIFSOC': 'SEAWIFS_OC',
            'SEAWIFS_0C': 'SEAWIFS_OC',
            'SMAP20': 'SMP20',
            'SYN1DEG3H0UR': 'SYN1DEG3HOUR',
            'TEMSC2LCR5': 'TEMSC-2LCR5',
            'TERRA1AQUA': 'TERRA+AQUA',
            'TERRATHORN+AQUA': 'TERRA+AQUA',
            'TRMM/TMPAOH-E/7': 'TRMM/TMPA/3H/7',
            'UBKO5ZUI715V': 'UBKO5ZUI7I5V',
            'VFMSTANDARD': 'VFM-STANDARD',
            'VJAPPLI1CSIV': 'VJAFPLI1CSIV',
            'L3CLOUDOCCURRENCE': 'L3_CLOUD_OCCURRENCE',
            'LIS-0TD': 'LIS-OTD',
            'MODO8': 'MOD08',
            'MODO9GA006': 'MODO9GA.006',
            'MODI3': 'MOD13',
            'MOD15A2.006': 'MOD15A2H.006',
            'MOD17A3.006': 'MOD17A3H.006',
            'MQD35': 'MOD35',
            'MODATML2.06': 'MODATML2.006',
            'MODIS?L3B': 'MODIS/L3B',
            'MYD06_GL2': 'MYD06_L2',
            'MYD08-M3': 'MYD08_M3',
            'MODO9': 'MOD09'
        }
        
        for old, new in replacements.items():
            data = data.replace(old, new)
        
        return data
    
    def _parse_bibtex_entries(self, data: str) -> List[Dict[str, Any]]:
        """Parse BibTeX entries into a list of dictionaries.
        
        Args:
            data: Cleaned BibTeX data
            
        Returns:
            List of parsed entries
        """
        entries = []
        data_entries = data.split('@article')[1:]  # Skip the first empty entry
        
        for entry in data_entries:
            entry_dict = {
                'wos': None,
                'doi': None,
                'year': None,
                'title': None,
                'author': None,
                'isbn': None,
                'issn': None,
                'early_access_date': None,
                'cited_references': []
            }
            
            for line in entry.split('\n'):
                line = line.strip().replace('{', '').replace('}', '')
                
                # Extract WOS ID
                if wos_match := re.search(r'Unique-ID = WOS:(\S+)', line):
                    entry_dict['wos'] = wos_match.group(1)
                
                # Extract DOI
                if doi_match := re.search(r'DOI = (\S+)', line):
                    entry_dict['doi'] = doi_match.group(1).upper().replace('\\_', '_')
                
                # Extract year
                if year_match := re.search(r'Year = (\S+)', line):
                    entry_dict['year'] = year_match.group(1)
                
                # Extract early access date
                if early_date_match := re.search(r'EarlyAccessDate = (.*)', line):
                    early_date = early_date_match.group(1)
                    if year_match := re.search(r'\d{4}', early_date):
                        entry_dict['early_access_date'] = year_match.group(0)
                
                # Extract ISBN
                if isbn_match := re.search(r'ISBN = (\S+)', line):
                    entry_dict['isbn'] = isbn_match.group(1).replace('{', '').replace('}', '')
                
                # Extract ISSN
                if issn_match := re.search(r'ISSN = (\S+)', line):
                    entry_dict['issn'] = issn_match.group(1).replace('{', '').replace('}', '')
                
                # Extract title
                if title_match := re.search(r'Title = (.*)', line):
                    title = title_match.group(1).strip()
                    title = re.sub(r'\\', '', title)
                    if title.endswith(','):
                        title = title[:-1]
                    entry_dict['title'] = title
                
                # Extract author
                if author_match := re.search(r'Author = (.*)', line):
                    entry_dict['author'] = author_match.group(1).split(' and')[0]
                
                # Extract cited references
                for prefix in self.prefixes:
                    sub_prefix = prefix.split('10.', 1)[1]
                    if ref_match := re.search(f'(10\.{sub_prefix}.*?)(,|])', line):
                        ref = ref_match.group(1).strip()
                        ref = re.sub(r'(\s+|DOI|\\|}|\)|]|)', '', ref)
                        ref = re.sub(r'\.$', '', ref)
                        if ref.upper() not in entry_dict['cited_references']:
                            entry_dict['cited_references'].append(ref.upper())
            
            # Use early access date as year if year is missing
            if not entry_dict['year'] and entry_dict['early_access_date']:
                entry_dict['year'] = entry_dict['early_access_date']
            
            entries.append(entry_dict)
        
        return entries
    
    def _remove_duplicates(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate entries based on WOS ID.
        
        Args:
            entries: List of entries to deduplicate
            
        Returns:
            Deduplicated list of entries
        """
        seen_wos = set()
        unique_entries = []
        
        for entry in entries:
            if entry['wos'] and entry['wos'] not in seen_wos:
                seen_wos.add(entry['wos'])
                unique_entries.append(entry)
        
        return unique_entries
    
    def _get_eosdis_data(self) -> List[Dict[str, Any]]:
        """Get EOSDIS data from CSV files.
        
        Returns:
            List of dictionaries containing EOSDIS data
        """
        csv_files = list(self.eosdis_csv_dir.glob("*.csv"))
        if not csv_files:
            raise FileNotFoundError(f"No CSV files found in {self.eosdis_csv_dir}")
        
        df_all = pd.DataFrame()
        for file in csv_files:
            print(f"Reading: {file}")
            df = pd.read_csv(file, encoding='unicode_escape')
            try:  # for EOS DOIS
                column_names = ['DOI_NAME', 'LP_AGENCY', 'SPECIAL']
                df = df[column_names]
                df = df.rename(columns={'DOI_NAME': 'EOS DOI',
                                        'LP_AGENCY': 'LP Agency',
                                        'SPECIAL': 'Shortname'})
            except KeyError:
                pass
            try:  # for ORNL & SEDAC
                column_names = ['DOI_NAME', 'PROVIDER', 'DOI_SPECIAL']
                df = df[column_names]
                df = df.rename(columns={'DOI_NAME': 'EOS DOI',
                                        'PROVIDER': 'LP Agency',
                                        'DOI_SPECIAL': 'Shortname'})
            except KeyError:
                pass
            print(f'Loading {file}')
            df_all = pd.concat([df_all, df])
        print(f'Total {df_all.shape[0]} EOS DOIS')
        df_all['EOS DOI'] = df_all['EOS DOI'].str.upper()
        return df_all.to_dict('records')
    
    def _validate_dois(self, entries: List[Dict[str, Any]], eosdis_data: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Validate DOIs against EOSDIS data.
        
        Args:
            entries: List of entries to validate
            eosdis_data: List of EOSDIS entries
            
        Returns:
            Tuple of (valid entries, invalid entries)
        """
        valid_dois = {d['EOS DOI'] for d in eosdis_data}
        valid_entries = []
        invalid_entries = []
        
        for entry in entries:
            valid_refs = []
            invalid_refs = []
            
            for ref in entry['cited_references']:
                if ref in valid_dois:
                    valid_refs.append(ref)
                elif ref:
                    invalid_refs.append(ref)
            
            entry['cited_references'] = valid_refs
            entry['invalid_references'] = invalid_refs
            
            if valid_refs:
                valid_entries.append(entry)
            else:
                invalid_entries.append(entry)
        
        return valid_entries, invalid_entries
    
    def _match_to_eosdis(self, entries: List[Dict[str, Any]], eosdis_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Match entries to EOSDIS data.
        
        Args:
            entries: List of entries to match
            eosdis_data: List of EOSDIS entries
            
        Returns:
            List of matched entries
        """
        # Create a mapping of DOIs to EOSDIS data
        eosdis_map = {d['EOS DOI']: d for d in eosdis_data}
        
        for entry in entries:
            entry['eosdis_matches'] = []
            for ref in entry['cited_references']:
                if ref in eosdis_map:
                    entry['eosdis_matches'].append(eosdis_map[ref])
        
        return entries 