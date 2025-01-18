import pandas as pd
import argparse
from pathlib import Path
import os


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--video_ids', type=str, required=True, help="Comma-separated list of video IDs")
    return parser.parse_args()


def main():
    args = parse_arguments()
    video_ids = args.video_ids.split(",")
    for video_id in video_ids:
        left_csv_dir = Path(f"raw/annotation/{video_id}_Left")
        right_csv_dir = Path(f"raw/annotation/{video_id}_Right")
        combine_csv_files(left_csv_dir, right_csv_dir)


def combine_csv_files(left_csv_dir: Path, right_csv_dir: Path):
    # Check if the directories exist
    if not left_csv_dir.exists():
        print(f"Left CSV directory not found: {left_csv_dir}")
        return
    if not right_csv_dir.exists():
        print(f"Right CSV directory not found: {right_csv_dir}")
        return

    # Process all CSV files in the left directory
    for left_csv_file in left_csv_dir.glob("*.csv"):
        # Find the corresponding right CSV file
        right_csv_file = right_csv_dir / left_csv_file.name
        if not right_csv_file.exists():
            print(f"Matching Right CSV not found for: {left_csv_file.name}")
            continue

        # Parse game ID from the file name (assuming a function parse_time_range exists)
        game_id = left_csv_file.stem.split('_')[0]  # Example: Extract game_id from "gameid_xx.csv"
        output_dir = Path(f"interim/{game_id}")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Read the CSV files
        left_df = pd.read_csv(left_csv_file)
        right_df = pd.read_csv(right_csv_file)

        # Rename columns for Left and Right
        left_df.columns = [f"{col} 1" if col != "match time" else col for col in left_df.columns]
        right_df.columns = [f"{col} 2" if col != "match time" else col for col in right_df.columns]

        # Merge the dataframes on "match time"
        combined_df = pd.merge(left_df, right_df, on="match time", how="outer")

        # Sort by match time (if necessary)
        combined_df = combined_df.sort_values(by="match time")

        # Save the combined dataframe to a new CSV file
        output_file = output_dir / f"{os.path.splitext(Path(left_csv_file).stem)[0]}_annotation_combined.csv"
        combined_df.to_csv(output_file, index=False)
        print(f"Combined CSV saved to {output_file}")


if __name__ == "__main__":
    main()