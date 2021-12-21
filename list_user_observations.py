#!/usr/bin/env python3
from pyinaturalist import *
import sys
import pprint


def main():
    try:
        id = sys.argv[1]
    except:
        id = input("Enter the user id:")

    observations = get_observations(user_id="my_username")

    for obs in observations["results"]:
        pprint(obs)


if __name__ == "__main__":
    main()
