"""entrypoint for all cli commands
"""

import click

#from nblade import settings  # pylint: disable=unused-import
from scidata.openai import cli_openai


# pylint: disable=missing-function-docstring
@click.group(name="dinghy-scidata")
def cli():
    pass

def main():
    cli.add_command(cli_openai)
    cli()

if __name__ == "__main__":
    main()
