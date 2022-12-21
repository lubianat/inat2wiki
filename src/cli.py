import click

from pynaturalist2commons import get_all_observations


@click.group()
def cli():
    """PyNaturalist2Commons."""


cli.add_command(get_all_observations.main)

if __name__ == "__main__":
    cli()
