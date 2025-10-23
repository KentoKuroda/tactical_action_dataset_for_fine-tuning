import argparse
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from loguru import logger
import json


def main():
    """
    Main function to process tracking data and add team_id and position.
    """
    parser = argparse.ArgumentParser(description="Add team_id and position to tracking CSV files based on player_id.")
    parser.add_argument("--match_id", required=True, type=str, help="The match identifier to process.")
    args = parser.parse_args()
    match_ids = [str(match_id) for match_id in args.match_id.split(",")]

    for match_id in match_ids:
        tracking_csv = f"raw/tracking/{match_id}/{match_id}_pitch_plane_coordinates.csv"

        if not Path(tracking_csv).exists():
            logger.error(f"Tracking CSV file not found: {tracking_csv}")
            continue

        if match_id == '132831' or match_id == '132877':
            json_path = f"raw/tracking/{match_id}/{match_id}_metadata.json"
            player_info = parse_json_for_player_info(json_path)
        else:
            xml_path = f"raw/tracking/{match_id}/{match_id}_tracker_box_metadata.xml"
            player_info = parse_xml_for_player_info(xml_path)
        
        add_team_and_position_to_tracking(tracking_csv, player_info)


def parse_xml_for_player_info(xml_path):
    """
    Parse the XML file to extract player-to-team and player-to-position mappings.

    Args:
        xml_path (str): Path to the XML file.

    Returns:
        dict: A mapping of player_id to a dictionary with team_id and position.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    player_info = {}

    for player in root.findall(".//players/player"):
        player_id = player.get("id")
        team_id = player.get("teamId")
        position = player.get("position")
        if player_id:
            player_info[player_id] = {"team_id": team_id, "position": position}

    return player_info


def parse_json_for_player_info(json_path):
    """
    Parse the JSON file to extract player-to-team and player-to-position mappings.

    Args:
        json_path (str): Path to the JSON file.

    Returns:
        dict: A mapping of player_id to a dictionary with team_id and position.
    """
    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    player_info = {}

    # Extract players from the home team
    if "home_team" in data and "players" in data["home_team"]:
        for player in data["home_team"]["players"]:
            player_id = str(player.get("player_id"))
            team_id = str(player.get("team_id"))
            position = player.get("initial_position_name")
            if player_id:
                player_info[player_id] = {"team_id": team_id, "position": position}

    # Extract players from the away team (if present)
    if "away_team" in data and "players" in data["away_team"]:
        for player in data["away_team"]["players"]:
            player_id = str(player.get("player_id"))
            team_id = str(player.get("team_id"))
            position = player.get("initial_position_name")
            if player_id:
                player_info[player_id] = {"team_id": team_id, "position": position}

    return player_info


def add_team_and_position_to_tracking(tracking_csv, player_info):
    """
    Add team_id and position to the existing tracking CSV file.

    Args:
        tracking_csv (str): Path to the tracking CSV file to be updated.
        player_info (dict): Mapping of player_id to team_id and position.
    """
    # 読み込みと書き込みのために一時的にメモリ上で操作
    updated_rows = []
    with open(tracking_csv, mode="r") as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames

        # 新しい列を追加
        if "team_id" not in fieldnames:
            fieldnames.append("team_id")
        if "position" not in fieldnames:
            fieldnames.append("position")

        for row in reader:
            player_id = row["player_id"]
            info = player_info.get(player_id, {"team_id": "UNKNOWN", "position": "UNKNOWN"})
            row["team_id"] = info["team_id"]
            row["position"] = info["position"]
            updated_rows.append(row)

    # 更新されたデータを同じファイルに上書き
    with open(tracking_csv, mode="w", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)

    logger.info(f"Tracking data in {tracking_csv} updated with team_id and position.")


if __name__ == "__main__":
    main()
