"""
This script converts raw XML tracking data to MOT-style CSV files using pitch plane coordinates.

Usage:
    python coordinate_conversion/convert_raw_to_pitch_plane_mot.py --match_id <match_id>

Example:
    python scripts/coordinate_conversion/convert_raw_to_pitch_plane_mot.py --match_id 117093

Arguments:
    --match_id: The match identifier to process.
"""

import argparse
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from loguru import logger
import json


def main():
    """
    Main function to parse arguments and execute conversion.
    """
    parser = argparse.ArgumentParser(description="Convert raw XML tracking data to MOT-style CSV using match_id.")
    parser.add_argument("--match_id", required=True, type=str, help="The match identifier to process.")
    args = parser.parse_args()
    match_ids = [str(match_id) for match_id in args.match_id.split(",")]

    for match_id in match_ids:
        output_csv = f"raw/tracking/{match_id}/{match_id}_pitch_plane_coordinates.csv"

        if match_id == '132831' or match_id == '132877':
            for i in range(2, 4):
                input_json = f"raw/tracking/{match_id}/{match_id}_{i}_frame_data.json"
                output_csv = f"raw/tracking/{match_id}/{match_id}_{i}_pitch_plane_coordinates.csv"
                tracking_data = parse_json(input_json)
                write_csv(tracking_data, output_csv)
        else:
            input_xml = f"raw/tracking/{match_id}/{match_id}_tracker_box_data.xml"
            tracking_data = parse_xml(input_xml)
            write_csv(tracking_data, output_csv)


def parse_xml(xml_path):
    """
    Parse the XML file and extract tracking data.

    Args:
        xml_path (str): Path to the XML file.

    Returns:
        list of dict: A list containing tracking information for each player in each frame.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    tracking_data = []

    for frame in root.findall("frame"):
        frame_number = int(frame.get("frameNumber"))
        match_time = float(frame.get("matchTime"))
        
        for player in frame:
            player_id = player.get("playerId")
            loc = player.get("loc")
            # Convert loc string to float coordinates
            try:
                x, y = map(float, loc.strip("[]").split(","))
                tracking_data.append({
                    "frame": frame_number,
                    "match_time": match_time,
                    "player_id": player_id,
                    "x": x,
                    "y": y
                })
            except ValueError:
                logger.warning(f"Invalid location format for player {player_id} in frame {frame_number}")

    return tracking_data


def parse_json(json_path):
    """
    Parse the JSON file and extract tracking data.

    Args:
        json_path (str): Path to the JSON file.

    Returns:
        list of dict: A list containing tracking information for each player in each frame.
    """
    with open(json_path, "r") as f:
        data = json.load(f)

    tracking_data = []
    for frame_number, players in data.items():
        for player in players:
            try:
                tracking_data.append({
                    "frame": int(frame_number),
                    "match_time": float(player.get("match_time", 0)),
                    "player_id": "ball" if player.get("player_id") == None else player.get("player_id"),
                    "x": float(player.get("x", 0)),
                    "y": float(player.get("y", 0))
                })
            except ValueError:
                logger.warning(f"Invalid data format in frame {frame_number}")
    
    return tracking_data


def write_csv(tracking_data, output_csv):
    """
    Write the tracking data to a CSV file in MOT-style format.

    Args:
        tracking_data (list of dict): Tracking information.
        output_csv (str): Path to the output CSV file.
    """
    fieldnames = ["frame", "match_time", "player_id", "x", "y"]
    with open(output_csv, mode="w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for data in tracking_data:
            writer.writerow(data)

    logger.info(f"Tracking data written to {output_csv}")


if __name__ == "__main__":
    main()