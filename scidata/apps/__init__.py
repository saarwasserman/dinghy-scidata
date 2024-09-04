import click

from scidata.apps.movies import cli_apps_movies


@click.group(name="apps")
def cli_apps():
    """apps"""
    pass  # pylint: disable=unnecessary-pass


cli_apps.add_command(cli_apps_movies)
