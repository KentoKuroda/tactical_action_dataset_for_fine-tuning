import cv2
import json
import argparse
import numpy as np
import pandas as pd
from pathlib import Path


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--base_name', required=True) # 117093/117093_09_22-10_07, 128058/128058_03_51-05_07
    return parser.parse_args()


def main():

    args = parse_arguments()
    model = args.model
    base_name = args.base_name

    input_video_path = f"data/raw/visualization/{base_name}.mp4"
    output_video_path = f"data/interim/{base_name}_{model}_visualize_label_output.mp4"
    resulting_csv_path = f"data/interim/{base_name}_output_{model}.csv"
    resulting_df = pd.read_csv(resulting_csv_path)
    label_path = f"data/interim/{base_name}_annotation_combined.csv"
    label_df = pd.read_csv(label_path)

    visualize_output_label(input_video_path, output_video_path, resulting_df, label_df)


def visualize_output_label(input_video_path, output_video_path, resulting_df, label_df):
    cap = cv2.VideoCapture(input_video_path)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    frame_rate = cap.get(cv2.CAP_PROP_FPS)
    out = cv2.VideoWriter(output_video_path, fourcc, frame_rate, (int(cap.get(3)), int(cap.get(4))))

    columns_outputs = [col for col in resulting_df.columns if col.startswith("output_")]
    columns_labels = [col for col in label_df.columns if not col.startswith("output_")]

    outputs_1 = resulting_df[[col for col in columns_outputs if col.endswith("1")]].copy()
    outputs_2 = resulting_df[[col for col in columns_outputs if col.endswith("2")]].copy()
    labels_1 = label_df[[col for col in columns_labels if col.endswith("1")]].copy()
    labels_2 = label_df[[col for col in columns_labels if col.endswith("2")]].copy()

    outputs_1.columns = [col.replace("output_", "", 1).rsplit(" ", 1)[0] for col in outputs_1.columns]
    outputs_2.columns = [col.replace("output_", "", 1).rsplit(" ", 1)[0] for col in outputs_2.columns]
    labels_1.columns = [col.rsplit(" ", 1)[0] for col in labels_1.columns]
    labels_2.columns = [col.rsplit(" ", 1)[0] for col in labels_2.columns]

    default_font_color = (255, 255, 255)
    output_bar_color = (170, 218, 255)  # 予測バーの色
    label_bar_color = (255, 165, 0)      # ラベルバーの色

    bar_length = 200
    bar_height = 10
    font_scale = 1.0
    y_shift = 800
    x_1_position = 30
    x_2_position = 1600
    len_between_font_and_bar = 15
    len_between_label_and_output = 5
    tactics_list = ['Build up', 'Progression', 'Final third', 'Counter-attack', 'High press', 'Mid block', 'Low block', 'Counter-press', 'Recovery']

    frame_count = 0
    start_output_frame = int(frame_rate * 10)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        label_index = min(max(0, frame_count // 5), len(labels_1) - 1)
        label_row_1, label_row_2 = labels_1.iloc[label_index], labels_2.iloc[label_index]

        if frame_count >= start_output_frame:
            output_index = min(max(0, (frame_count - start_output_frame) // 5), len(outputs_1) - 1)
            output_row_1, output_row_2 = outputs_1.iloc[output_index], outputs_2.iloc[output_index]
        else:
            output_row_1 = output_row_2 = None

        for i, tactic in enumerate(tactics_list):
            y_position = frame.shape[0] - y_shift + i * 75
            
            for x_position, label_row, output_row in zip([x_1_position, x_2_position], [label_row_1, label_row_2], [output_row_1, output_row_2]):
                # --- 1. テキストの描画 (常に白) ---
                cv2.putText(frame, tactic, (x_position, y_position), cv2.FONT_HERSHEY_SIMPLEX, font_scale, default_font_color, 2)

                # --- 2. 教師ラベルバー (上段) の描画 ---
                label_val = max(0, label_row.get(tactic, 0))
                label_bar_width = int(label_val * bar_length)
                # y座標に「bar_height + 5」を足して一段下げて描画
                label_y_top = y_position + len_between_font_and_bar
                
                # ラベルバーの中身
                cv2.rectangle(frame, (x_position, label_y_top),
                                (x_position + label_bar_width, label_y_top + bar_height),
                                label_bar_color, -1)
                # ラベルバーの外枠
                cv2.rectangle(frame, (x_position, label_y_top),
                                (x_position + bar_length, label_y_top + bar_height),
                                (255, 255, 255), 1)

                # --- 3. 予測バー (下段) の描画 ---
                output_y_top = y_position + len_between_font_and_bar + bar_height + len_between_label_and_output
                # 予測データがある場合のみ中身を塗る
                if output_row is not None:
                    output_val = max(0, min(output_row.get(tactic, 0), 1.0))
                    output_bar_width = int(output_val * bar_length)
                    
                    cv2.rectangle(frame, (x_position, output_y_top),
                                    (x_position + output_bar_width, output_y_top + bar_height),
                                    output_bar_color, -1)
                
                # 予測バーの外枠 (常に表示)
                cv2.rectangle(frame, (x_position, output_y_top),
                                (x_position + bar_length, output_y_top + bar_height),
                                (255, 255, 255), 1)

        out.write(frame)
        frame_count += 1

    cap.release()
    out.release()


if __name__ == '__main__':
    main()