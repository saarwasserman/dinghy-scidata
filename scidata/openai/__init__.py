import click

from scidata.openai.chat import cli_openai_chat


@click.group(name="openai")
def cli_openai():
    """openai utils"""
    pass  # pylint: disable=unnecessary-pass


cli_openai.add_command(cli_openai_chat)