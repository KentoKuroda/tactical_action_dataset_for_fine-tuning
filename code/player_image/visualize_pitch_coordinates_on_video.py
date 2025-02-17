import os
import json
import re
import argparse
import subprocess


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--match_ids', required=True, help="Comma-separated list of match IDs to process")
    return parser.parse_args()


def main():
    args = parse_arguments()
    match_ids = [str(match_id) for match_id in args.match_ids.split(",")]

    for match_id in match_ids:
        # input
        interim_dir = f"interim/{match_id}"

        visualize_pitch_coordinates()


def visualize_pitch_coordinates():
    print("a")


if __name__ == '__main__':
    main()