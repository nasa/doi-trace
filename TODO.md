# TODO

- Set up a list of project requirements at specific versions and basic project information into a pyproject.toml
- Install, run at least once
- Address linter warnings and errors; remove unused imports, commented code, etc. (use a light touch)
- Create a ReferenceDataSource abstract interface that has common methods for shared functionality
- Create a main script that runs DOI searches when given a list of data sources. E.g., `python -m main WoS` (`python -m main all` should work, too); start with running every ref data source
- Create a few tests (light touch)
- look into SQLite, since that would allow us to eliminate the `combine_doi_sources.py` step; we could just output from DB into JSON using adapter
- Create a CitationAdapter (our only implementation being a Zotero adapter, future CMR adapter)
