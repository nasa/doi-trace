import click
from pathlib import Path
from datetime import datetime
from .reference_sources.web_of_science import WebOfScience
from .reference_sources.scopus import Scopus
from .reference_sources.crossref import Crossref
from .reference_sources.datacite import DataCite
from .reference_sources.google_scholar import GoogleScholar
from .config import config

"""
This module handles ensuring that 
    1.) the click CLI always has a context object https://click.palletsprojects.com/en/stable/commands/
    2.) the top-level commands groups are always added to the CLI https://click.palletsprojects.com/en/stable/api/#click.Group.add_command
"""


# NOTE:
# Currently unimplemented, `output` and `pretty` are stored in context.
# - to make use of `pretty`, read it from context (ctx) and then either format with json.dumps or just dump to stdout.
# - to make use of `output_file`, read it from context (ctx) and then write to it instead of outputting to stdout.
#   - e.g., output_file.write(json.dumps(data, indent=PRETTY_PRINT_INDENT if context.obj.get("pretty") else None,))


@click.group()
def cli():
    """DOI Trace - Track and analyze dataset citations."""
    pass


@cli.command()
@click.option('--start-date', type=click.DateTime(formats=["%Y-%m-%d"]), help="Start date for citation search (YYYY-MM-DD)", required=True)
@click.option('--end-date', type=click.DateTime(formats=["%Y-%m-%d"]), help="End date for citation search (YYYY-MM-DD)", required=True)
def wos(start_date, end_date):
    """Fetch citations from Web of Science."""
    processor = WebOfScience()
    citations = processor.fetch_citations(None, start_date, end_date)
    processed = processor.process_results(citations)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"wos_citations_{timestamp}.json"
    processor.save_results(processed, output_path)
    click.echo(f"Results saved to {output_path}")


@cli.command()
@click.option('--start-date', type=click.DateTime(formats=["%Y-%m-%d"]), help="Start date for citation search (YYYY-MM-DD)", required=True)
@click.option('--end-date', type=click.DateTime(formats=["%Y-%m-%d"]), help="End date for citation search (YYYY-MM-DD)", required=True)
def scopus(start_date, end_date):
    """Fetch citations from Scopus."""
    processor = Scopus()
    citations = processor.fetch_citations(None, start_date, end_date)
    processed = processor.process_results(citations)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"scopus_citations_{timestamp}.json"
    processor.save_results(processed, output_path)
    click.echo(f"Results saved to {output_path}")


@cli.command()
@click.option('--start-date', type=click.DateTime(formats=["%Y-%m-%d"]), help="Start date for citation search (YYYY-MM-DD)", required=True)
@click.option('--end-date', type=click.DateTime(formats=["%Y-%m-%d"]), help="End date for citation search (YYYY-MM-DD)", required=True)
def crossref(start_date, end_date):
    """Fetch citations from Crossref."""
    processor = Crossref()
    citations = processor.fetch_citations(None, start_date, end_date)
    processed = processor.process_results(citations)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"crossref_citations_{timestamp}.json"
    processor.save_results(processed, output_path)
    click.echo(f"Results saved to {output_path}")


@cli.command()
@click.option('--start-date', type=click.DateTime(formats=["%Y-%m-%d"]), help="Start date for citation search (YYYY-MM-DD)", required=True)
@click.option('--end-date', type=click.DateTime(formats=["%Y-%m-%d"]), help="End date for citation search (YYYY-MM-DD)", required=True)
def datacite(start_date, end_date):
    """Fetch citations from DataCite."""
    processor = DataCite()
    citations = processor.fetch_citations(None, start_date, end_date)
    processed = processor.process_results(citations)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"datacite_citations_{timestamp}.json"
    processor.save_results(processed, output_path)
    click.echo(f"Results saved to {output_path}")


@cli.command()
@click.option('--start-date', type=click.DateTime(formats=["%Y-%m-%d"]), help="Start date for citation search (YYYY-MM-DD)", required=True)
@click.option('--end-date', type=click.DateTime(formats=["%Y-%m-%d"]), help="End date for citation search (YYYY-MM-DD)", required=True)
def google_scholar(start_date, end_date):
    """Fetch citations from Google Scholar."""
    processor = GoogleScholar()
    citations = processor.fetch_citations(None, start_date, end_date)
    processed = processor.process_results(citations)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"google_scholar_citations_{timestamp}.json"
    processor.save_results(processed, output_path)
    click.echo(f"Results saved to {output_path}")


@cli.command()
@click.option('--start-date', type=click.DateTime(formats=["%Y-%m-%d"]), help="Start date for citation search (YYYY-MM-DD)", required=True)
@click.option('--end-date', type=click.DateTime(formats=["%Y-%m-%d"]), help="End date for citation search (YYYY-MM-DD)", required=True)
def all(start_date, end_date):
    """Run all citation processors."""
    processors = [
        WebOfScience(),
        Scopus(),
        Crossref(),
        DataCite(),
        GoogleScholar()
    ]
    
    for processor in processors:
        click.echo(f"\nProcessing {processor.get_source_name()} citations...")
        citations = processor.fetch_citations(None, start_date, end_date)
        processed = processor.process_results(citations)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"{processor.get_source_name().lower().replace(' ', '_')}_citations_{timestamp}.json"
        processor.save_results(processed, output_path)
        click.echo(f"Results saved to {output_path}")


if __name__ == '__main__':
    cli()
