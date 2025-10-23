import os
import json
import re
import argparse
import subprocess


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--match_ids', required=True, help="Comma-separated list of match IDs to process")
    return parser.parse_args()


def main():
    args = parse_arguments()
    match_ids = [str(match_id) for match_id in args.match_ids.split(",")]

    for match_id in match_ids:
        # input
        panorama_video = f"raw/video/{match_id}/{match_id}.mp4" # _calibrated
        video_list = f"raw/video/{match_id}/{match_id}_videolist.txt"
        video_info = "raw/video/video_info.json"

        # output
        output_video_dir = f"interim/{match_id}"

        get_sequence_video(panorama_video, video_list, video_info, output_video_dir)


def get_sequence_video(panorama_video, video_list, video_info, output_video_dir):
    # 出力ディレクトリの作成
    os.makedirs(output_video_dir, exist_ok=True)
    
    # ビデオ情報の読み込み
    with open(video_info, 'r') as f:
        video_data = json.load(f)
    
    match_id = os.path.basename(video_list).split('_')[0]
    if match_id not in video_data:
        print(f"Match ID {match_id} not found in video info.")
        return
    
    match_info = video_data[match_id]
    first_half_start = match_info["1st_half_start"]
    second_half_start = match_info["2nd_half_start"]
    
    # ビデオリストの読み込み
    with open(video_list, 'r') as f:
        video_files = f.read().splitlines()
    
    for video_name in video_files:
        print(video_name)
        match = re.match(r"\d+_(\d+)_(\d+)-(\d+)_(\d+).mp4", video_name)
        if not match:
            print(f"Skipping invalid file name format: {video_name}")
            continue
        
        start_min, start_sec, end_min, end_sec = map(int, match.groups())
        start_time = start_min * 60 + start_sec  # 試合時間での開始秒数
        end_time = end_min * 60 + end_sec  # 試合時間での終了秒数
        
        # 前半か後半かを判定し、パノラマ映像の開始時間を算出
        if start_time < 2700:
            real_start_time = first_half_start + (start_time * 1000)
            real_end_time = first_half_start + (end_time * 1000)
        else:
            real_start_time = second_half_start + ((start_time - 2700) * 1000)
            real_end_time = second_half_start + ((end_time - 2700) * 1000)
        
        output_video_path = os.path.join(output_video_dir, video_name) #.replace('.mp4', '_video.mp4'))
        
        # ffmpegを使用して映像を切り取る
        cmd = [
            "ffmpeg", "-i", panorama_video,
            "-ss", str(real_start_time / 1000),
            "-to", str(real_end_time / 1000),
            "-c", "copy", output_video_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Saved: {output_video_path}")



if __name__ == '__main__':
    main()