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

### Crossref Citations

Run the Crossref citation processor:
   ```bash
   python -m doi_trace crossref --start-date YYYY-MM-DD --end-date YYYY-MM-DD
   ```

   Options:
   - `--start-date`: Start date for citation search (YYYY-MM-DD)
   - `--end-date`: End date for citation search (YYYY-MM-DD)

### DataCite Citations

Run the DataCite citation processor:
   ```bash
   python -m doi_trace datacite --start-date YYYY-MM-DD --end-date YYYY-MM-DD
   ```

   Options:
   - `--start-date`: Start date for citation search (YYYY-MM-DD)
   - `--end-date`: End date for citation search (YYYY-MM-DD)

### Google Scholar Citations

1. Create an account and an API key from https://serpapi.com/
2. Paste your API key into the "serp_api_key" value in your config.toml 
3. Run the Google Scholar citation processor:
   ```bash
   python -m doi_trace google-scholar --start-date YYYY-MM-DD --end-date YYYY-MM-DD
   ```

   Options:
   - `--start-date`: Start date for citation search (YYYY-MM-DD)
   - `--end-date`: End date for citation search (YYYY-MM-DD)

### Combine Citations

Run the citation combiner to merge results from multiple sources:
   ```bash
   # Combine all sources
   python -m doi_trace combine

   # Combine specific sources
   python -m doi_trace combine -s wos -s google-scholar -s scopus
   ```

   The combiner will:
   - Find the most recent citation files for each source
   - Create a unique set of DOIs across all sources
   - Save the combined results to `data/combined_citations_YYYYMMDD.json`

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
