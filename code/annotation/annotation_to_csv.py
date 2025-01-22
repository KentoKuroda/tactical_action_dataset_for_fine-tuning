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
            input_files.append(f'raw/annotation/{video_id}_{team_id}/{video_id}_{i}_{team_id}.json')
        
        # output file
        output_dir = f'raw/annotation/{video_id}_{team_id}'

        generate_csv(input_files, output_dir)


def generate_csv(json_files, output_dir):
    video_data = defaultdict(list)

    # 定義済み列名の順序
    fixed_labels = ["Build up", "Progression", "Final third", "Counter-attack", "High press", "Mid block", "Low block", "Counter-press", "Recovery"]
    fieldnames = ["match_time"] + fixed_labels

    # Read and group annotations by video
    for json_file in json_files:
        with open(json_file, "r") as f:
            data = json.load(f)
            for entry in data:
                key = (entry["game_id"], entry["start_video"], entry["end_video"])
                video_data[key].append(entry["annotations"])

    # Process each video
    for (game_id, start_video, end_video), annotations_list in video_data.items():
        duration = end_video - start_video

        # Initialize a dictionary for each second
        probabilities = {t: defaultdict(float) for t in range(start_video, end_video)}

        # Aggregate annotations
        for annotations in annotations_list:
            for annotation in annotations:
                label = annotation["label"]
                label_start = max(start_video, annotation["start"])
                label_end = min(end_video, annotation["end"])
                for t in range(label_start, label_end):
                    probabilities[t][label] += 1

        # Normalize probabilities
        for t in probabilities:
            for label in probabilities[t]:
                probabilities[t][label] /= 4

        # Write to CSV
        sanitized_start_video = sanitize_filename(start_video)
        sanitized_end_video = sanitize_filename(end_video)
        output_file = f"{output_dir}/{game_id}_{sanitized_start_video}-{sanitized_end_video}_annotation.csv"

        with open(output_file, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for t in range(start_video, end_video):
                if t % 200 != 0:
                    continue
                row = {label: probabilities[t].get(label, 0.0) for label in fixed_labels}
                row["match_time"] = t
                writer.writerow(row)

        print(f"CSV file saved: {output_file}")


def sanitize_filename(time):
    time = time / 1000
    minutes = int(time / 60)
    seconds = int(time % 60)
    return f"{minutes:02}_{seconds:02}"


if __name__ == "__main__":
    main()
