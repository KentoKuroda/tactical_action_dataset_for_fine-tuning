import os
import json
import cv2
import argparse
import numpy as np
import pandas as pd
from pathlib import Path


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--match_ids', required=True, help="Comma-separated list of match IDs to process")
    return parser.parse_args()


def main():
    args = parse_arguments()
    match_ids = [str(match_id) for match_id in args.match_ids.split(",")]

    video_info_path = Path("raw/video/video_info.json")
    with open(video_info_path, 'r') as f:
        video_info = json.load(f)
    
    for match_id in match_ids:
        raw_dir = Path(f"raw/tracking/{match_id}")
        interim_dir = Path(f"interim/{match_id}")
        pitch_points = video_info.get(match_id, {}).get("pitch_points", [])
        
        tracking_files = sorted(raw_dir.rglob("*_tracking.csv"))
        for tracking_file in tracking_files:
            base_name = tracking_file.stem.replace("_tracking", "")
            video_file = interim_dir / f"{base_name}_video.mp4"
            
            if not video_file.exists():
                print(f"Warning: Video file not found {video_file}")
                continue
            
            tracking_data = pd.read_csv(tracking_file)
            visualize_pitch_coordinates(tracking_data, video_file, pitch_points)
            break


def visualize_pitch_coordinates(tracking_data, video_file, pitch_points):
    if len(pitch_points) < 4:
        print("Error: Not enough pitch points")
        return
    
    H = compute_homography(pitch_points)
    cap = cv2.VideoCapture(str(video_file))
    
    if not cap.isOpened():
        print("Error: Cannot open video")
        return
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    output_video_path = video_file.with_name(video_file.stem.replace("_video", "_coordinates_video") + ".mp4")
    out_video = cv2.VideoWriter(str(output_video_path), cv2.VideoWriter_fourcc(*'mp4v'), fps, (frame_width, frame_height))
    
    frame_idx = 6426
    frame_list = tracking_data['frame'].unique()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_idx in frame_list:
            tracking_frame = tracking_data[tracking_data['frame'] == frame_idx]
            player_positions = tracking_frame[['x', 'y']].values
            transformed_positions = transform_player_positions(player_positions, H)
            
            for pos in transformed_positions:
                x, y = int(pos[0]), int(pos[1])
                cv2.circle(frame, (x, y), 5, (0, 0, 255), -1)
        print(frame_idx)
        
        out_video.write(frame)
        frame_idx += 1
    
    cap.release()
    out_video.release()
    print(f"Video saved: {output_video_path}")


def compute_homography(pitch_points):
    real_points = np.array([p["real"] for p in pitch_points], dtype=np.float32)
    image_points = np.array([p["image"] for p in pitch_points], dtype=np.float32)
    H, _ = cv2.findHomography(real_points, image_points)
    return H


def transform_player_positions(player_positions, H):
    real_positions = np.array(player_positions, dtype=np.float32).reshape(-1, 1, 2)
    image_positions = cv2.perspectiveTransform(real_positions, H)
    return image_positions.reshape(-1, 2)


if __name__ == '__main__':
    main()