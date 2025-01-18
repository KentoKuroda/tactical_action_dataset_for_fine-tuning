import os
import re
import json
import pandas as pd
import argparse
from pathlib import Path

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--match_id', required=True, help="Match ID to process")
    return parser.parse_args()


def main():
    args = parse_arguments()
    match_ids = [str(match_id) for match_id in args.match_id.split(",")]

    # Load JSON data
    json_file = 'raw/video_info.json'
    with open(json_file, 'r') as f:
        json_data = json.load(f)

    for match_id in match_ids:
        csv_dir = Path(f'raw/tracking/{match_id}')
        output_dir = Path(f'interim/{match_id}')
        output_dir.mkdir(parents=True, exist_ok=True)

        for csv_file in csv_dir.glob("*tracking.csv"):
            process_tracking_data(csv_file, json_data, output_dir)


def process_tracking_data(csv_file, json_data, output_dir):
    game_id, start_time, _ = parse_time_range(Path(csv_file).stem)
    half = determine_half(start_time)
    if half is None:
        print(f"Skipping file {csv_file}: Could not determine half.")
        return

    if half == '1st' or half == '3rd':
        right_team_id = str(json_data[game_id]['right_team_id_1st_half'])
        left_team_id = str(json_data[game_id]['left_team_id_1st_half'])
    elif half == '2nd':
        right_team_id = json_data[game_id]['left_team_id_1st_half']
        left_team_id = json_data[game_id]['right_team_id_1st_half']
    print(half, left_team_id, right_team_id)

    # Load CSV data
    df = pd.read_csv(csv_file)

    # Define positions in the desired order
    position_order = ['GK', 'CB', 'RWB', 'RB', 'LWB', 'LB', 'CDM', 'CM', 'CAM', 'RW', 'LW', 'CF']

    # Create empty lists for rows
    rows = []

    # Group by match time
    for match_time, group in df.groupby('match_time'):
        row = {'match_time': match_time, 'ball_x': None, 'ball_y': None}

        left_players = group[group['team_id'] == left_team_id]
        right_players = group[group['team_id'] == right_team_id]

        # Add ball data
        ball_data = group[group['player_id'] == 'ball']
        if not ball_data.empty:
            row['ball_x'] = ball_data.iloc[0]['x']
            row['ball_y'] = ball_data.iloc[0]['y']

        # Process left team
        num_left_team_player = 1
        for position in position_order:
            position_players = left_players[left_players['position'] == position]
            if not position_players.empty:
                if len(position_players) == 1:
                    row[f'left_{num_left_team_player}_x'] = position_players.iloc[0]['x']
                    row[f'left_{num_left_team_player}_y'] = position_players.iloc[0]['y']
                    num_left_team_player += 1
                else:
                    position_players = position_players.reset_index(drop=True)
                    for i in range(len(position_players)):
                        player_x = position_players.loc[i, 'x']
                        player_y = position_players.loc[i, 'y']
                        row[f'left_{num_left_team_player}_x'] = player_x
                        row[f'left_{num_left_team_player}_y'] = player_y
                        num_left_team_player += 1

        # Process right team
        num_right_team_player = 1
        for position in position_order:
            position_players = right_players[right_players['position'] == position]
            if not position_players.empty:
                if len(position_players) == 1:
                    row[f'right_{num_right_team_player}_x'] = position_players.iloc[0]['x']
                    row[f'right_{num_right_team_player}_y'] = position_players.iloc[0]['y']
                    num_right_team_player += 1
                else:
                    position_players = position_players.reset_index(drop=True)
                    for i in range(len(position_players)):
                        player_x = position_players.loc[i, 'x']
                        player_y = position_players.loc[i, 'y']
                        row[f'right_{num_right_team_player}_x'] = player_x
                        row[f'right_{num_right_team_player}_y'] = player_y
                        num_right_team_player += 1

        # print(row)
        rows.append(row)

    # Convert rows to DataFrame
    output_df = pd.DataFrame(rows)

    # Save to CSV
    output_file = Path(output_dir) / f"{os.path.splitext(Path(csv_file).stem)[0]}_arranged.csv"
    output_df.to_csv(output_file, index=False)
    print(f"Processed file saved to {output_file}")


def parse_time_range(filename):
    match = re.search(r"(\d+)_\d{2}_\d{2}-\d{2}_\d{2}", filename)
    if match:
        game_id = match.group(1)
    match = re.search(r"\d+_(\d{2})_(\d{2})-(\d{2})_(\d{2})", filename)
    if match:
        start_min, start_sec, end_min, end_sec = map(int, match.groups())
        start_time = start_min * 60 + start_sec
        end_time = end_min * 60 + end_sec
        return game_id, start_time, end_time
    return None, None, None

def determine_half(start_time):
    if start_time <= 45 * 60:
        return '1st'
    elif 45 * 60 <= start_time <= 90 * 60:
        return '2nd'
    elif start_time >= 90 * 60:
        return '3rd'
    return None


if __name__ == "__main__":
    main()