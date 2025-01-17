import json
import csv
from collections import defaultdict
import argparse


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--video_id')
    parser.add_argument('--team_id')
    return parser.parse_args()


def main():
    args = parse_arguments()
    video_ids = [str(video_id) for video_id in args.video_id.split(",")]
    team_id = args.team_id

    for video_id in video_ids:

        # input file
        input_files = []
        for i in range(1,5):
            input_files.append(f'annotation_data/{video_id}_{team_id}/{video_id}_{i}_{team_id}.json')
        
        # output file
        output_dir = f'annotation_data/{video_id}_{team_id}'

        generate_csv(input_files, output_dir)


def generate_csv(json_files, output_dir):
    video_data = defaultdict(list)

    # 定義済み列名の順序
    fixed_labels = [
        "Build up", "Progression", "Final third", "Counter-attack", 
        "High press", "Mid block", "Low block", "Counter-press", "Recovery"
    ]
    fieldnames = ["match time"] + fixed_labels

    # Read and group annotations by video
    for json_file in json_files:
        with open(json_file, "r") as f:
            data = json.load(f)
            for entry in data:
                key = (entry["game_id"], entry["start_video"], entry["end_video"])
                video_data[key].append(entry["annotations"])

    # Process each video
    for (game_id, start_video, end_video), annotations_list in video_data.items():
        start_seconds = parse_time_to_seconds(start_video)
        end_seconds = parse_time_to_seconds(end_video)
        duration = end_seconds - start_seconds

        # Initialize a dictionary for each second
        probabilities = {t: defaultdict(float) for t in range(start_seconds, end_seconds)}

        # Aggregate annotations
        for annotations in annotations_list:
            for annotation in annotations:
                label = annotation["label"]
                label_start = max(start_seconds, parse_time_to_seconds(annotation["start"]))
                label_end = min(end_seconds, parse_time_to_seconds(annotation["end"]))
                for t in range(label_start, label_end):
                    probabilities[t][label] += 1

        # Normalize probabilities
        for t in probabilities:
            for label in probabilities[t]:
                probabilities[t][label] /= 4

        # Write to CSV
        sanitized_start_video = sanitize_filename(start_video)
        sanitized_end_video = sanitize_filename(end_video)
        output_file = f"{output_dir}/{game_id}_{sanitized_start_video}-{sanitized_end_video}.csv"

        with open(output_file, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for t in range(start_seconds, end_seconds):
                row = {label: probabilities[t].get(label, 0.0) for label in fixed_labels}
                row["match time"] = format_seconds_to_time(t)
                writer.writerow(row)

        print(f"CSV file saved: {output_file}")



def parse_time_to_seconds(time_str):
    minutes, seconds = map(int, time_str.split(":"))
    return minutes * 60 + seconds


def format_seconds_to_time(seconds):
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02}:{seconds:02}"


def sanitize_filename(filename):
    return filename.replace(":", "_")


if __name__ == "__main__":
    main()
