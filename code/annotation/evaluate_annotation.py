import pandas as pd
from pathlib import Path
import argparse

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--match_ids', required=True, help="Comma-separated list of match IDs to process")
    return parser.parse_args()


def main():
    args = parse_arguments()
    match_ids = [str(match_id) for match_id in args.match_ids.split(",")]
    output_file = "raw/annotation/evaluate_annotation.csv"

    all_results = []

    for match_id in match_ids:
        # Directory containing the CSV files
        csv_directory = f"interim/{match_id}"

        # Evaluate the tactics
        try:
            match_results = evaluate_tactics(csv_directory)
            all_results.append(match_results)
        except Exception as e:
            print(f"Error processing match {match_id}: {e}")

    # Combine all match results into a single DataFrame
    if all_results:
        combined_results = pd.concat(all_results, ignore_index=True)
        final_summary = calculate_overall_summary(combined_results)
        final_summary.to_csv(output_file, index=False)
        print(f"Summary saved to {output_file}")
    else:
        print("No results to process.")


def evaluate_tactics(csv_dir):
    """
    Evaluate the proportion of each value (0.0, 0.25, 0.5, 0.75, 1.0) for all tactics across multiple CSV files.

    Args:
        csv_dir (str): Directory containing the CSV files to evaluate.

    Returns:
        pd.DataFrame: Raw results for all rows in the evaluated files.
    """
    csv_dir = Path(csv_dir)
    if not csv_dir.exists():
        raise FileNotFoundError(f"The directory {csv_dir} does not exist.")
    
    csv_files = list(csv_dir.glob("*annotation_combined.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in the directory {csv_dir}.")
    
    combined_data = []

    for csv_file in csv_files:
        print(f"Processing file: {csv_file.name}")
        df = pd.read_csv(csv_file)

        # Combine columns with '1' and '2' for the same tactic
        tactics = set(col[:-2] for col in df.columns if col.endswith(' 1'))
        for tactic in tactics:
            col_1 = f"{tactic} 1"
            col_2 = f"{tactic} 2"
            combined_column = df[col_1].fillna(0) + df[col_2].fillna(0)
            combined_data.append(pd.DataFrame({
                "Tactic": tactic,
                "Value": combined_column
            }))
    
    # Combine all rows into a single DataFrame
    return pd.concat(combined_data, ignore_index=True)


def calculate_overall_summary(results):
    """
    Calculate the overall summary of proportions for all tactics.

    Args:
        results (pd.DataFrame): DataFrame containing "Tactic" and "Value" columns.

    Returns:
        pd.DataFrame: Summary of proportions for all tactics.
    """
    summary = []
    total_rows = len(results)
    
    for tactic, group in results.groupby("Tactic"):
        value_counts = group["Value"].value_counts(normalize=True).to_dict()
        summary.append({
            "Tactic": tactic,
            "0.0": value_counts.get(0.0, 0),
            "0.25": value_counts.get(0.25, 0),
            "0.5": value_counts.get(0.5, 0),
            "0.75": value_counts.get(0.75, 0),
            "1.0": value_counts.get(1.0, 0)
        })

    return pd.DataFrame(summary)


if __name__ == "__main__":
    main()
