import click
from .config import config


@click.command()
@click.pass_context
def all(ctx):
    """
    Search all configured providers.
    """
    click.echo(
        click.style(
            f"will run all DOI searches for configured providers: {config.get('providers')}",
            fg="green",
        )
    )


@click.command()
@click.pass_context
@click.option(
    "--provider",
    "-p",
    required=True,
    multiple=True,
    help="Use the provider's name.",
)
def some(ctx, provider):
    click.echo(click.style(f"will run DOI searches for {provider}", fg="green"))

    pass
