import click
from pathlib import Path
from datetime import datetime
from .reference_sources.web_of_science import WebOfScience
from .config import config


@click.group()
def cli():
    """DOI Trace CLI tool for fetching and processing citations."""
    pass


@cli.command()
@click.option('--start-date', type=str, help='Start date for citation search (format: YYYY-MM-DD)')
@click.option('--end-date', type=str, help='End date for citation search (format: YYYY-MM-DD)')
def wos(start_date, end_date):
    """Fetch citations from Web of Science."""
    wos = WebOfScience()
    raw_data = wos.fetch_citations(dois=[], start_date=start_date, end_date=end_date)
    processed_data = wos.process_results(raw_data)
    output_path = Path(config.get_directory('output')) / f"wos_citations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    wos.save_results(processed_data, output_path)
    click.echo(f"Citations saved to {output_path}")


if __name__ == '__main__':
    cli()
