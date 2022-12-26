import click

from pynaturalist2commons import get_all_observations, parse_observation


@click.group()
def cli():
    """PyNaturalist2Commons."""


cli.add_command(get_all_observations.click_get_all_observations)
cli.add_command(parse_observation.parse_observation)

if __name__ == "__main__":
    cli()
