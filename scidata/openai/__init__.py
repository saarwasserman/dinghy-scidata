import click

from scidata.openai.chat import cli_openai_chat
from scidata.openai.embeddings import cli_openai_embeddings
from scidata.openai.batch import cli_openai_batch


@click.group(name="openai")
def cli_openai():
    """openai utils"""
    pass  # pylint: disable=unnecessary-pass


cli_openai.add_command(cli_openai_chat)
cli_openai.add_command(cli_openai_embeddings)
cli_openai.add_command(cli_openai_batch)
