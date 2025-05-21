import click
from pathlib import Path
from datetime import datetime
from .reference_sources.web_of_science import WebOfScience
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


@cli.command()
@click.option('--start-date', type=str, help='Start date for citation search (format: YYYY-MM-DD)')
@click.option('--end-date', type=str, help='End date for citation search (format: YYYY-MM-DD)')
def all(start_date, end_date):
    """Run all citation processors in sequence."""
    processors = [WebOfScience]  # Add other processors here as they are implemented
    for processor_class in processors:
        click.echo(f"Running {processor_class.__name__}...")
        processor = processor_class()
        raw_data = processor.fetch_citations(dois=[], start_date=start_date, end_date=end_date)
        processed_data = processor.process_results(raw_data)
        output_path = Path(config.get_directory('output')) / f"{processor_class.__name__.lower()}_citations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        processor.save_results(processed_data, output_path)
        click.echo(f"Citations saved to {output_path}")


if __name__ == '__main__':
    cli()
