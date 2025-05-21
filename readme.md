# DOI Trace

Creating and updating collection of EOSDIS dataset citing publication citations

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/nasa/doi-trace.git
   cd doi-trace
   ```

2. Install the package:
   ```bash
   python -m pip install .
   ```

3. Set up configuration:
   - Copy `config.toml.example` to `config.toml`
   - Review and add API keys to `config.toml`

## Usage

### Pre-setup

Obtain latest dataset DOIs from EOSDIS DOI server https://doiserver.eosdis.nasa.gov/ords/f?p=100:8:::NO:::  and place the csv file into eosdis_csv_files/ directory.
   For all 10.5067 : Provider -> Data, Status=Registered, Query
   For ORNL and SEDAC Home->Monthly Report->'ORNL DAAC' or 'SEDAC'. ORNL and SEDAC csv files can be combined. The csv with 10.5067 DOI has more extended format. 
   Keep two latest .csv files in eosdis_csv_files/ directory.

### Web of Science Citations

1. Execute WoS search at https://www.webofscience.com/wos/woscc/cited-reference-search for 'Cited DOI' prefixes 10.5067, 10.7927, 10.3334.
   Specify 'Publication Date' that covers the latest year or two.
   Inspect WoS/ directory -- move old .bib files out of the way.
   Export search results in BibTex format with 'Full Record and Cited References' into WoS/ directory (one .bib file contains <=500 citations).

2. Run the Web of Science citation processor:
   ```bash
   python -m doi_trace wos --start-date YYYY-MM-DD --end-date YYYY-MM-DD
   ```

   Options:
   - `--start-date`: Start date for citation search (YYYY-MM-DD)
   - `--end-date`: End date for citation search (YYYY-MM-DD)

### Scopus Citations

1. Create an account and an API key from https://dev.elsevier.com/
2. Paste your API key into the "scopus_api_key" value in your config.toml 
3. Run the Scopus citation processor:
   ```bash
   python -m doi_trace scopus --start-date YYYY-MM-DD --end-date YYYY-MM-DD
   ```

   Options:
   - `--start-date`: Start date for citation search (YYYY-MM-DD)
   - `--end-date`: End date for citation search (YYYY-MM-DD)

### Run ALL processors in order

You can also run all the processors in order, rather than running each separately.

To run all processors in sequence:
   ```bash
   python -m doi_trace all --start-date YYYY-MM-DD --end-date YYYY-MM-DD
   ```

### Output

The tool generates JSON files in the output directory with the following information:
- Citation metadata (title, authors, year, etc.)
- Cited dataset DOIs
- Validation results
- Processing metadata

Output files are named according to the processor (e.g., `wos_citations_...json`, `scopus_citations_...json`).

## Configuration

The tool can be configured using:
1. Environment variables
2. `config.toml` file
3. Command-line arguments

See `config.toml` for available settings.

## Development

### Project Structure

```
doi_trace/
├── __init__.py
├── cli.py
├── config.py
└── reference_sources/
    ├── __init__.py
    ├── base.py
    └── web_of_science.py
```

### Adding New Data Sources

1. Create a new class in `reference_sources/` that inherits from `ReferenceDataSource`
2. Implement the required methods:
   - `fetch_citations()`
   - `process_results()`
   - `save_results()`
   - `get_source_name()`
3. Add a new command to `cli.py`

Creating and updating collection of EOSDIS dataset citing publication citations (Updated: 3-26-2025)
-------------

JSON files are placed in data/ directory
EOSDIS CSV files are in eosdis_csv_files/ directory
WoS .bib files are in WoS/ directory
eosutilities.py - our own library with the most common functions 

Follow steps sequentially:

1) 

2) 

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

