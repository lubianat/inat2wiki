import click

from inat2wiki import get_all_observations, parse_observation_in_cli


@click.group()
def cli():
    """inat2wiki."""


cli.add_command(get_all_observations.click_get_all_observations)
cli.add_command(parse_observation_in_cli.parse_observation_in_cli)

if __name__ == "__main__":
    cli()
