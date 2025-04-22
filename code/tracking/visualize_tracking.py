import cv2
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.signal import savgol_filter


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base_name', required=True)
    return parser.parse_args()


def main():
    args = parse_arguments()
    base_name = args.base_name

    input_tracking_path = f"interim/{base_name}_tracking_arranged.csv"
    output_video_path = f"interim/{base_name}_visualize_tracking.mp4"

    df = pd.read_csv(input_tracking_path)
    visualize_tracking(df, output_video_path)


def visualize_tracking(df, output_video_path):
    fps = 25
    frame_width, frame_height = 1050, 680
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_out = cv2.VideoWriter(output_video_path, fourcc, fps, (frame_width, frame_height))

    # Savitzky-Golay フィルターで平滑化（全データを一括で処理）
    cols_to_smooth = df.columns[1:]
    data_len = len(df)
    window_length = min(11, data_len if data_len % 2 != 0 else data_len - 1)  # 偶数なら1引く
    if window_length > 2:
        df[cols_to_smooth] = savgol_filter(df[cols_to_smooth], window_length, 3, axis=0)

    for i in range(len(df)):
        frame = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
        frame[:] = (255, 255, 255)
        soccer_court(frame, frame_width, frame_height)

        # 座標変換（x: -52.5~52.5, y: -34~34 → 画像座標系）
        def transform_coords(x, y):
            x_img = int((x + 52.5) / 105 * frame_width)
            y_img = int((y + 34) / 68 * frame_height)
            return x_img, y_img

        # ボール
        ball_x, ball_y = transform_coords(df.loc[i, 'ball_x'], df.loc[i, 'ball_y'])
        cv2.circle(frame, (ball_x, ball_y), 8, (0, 0, 0), -1)

        # レフトチーム
        for j in range(1, 12):
            x, y = transform_coords(df.iloc[i, 1 + 2 * j], df.iloc[i, 2 + 2 * j])
            cv2.circle(frame, (x, y), 10, (180, 105, 255), -1)  # ピンク

        # ライトチーム
        for j in range(1, 12):
            x, y = transform_coords(df.iloc[i, 23 + 2 * j], df.iloc[i, 24 + 2 * j])
            cv2.circle(frame, (x, y), 10, (255, 255, 0), -1)  # 水色

        video_out.write(frame)

    video_out.release()


def soccer_court(frame, width, height):
    line_color = (0, 0, 0)
    thickness = 2
    mid_x, mid_y = width // 2, height // 2

    # センターライン
    cv2.line(frame, (mid_x, 0), (mid_x, height), line_color, thickness)

    # センターサークル
    cv2.circle(frame, (mid_x, mid_y), int(70), line_color, thickness)

    # ペナルティエリア
    for side in [0, width]:
        p_x = side if side == 0 else width - 180
        cv2.rectangle(frame, (p_x, mid_y - 150), (p_x + 180, mid_y + 150), line_color, thickness)

    # ゴール
    for side in [0, width]:
        g_x = side if side == 0 else width - 30
        cv2.rectangle(frame, (g_x, mid_y - 40), (g_x + 30, mid_y + 40), line_color, thickness)


if __name__ == '__main__':
    main()
