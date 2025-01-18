import xml.etree.ElementTree as ET
import re
import os
import pandas as pd
import argparse


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--video_id')
    return parser.parse_args()


def main():
    args = parse_arguments()
    video_ids = [str(video_id) for video_id in args.video_id.split(",")]

    for video_id in video_ids:
        # トラッキングデータのcsvファイルがあるディレクトリ
        csv_file_dir = 'raw/tracking'

        # TXTファイルの読み込み
        txt_file = f'raw/videolist_{video_id}.txt'

        # 抽出したトラッキングデータが入るディレクトリ
        output_file_dir = 'raw/tracking'

        get_tracking_in_video(csv_file_dir, txt_file, output_file_dir)


def get_tracking_in_video(csv_file_dir, txt_file, output_file_dir):
    with open(txt_file, "r") as f:
        # 拡張子を省いたファイル名を取得
        video_files = [os.path.splitext(line.strip())[0] for line in f.readlines()]

    # 動画情報を解析
    videos = {}
    for video_file in video_files:
        game_id, start_time, end_time = parse_time_range(video_file)
        if start_time is not None and end_time is not None:
            videos[video_file] = (game_id, start_time * 1000, end_time * 1000)  # ミリ秒に変換

    # トラッキングデータを取得
    for video_file, (game_id, start_time, end_time) in videos.items():
        input_csv = os.path.join(csv_file_dir, f"{game_id}/{game_id}_pitch_plane_coordinates.csv")
        output_csv = os.path.join(output_file_dir, f"{game_id}/{video_file}_tracking.csv")

        if not os.path.exists(input_csv):
            print(f"Tracking data file not found: {input_csv}")
            continue

        # トラッキングデータをフィルタリングして保存
        tracking_data = pd.read_csv(input_csv)
        filtered_data = tracking_data[
            (tracking_data["match_time"] >= start_time) &
            (tracking_data["match_time"] <= end_time)
        ]
        filtered_data.to_csv(output_csv, index=False)
        print(f"Extracted tracking data saved to: {output_csv}")


def parse_time_range(filename):
    match = re.search(r"(\d+)_\d{2}_\d{2}-\d{2}_\d{2}", filename)
    if match:
        game_id = match.group(1)
    match = re.search(r"\d+_(\d{2})_(\d{2})-(\d{2})_(\d{2})", filename)
    if match:
        start_min, start_sec, end_min, end_sec = map(int, match.groups())
        start_time = start_min * 60 + start_sec
        end_time = end_min * 60 + end_sec
        return game_id, start_time, end_time
    return None, None, None


if __name__ == "__main__":
    main()
