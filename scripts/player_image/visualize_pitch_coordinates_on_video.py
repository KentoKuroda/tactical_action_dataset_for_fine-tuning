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
        calibrated_pitch_points = video_info.get(match_id, {}).get("calibrated_pitch_points", [])

        pitch_points = video_info.get(match_id, {}).get("pitch_points", [])
        object_points = np.array([[p["real"] + [0]] for p in pitch_points], dtype=np.float32)
        image_points = np.array([[p["image"]] for p in pitch_points], dtype=np.float32)
        
        tracking_files = sorted(raw_dir.rglob("*_tracking.csv"))
        for tracking_file in tracking_files:
            base_name = tracking_file.stem.replace("_tracking", "")

            calibrated_video_file = interim_dir / f"{base_name}_video.mp4"
            video_file = interim_dir / f"{base_name}.mp4"

            # フレームサイズ取得
            cap = cv2.VideoCapture(str(video_file))
            if cap.isOpened():
                frame_size = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
            cap.release()
            # カメラキャリブレーション (内部パラメータ推定)
            ret, camera_matrix, dist_coeffs, _, _ = cv2.calibrateCamera(
                [object_points], [image_points], frame_size, None, None
            )

            if not calibrated_video_file.exists():
                print(f"Warning: Video file not found {calibrated_video_file}")
                continue
            
            tracking_data = pd.read_csv(tracking_file)
            visualize_pitch_coordinates(tracking_data, calibrated_video_file, video_file, calibrated_pitch_points, camera_matrix, dist_coeffs)
            break


def visualize_pitch_coordinates(tracking_data, calibrated_video_file, video_file, calibrated_pitch_points, camera_matrix, dist_coeffs):
    if len(calibrated_pitch_points) < 4:
        print("Error: Not enough pitch points")
        return
    
    H = compute_homography(calibrated_pitch_points)
    print(H)
    cap = cv2.VideoCapture(str(video_file))
    
    if not cap.isOpened():
        print("Error: Cannot open video")
        return
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    output_video_path = video_file.with_stem(video_file.stem + "_coordinates_origin_video")
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
            # 歪み補正前の座標を求める
            original_positions = transform_to_distorted_positions(transformed_positions, camera_matrix, dist_coeffs)
            
            for pos in original_positions:
                x, y = int(pos[0]), int(pos[1])
                cv2.circle(frame, (x, y), 5, (0, 0, 255), -1)
        # print(frame_idx)
        
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


def transform_to_distorted_positions(undistorted_positions, camera_matrix, dist_coeffs):
    """
    歪み補正後の画像座標を、歪み補正前の画像座標に変換する
    :param undistorted_positions: np.array, shape(N,2), 歪み補正後の座標
    :param camera_matrix: 内部カメラパラメータ
    :param dist_coeffs: レンズの歪み係数
    :return: np.array, shape(N,2), 歪み補正前の座標
    """
    # 座標を適切な形に変換 (N,2) → (N,1,2)
    undistorted_positions = np.expand_dims(undistorted_positions, axis=1).astype(np.float32)

    # `cv2.undistortPoints` は正規化されたカメラ座標を出力するので、カメラ行列を適用
    normalized_points = cv2.undistortPoints(undistorted_positions, camera_matrix, dist_coeffs)
    
    # 正規化座標を元の画像座標に変換するためにカメラ行列を適用
    distorted_image_positions = cv2.convertPointsToHomogeneous(normalized_points)[:, 0, :2]
    distorted_image_positions = (distorted_image_positions @ camera_matrix[:2, :2].T) + camera_matrix[:2, 2]

    return distorted_image_positions



if __name__ == '__main__':
    main()