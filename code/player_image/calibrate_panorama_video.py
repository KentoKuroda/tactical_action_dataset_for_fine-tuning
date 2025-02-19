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
        raw_dir = Path(f"raw/video/{match_id}")
        video_file = raw_dir / f"{match_id}.mp4"
        if not video_file.exists():
            print(f"Warning: Video file not found {video_file}")
            continue

        pitch_points = video_info.get(match_id, {}).get("pitch_points", [])

        undistort_video(video_file, pitch_points)


def undistort_video(video_file, pitch_points):
    if len(pitch_points) < 10:  # 10点以上必要
        print("Error: Not enough pitch points for calibration")
        return
    
    # 3D にする (z=0 を追加)
    object_points = np.array([[p["real"] + [0]] for p in pitch_points], dtype=np.float32)
    image_points = np.array([[p["image"]] for p in pitch_points], dtype=np.float32)

    # フレームサイズ取得
    cap = cv2.VideoCapture(str(video_file))
    if cap.isOpened():
        frame_size = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    cap.release()
    
    if frame_size is None:
        print("Error: Cannot determine video frame size")
        return
    
    # カメラキャリブレーション (内部パラメータ推定)
    ret, camera_matrix, dist_coeffs, _, _ = cv2.calibrateCamera(
        [object_points], [image_points], frame_size, None, None
    )
    
    if not ret:
        print("Error: Camera calibration failed")
        return
    
    # 最適な新しいカメラ行列を取得
    new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(camera_matrix, dist_coeffs, frame_size, 1, frame_size)

    # 出力フレームサイズをROIに基づいて計算
    x, y, w, h = roi
    output_size = (w, h)  # 切り取られる領域を考慮

    # 歪み補正と保存
    cap = cv2.VideoCapture(str(video_file))
    fps = cap.get(cv2.CAP_PROP_FPS)
    output_video_path = video_file.with_name(video_file.stem.replace("117093", "117093_calibrated") + ".mp4")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out_video = cv2.VideoWriter(str(output_video_path), fourcc, fps, output_size)
    idx = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # 歪み補正
        undistorted_frame = cv2.undistort(frame, camera_matrix, dist_coeffs, None, new_camera_matrix)
        
        # ROI でトリミング
        undistorted_frame = undistorted_frame[y:y+h, x:x+w]

        # 出力動画に書き込む
        out_video.write(undistorted_frame)
        if idx % 3600 == 0:
            print(idx)
        idx += 1
    
    cap.release()
    out_video.release()
    print(f"Undistorted video saved: {output_video_path}")


if __name__ == '__main__':
    main()