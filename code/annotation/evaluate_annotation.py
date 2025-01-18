import pandas as pd
from pathlib import Path
import argparse
from collections import Counter


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--match_ids', required=True, help="Comma-separated list of match IDs to process")
    return parser.parse_args()


def main():
    args = parse_arguments()
    match_ids = [str(match_id) for match_id in args.match_ids.split(",")]
    output_file = "raw/annotation/evaluate_annotation.csv"

    all_tactic_results_1 = []
    all_tactic_results_2 = []
    all_pattern_results_1 = Counter()
    all_pattern_results_2 = Counter()

    for match_id in match_ids:
        csv_directory = f"interim/{match_id}"

        try:
            results_1, patterns_1, results_2, patterns_2 = evaluate_tactics(csv_directory)
            all_tactic_results_1.append(results_1)
            all_tactic_results_2.append(results_2)
            all_pattern_results_1.update(patterns_1)
            all_pattern_results_2.update(patterns_2)
        except Exception as e:
            print(f"Error processing match {match_id}: {e}")

    if all_tactic_results_1 and all_tactic_results_2:
        # Combine tactic results
        combined_tactics_1 = pd.concat(all_tactic_results_1, ignore_index=True)
        combined_tactics_2 = pd.concat(all_tactic_results_2, ignore_index=True)
        final_tactic_summary = calculate_overall_summary(pd.concat([combined_tactics_1, combined_tactics_2]))

        # Process pattern results
        total_patterns_1 = sum(all_pattern_results_1.values())
        total_patterns_2 = sum(all_pattern_results_2.values())
        total_patterns = total_patterns_1 + total_patterns_2

        pattern_summary = {
            "Pattern": list(set(all_pattern_results_1.keys()) | set(all_pattern_results_2.keys())),
            "Proportion": [
                (all_pattern_results_1.get(pattern, 0) + all_pattern_results_2.get(pattern, 0)) / total_patterns
                for pattern in set(all_pattern_results_1.keys()) | set(all_pattern_results_2.keys())
            ]
        }
        pattern_summary_df = pd.DataFrame(pattern_summary)

        # Save results
        final_tactic_summary.to_csv(output_file, index=False)
        print(f"Tactic summary saved to {output_file}")

        pattern_output_file = "raw/annotation/pattern_summary.csv"
        pattern_summary_df.to_csv(pattern_output_file, index=False)
        print(f"Pattern summary saved to {pattern_output_file}")
    else:
        print("No results to process.")


def evaluate_tactics(csv_dir):
    """
    Evaluate the tactics and patterns across multiple CSV files.

    Args:
        csv_dir (str): Directory containing the CSV files to evaluate.

    Returns:
        tuple: DataFrames and pattern counts for tactics 1 and 2.
    """
    csv_dir = Path(csv_dir)
    if not csv_dir.exists():
        raise FileNotFoundError(f"The directory {csv_dir} does not exist.")
    
    csv_files = list(csv_dir.glob("*annotation_combined.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in the directory {csv_dir}.")
    
    combined_data_1 = []
    combined_data_2 = []
    pattern_counter_1 = Counter()
    pattern_counter_2 = Counter()

    for csv_file in csv_files:
        print(f"Processing file: {csv_file.name}")
        df = pd.read_csv(csv_file)

        # Process tactics 1
        tactics_1 = [col for col in df.columns if col.endswith(' 1')]
        df_1 = df[tactics_1].fillna(0)
        combined_data_1.append(
            pd.melt(df_1, var_name="Tactic", value_name="Value")
        )
        for _, row in df_1.iterrows():
            pattern = classify_pattern(row)
            pattern_counter_1[pattern] += 1

        # Process tactics 2
        tactics_2 = [col for col in df.columns if col.endswith(' 2')]
        df_2 = df[tactics_2].fillna(0)
        combined_data_2.append(
            pd.melt(df_2, var_name="Tactic", value_name="Value")
        )
        for _, row in df_2.iterrows():
            pattern = classify_pattern(row)
            pattern_counter_2[pattern] += 1

    return (
        pd.concat(combined_data_1, ignore_index=True),
        pattern_counter_1,
        pd.concat(combined_data_2, ignore_index=True),
        pattern_counter_2
    )


def classify_pattern(row):
    """
    Classify a row into a specific pattern.

    Args:
        row (pd.Series): Row of values for tactics.

    Returns:
        str: Pattern description.
    """
    counts = Counter(row)

    # 4 annotator
    if counts[0.25] == 4:
        return "4 Four 0.25"
    elif counts[0.5] == 1 and counts[0.25] == 2:
        return "4 One 0.5 Two 0.25"
    elif counts[0.75] == 1 and counts[0.25] == 1:
        return "4 One 0.75 One 0.25"
    elif counts[1.0] == 1:
        return "4 One 1.0"
    
    # 3 annotator
    elif counts[0.25] == 3:
        return "3 Three 0.25"
    elif counts[0.5] == 1 and counts[0.25] == 1:
        return "3 One 0.5 One 0.25"
    elif counts[0.75] == 1:
        return "3 One 0.75"
    
    # 2 annotator
    elif counts[0.25] == 2:
        return "2 Two 0.25"
    elif counts[0.5] == 1:
        return "2 One 0.5"
    
    # 1 annotator
    elif counts[0.25] == 1:
        return "1 One 0.25"
    
    # 0 annotator
    else:
        return "0 All 0.0"


def calculate_overall_summary(results):
    """
    Calculate the overall summary of proportions for all tactics, merging Tactic 1 and 2,
    and excluding 0.0 from the proportion calculation.

    Args:
        results (pd.DataFrame): DataFrame containing "Tactic" and "Value" columns.

    Returns:
        pd.DataFrame: Summary of proportions for all tactics, combined by tactic name,
                    with 0.0 excluded from the proportions.
    """
    # Remove " 1" or " 2" suffix from Tactic names
    results["Tactic"] = results["Tactic"].str.replace(r" \d$", "", regex=True)

    # Group by tactic name and calculate proportions excluding 0.0
    summary = []
    for tactic, group in results.groupby("Tactic"):
        # Count the occurrences of each value
        value_counts = group["Value"].value_counts().to_dict()
        
        # Exclude 0.0 and calculate the total occurrences of 0.25, 0.5, 0.75, 1.0
        filtered_counts = {k: v for k, v in value_counts.items() if k > 0.0}
        total_filtered = sum(filtered_counts.values())
        
        # Calculate proportions for non-zero values
        summary.append({
            "Tactic": tactic,
            "0.25": filtered_counts.get(0.25, 0) / total_filtered if total_filtered > 0 else 0,
            "0.5": filtered_counts.get(0.5, 0) / total_filtered if total_filtered > 0 else 0,
            "0.75": filtered_counts.get(0.75, 0) / total_filtered if total_filtered > 0 else 0,
            "1.0": filtered_counts.get(1.0, 0) / total_filtered if total_filtered > 0 else 0,
        })

    return pd.DataFrame(summary)


if __name__ == "__main__":
    main()