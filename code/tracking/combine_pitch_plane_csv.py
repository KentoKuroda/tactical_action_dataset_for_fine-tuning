import pandas as pd
import glob
import argparse


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--match_id')
    return parser.parse_args()


def main():
    args = parse_arguments()
    match_ids = [str(match_id) for match_id in args.match_id.split(",")]

    for match_id in match_ids:
        # Specify the input folder and output file
        input_folder = f"raw/tracking/{match_id}"
        output_file = f"raw/tracking/{match_id}/{match_id}_pitch_plane_coordinates.csv"

        # Combine the CSV files
        combine_csv_files(input_folder, output_file)


def combine_csv_files(input_folder, output_file):
    """
    Combine all CSV files in a specified folder into one CSV file.

    Args:
        input_folder (str): Path to the folder containing input CSV files.
        output_file (str): Path to save the combined CSV file.

    Returns:
        None
    """
    # Get a list of all CSV files in the folder
    csv_files = glob.glob(f"{input_folder}/*.csv")
    if not csv_files:
        print("No CSV files found in the specified folder.")
        return

    # Read and combine all CSV files
    combined_df = pd.concat([pd.read_csv(file) for file in csv_files], ignore_index=True)

    # Save the combined data to a new CSV file
    combined_df.to_csv(output_file, index=False)
    print(f"Combined CSV saved to {output_file}")


if __name__ == "__main__":
    main()
