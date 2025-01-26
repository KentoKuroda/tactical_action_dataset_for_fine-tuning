import os
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import argparse


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--match_ids', required=True, help="Comma-separated list of match IDs to process")
    return parser.parse_args()


def main():
    args = parse_arguments()
    match_ids = [str(match_id) for match_id in args.match_ids.split(",")]

    # Output numpy file
    output_sequence_numpy = "data/sequence_np.npy"
    output_label_numpy = "data/label_np.npy"

    all_sequences_list = []
    all_labels_list = []

    for match_id in match_ids:
        # Directory containing tracking and annotation files
        input_directory = f"interim/{match_id}"

        sequences, labels = process_data(input_directory)
        if sequences.size > 0 and labels.size > 0:
            all_sequences_list.append(sequences)
            all_labels_list.append(labels)

    if all_sequences_list and all_labels_list:
        # Combine all sequences and labels across matches
        final_sequences = np.concatenate(all_sequences_list, axis=0)
        final_labels = np.concatenate(all_labels_list, axis=0)

        # Save combined sequences and labels
        np.save(output_sequence_numpy, final_sequences)
        np.save(output_label_numpy, final_labels)
        print(f"Final sequences saved to {output_sequence_numpy}")
        print(f"Final labels saved to {output_label_numpy}")
    else:
        print("No valid data to save.")


def process_data(directory):
    sequences_list = []
    labels_list = []

    # Get all annotation files
    annotation_files = sorted(Path(directory).rglob("*_annotation_combined.csv"))
    for annotation_file in annotation_files:
        # Find the corresponding tracking file
        base_name = annotation_file.stem.replace("_annotation_combined", "")
        tracking_file = annotation_file.parent / f"{base_name}_tracking_arranged.csv"

        if not tracking_file.exists():
            print(f"Tracking file not found for {annotation_file.name}. Skipping.")
            continue

        print(f"Processing {tracking_file.name} and {annotation_file.name}...")
        # Load tracking and annotation data
        tracking_data = pd.read_csv(tracking_file)
        annotation_data = pd.read_csv(annotation_file)

        # Create sequences and labels
        sequences, labels = create_sequences(tracking_data, annotation_data)
        print(base_name, sequences.shape, labels.shape)
        sequences_list.append(sequences)
        labels_list.append(labels)

    if sequences_list and labels_list:
        # Combine all sequences and labels
        all_sequences = np.concatenate(sequences_list, axis=0)
        all_labels = np.concatenate(labels_list, axis=0)
        return all_sequences, all_labels
    else:
        return np.array([]), np.array([])


def create_sequences(tracking_data, annotation_data, sequence_length=20, fps=5):
    # 1秒間のフレーム数 (デフォルト25fpsから計算)
    frame_step = 25 // fps
    original_frames = 25 * sequence_length - 4
    num_frames = sequence_length * fps  # 20秒 × 5fps = 100フレーム
    sequence_data = []
    label_data = []

    for idx in range(25 * 10, (len(tracking_data) - 25), frame_step):
        current_time = tracking_data.iloc[idx]['match_time']
        start_time = current_time - sequence_length * 1000  # ミリ秒単位

        # 過去20秒間のデータを取得 (不足時はゼロ埋め)
        past_data = tracking_data[(tracking_data['match_time'] >= start_time) & (tracking_data['match_time'] <= current_time)]
        if len(past_data) < original_frames:
            padding = pd.DataFrame(0, index=np.arange(original_frames - len(past_data)), columns=tracking_data.columns)
            past_data = pd.concat([padding, past_data])

        # 等間隔でサンプリング (現在のフレームを含める)
        sampled_indices = np.linspace(-original_frames, -1, num=num_frames, dtype=int)
        sampled_data = past_data.iloc[sampled_indices, 1:].values  # match_timeを除外

        # NaNを含むシーケンスをスキップ
        if np.isnan(sampled_data).any():
            continue

        sequence_data.append(sampled_data)

        # 対応するラベルデータを取得
        label = annotation_data[annotation_data['match_time'] == current_time].iloc[:, 1:].values  # match_timeを除外
        if len(label) > 0:
            label_data.append(label[0])
        else:
            label_data.append(np.zeros(annotation_data.shape[1] - 1))

    return np.array(sequence_data), np.array(label_data)


if __name__ == "__main__":
    main()
