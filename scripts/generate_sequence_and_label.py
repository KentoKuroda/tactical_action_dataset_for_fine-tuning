import os
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import argparse


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--match_ids', required=True, help="Comma-separated list of match IDs to process")
    parser.add_argument('--classification', action='store_true',help="If set, convert labels to 0/1 for classification mode")
    parser.add_argument('--team1_only', action='store_true', help="If set, output labels for only Team 1")
    return parser.parse_args()


def main():
    args = parse_arguments()
    match_ids = [str(match_id) for match_id in args.match_ids.split(",")]

    # Output numpy file
    # 117093_09_22-10_07_, 128058_03_51-05_07_
    if args.classification:
        output_sequence_numpy = "data/sequence_label/sequence_np_including_future_classification.npy"
        output_label_numpy = "data/sequence_label/label_np_including_future_classification.npy"
    elif args.team1_only:
        output_sequence_numpy = "data/sequence_label/sequence_np_including_future_team1_only.npy"
        output_label_numpy = "data/sequence_label/label_np_including_future_team1_only.npy"
    else:
        output_sequence_numpy = "data/sequence_label/sequence_np_including_future.npy"
        output_label_numpy = "data/sequence_label/label_np_including_future.npy"

    all_sequences_list = []
    all_labels_list = []

    # チームごとの戦術出現回数カウント
    total_team1_counts = np.zeros(9, dtype=int)
    total_team2_counts = np.zeros(9, dtype=int)

    for match_id in match_ids:
        # Directory containing tracking and annotation files
        input_directory = f"data/interim/{match_id}"

        sequences, labels, team1_counts, team2_counts = process_data(input_directory, classification_mode=args.classification, team1_only_mode=args.team1_only)

        total_team1_counts += team1_counts
        total_team2_counts += team2_counts

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
        print(final_sequences.shape)
        print(final_labels.shape)
        print(f"Final sequences saved to {output_sequence_numpy}")
        print(f"Final labels saved to {output_label_numpy}")
    else:
        print("No valid data to save.")
    
    # 分類モードのときのみ戦術出現回数を表示
    if args.classification:
        tactics = ["Build up", "Progression", "Final third", "Counter-attack",
                    "High press", "Mid block", "Low block", "Counter-press", "Recovery"]
        print("\n=== 戦術が1（過半数）になった回数 ===")
        print("Team 1:")
        for t, c in zip(tactics, total_team1_counts):
            print(f"{t}: {c}")
        print("\nTeam 2:")
        for t, c in zip(tactics, total_team2_counts):
            print(f"{t}: {c}")


def process_data(directory, classification_mode=False, team1_only_mode=False):
    sequences_list = []
    labels_list = []

    team1_counts = np.zeros(9, dtype=int)
    team2_counts = np.zeros(9, dtype=int)

    # Get all annotation files
    annotation_files = sorted(Path(directory).rglob("*_annotation_combined.csv"))

    for annotation_file in annotation_files:
        # Find the corresponding tracking file
        base_name = annotation_file.stem.replace("_annotation_combined", "")
        tracking_file = annotation_file.parent / f"{base_name}_tracking_arranged.csv"

        # 117093_09_22-10_07, 128058_03_51-05_07
        # if base_name == '118575_47_56-49_49': 
        #     print(base_name)
        # else:
        #     continue

        if base_name == '117093_09_22-10_07' or base_name == '128058_03_51-05_07' or base_name == '118575_47_56-49_49':
            continue

        if not tracking_file.exists():
            print(f"Tracking file not found for {annotation_file.name}. Skipping.")
            continue

        print(f"Processing {tracking_file.name} and {annotation_file.name}...")

        # Load tracking and annotation data
        tracking_data = pd.read_csv(tracking_file)
        annotation_data = pd.read_csv(annotation_file)

        # === モード別処理 ===
        if classification_mode:
            annotation_data, team1_c, team2_c = convert_labels(annotation_data)
            team1_counts += team1_c
            team2_counts += team2_c

        elif team1_only_mode:
            annotation_data = select_team1_labels(annotation_data)

        sequences, labels = create_sequences(tracking_data, annotation_data)

        # --- 分類モードなら全0ラベルを除外 ---
        if classification_mode:
            valid_indices = np.any(labels > 0, axis=1)
            sequences = sequences[valid_indices]
            labels = labels[valid_indices]

        print(base_name, sequences.shape, labels.shape)

        sequences_list.append(sequences)
        labels_list.append(labels)

    if sequences_list and labels_list:
        # Combine all sequences and labels
        all_sequences = np.concatenate(sequences_list, axis=0)
        all_labels = np.concatenate(labels_list, axis=0)
        return all_sequences, all_labels, team1_counts, team2_counts
    else:
        return np.array([]), np.array([]), team1_counts, team2_counts


def convert_labels(annotation_data):
    """ アノテーションCSVを0/1ラベルに変換 """
    label_values = annotation_data.iloc[:, 1:].copy()

    # 0.75以上を1、それ以外は0
    binarized = (label_values >= 0.75).astype(int)

    # 出現回数カウント
    team1_counts = binarized.iloc[:, :9].sum().values
    team2_counts = binarized.iloc[:, 9:].sum().values

    # match_timeを戻して再構築
    binarized_df = pd.concat([annotation_data.iloc[:, [0]], binarized], axis=1)
    return binarized_df, team1_counts, team2_counts


def select_team1_labels(annotation_data):
    """ チーム1の列（列名が*_1で終わる）だけを残す """
    cols = [c for c in annotation_data.columns if c == "match_time" or c.endswith("1")]
    filtered = annotation_data[cols].copy()
    print(f"Team1-only columns selected: {len(cols)-1} columns")
    return filtered


def create_sequences(tracking_data, annotation_data, sequence_length=20, fps=5):
    # 1秒間のフレーム数 (デフォルト25fpsから計算)
    frame_step = 25 // fps
    original_frames = 25 * sequence_length - 4
    num_frames = sequence_length * fps  # 20秒 × 5fps = 100フレーム
    sequence_data = []
    label_data = []

    for idx in range(0, len(tracking_data), frame_step):
        current_time = tracking_data.iloc[idx]['match_time']
        # current_time を 40 の倍数に補正
        current_time = round(current_time / 40) * 40

        start_time = current_time - 10 * 1000  # ミリ秒単位
        end_time = current_time + 10 * 1000

        # データを取得 (不足時はゼロ埋め)
        past_data = tracking_data[(tracking_data['match_time'] >= start_time) & (tracking_data['match_time'] <= end_time)]
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
