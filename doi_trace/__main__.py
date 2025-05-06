import click
from doi_trace.cli import all, some

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
@click.version_option()
@click.pass_context
@click.option(
    "--output",
    "-o",
    "output_file",
    show_default=True,
    type=click.File("w"),
    help="Write output to <file> instead of stdout.",
)
@click.option(
    "--pretty/--no-pretty",
    "-p/-np",
    default=True,
    show_default=True,
    help="JSON formatting.",
)
def main(ctx, output_file, pretty):
    try:
        ctx.ensure_object(dict)
        ctx.obj["output_file"] = output_file
        ctx.obj["pretty"] = pretty

    except KeyboardInterrupt:
        click.echo(click.style("Exiting due to SIGNINT.", fg="red"))
        exit(0)


main.add_command(all)
main.add_command(some)


if __name__ == "__main__":
    main(obj={})
