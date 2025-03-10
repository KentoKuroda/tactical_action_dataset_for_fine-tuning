import cv2
import json
import argparse
import numpy as np
import pandas as pd
from pathlib import Path


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base_name', required=True) # 117093/117093_09_22-10_07, 128058/128058_03_51-05_07
    return parser.parse_args()


def main():

    args = parse_arguments()
    base_name = args.base_name

    input_video_path = f"raw/visualization/{base_name}.mp4"
    output_video_path = f"interim/{base_name}_visualize_label.mp4"
    label_path = f"interim/{base_name}_annotation_combined.csv"
    label_df = pd.read_csv(label_path)

    visualize_label(input_video_path, output_video_path, label_df)


# Calculate bar position based on value
def calculate_bar_position(value, bar_length):
    if value <= 0.1:
        return 0
    elif value >= 0.6:
        return bar_length
    else:
        return int((value - 0.1) / (0.6 - 0.1) * bar_length)


# New function to calculate position for orange bar
def calculate_orange_bar_position(value, bar_length):
    return int(value * bar_length)  # Scale directly from 0 to 1 range


def visualize_label(input_video_path, output_video_path, label_df):
    cap = cv2.VideoCapture(input_video_path)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    frame_rate = cap.get(cv2.CAP_PROP_FPS)
    out = cv2.VideoWriter(output_video_path, fourcc, frame_rate, (int(cap.get(3)), int(cap.get(4))))

    # 予測結果とラベルを分類
    columns_labels = [col for col in label_df.columns if not col.startswith("output_")]

    # ラベルと予測結果をチームごとに分ける
    labels_1 = label_df[[col for col in columns_labels if col.endswith("1")]].copy()
    labels_2 = label_df[[col for col in columns_labels if col.endswith("2")]].copy()

    # 列名からチーム名を削除
    labels_1.columns = [col.rsplit(" ", 1)[0] for col in labels_1.columns]
    labels_2.columns = [col.rsplit(" ", 1)[0] for col in labels_2.columns]

    # Colors: all labels and bars are skin-colored, top value label in red
    default_font_color = (255, 255, 255)  # White color
    output_bar_color = (170, 218, 255)  # Skin color
    label_bar_color = (255, 165, 0)  # orange color
    highlight_font_color = (0, 0, 255)  # Red for highest value label

    bar_length = 200  # Bar max length
    bar_height = 10   # Bar height
    font_scale = 1.0  # Fixed font size
    y_shift = 800     # Shift up by 150 pixels
    x_1_position = 30
    x_2_position = 1600
    len_between_font_and_bar = 15

    # Predefined order of labels
    tactics_list = ['Build up', 'Progression', 'Final third', 'Counter-attack', 'High press', 'Mid block', 'Low block', 'Counter-press', 'Recovery']

    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        index = frame_count // 5 # - int(frame_rate * 10 / 5)
        index = min(max(0, index), len(labels_1) - 1)
        label_row_1, label_row_2 = labels_1.iloc[index], labels_2.iloc[index]
        
        for i, tactic in enumerate(tactics_list):
            y_position = frame.shape[0] - y_shift + i * 75

            for x_position, label_row in zip([x_1_position, x_2_position], [label_row_1, label_row_2]):
                label = max(0, label_row.get(tactic, 0))
                text_color = highlight_font_color if label >= 0.75 else default_font_color
                
                cv2.putText(frame, tactic, (x_position, y_position), cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, 2)

                # ラベルバー描画
                label_bar_position = int(label * bar_length)
                cv2.rectangle(frame, (x_position, y_position + len_between_font_and_bar + bar_height + 5),
                                (x_position + label_bar_position, y_position + len_between_font_and_bar + bar_height + 5 + bar_height),
                                label_bar_color, -1)
                cv2.rectangle(frame, (x_position, y_position + len_between_font_and_bar + bar_height + 5),
                                (x_position + bar_length, y_position + len_between_font_and_bar + bar_height + 5 + bar_height),
                                (255, 255, 255), 1)

        out.write(frame)

        frame_count += 1
    
    cap.release()
    out.release()


if __name__ == '__main__':
    main()