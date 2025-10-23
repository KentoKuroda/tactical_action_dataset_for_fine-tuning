import argparse
import subprocess
import pickle
import os
import io
import json
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.http import MediaFileUpload
import googleapiclient.errors

# Google Drive APIのスコープ
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


def main():

    creds = authenticate()
    service = build('drive', 'v3', credentials=creds)

    # JSONファイルの読み込み
    json_file = "video_info.json"
    with open(json_file, "r") as file:
        tasks = json.load(file)

    for task in tasks:
        folder_id = task["folder_id"]
        start_time_1st_half = task["1st_half_start"] / 1000  # ミリ秒を秒に変換
        start_time_2nd_half = task["end"] / 1000

        # Google Driveから動画ファイルを取得
        video_file_path = download_video(service, folder_id)

        if video_file_path:
            output_video_path = f"output_{task['game_id']}.mp4"
            trim_video(video_file_path, output_video_path, start_time_1st_half, start_time_2nd_half)
            print(f"Trimmed video saved to {output_video_path}")
        else:
            print(f"Failed to download video for game_id: {task['game_id']}")


def download_video(service, folder_id):
    """
    指定されたGoogle DriveフォルダID内の「Panoramic Video」フォルダにあるmp4動画をダウンロードする。

    Args:
        service: Google Drive APIのサービスインスタンス。
        folder_id (str): フォルダID。

    Returns:
        str: ダウンロードされた動画のローカルパス。
    """
    try:
        # フォルダ内の「Panoramic Video」という名前のサブフォルダを検索
        query = f"'{folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and name = 'Panoramic Video'"
        results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        folders = results.get('files', [])

        if not folders:
            print("No 'Panoramic Video' folder found.")
            return None

        panoramic_folder_id = folders[0]['id']

        # Panoramic Videoフォルダ内のmp4動画を検索
        query = f"'{panoramic_folder_id}' in parents and mimeType='video/mp4'"
        results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = results.get('files', [])

        if not files:
            print("No mp4 video files found in 'Panoramic Video' folder.")
            return None

        # 最初のmp4動画ファイルをダウンロード
        file_id = files[0]['id']
        file_name = files[0]['name']
        request = service.files().get_media(fileId=file_id)
        file_path = f"./{file_name}"

        with io.FileIO(file_path, 'wb') as file:
            downloader = MediaIoBaseDownload(file, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

        print(f"Downloaded file: {file_path}")
        return file_path

    except Exception as e:
        print(f"Error downloading video: {e}")
        return None


def trim_video(input_video_path, output_video_path, start_time_1st_half, start_time_2nd_half):
    """
    Trims a video to a specified start and end time using ffmpeg.

    Args:
        input_video_path (str): The path to the input video file.
        output_video_path (str): The path where the trimmed video will be saved.
        start_time (float): The start time in seconds to trim the video from.
        end_time (float): The end time in seconds to trim the video to.
    """
    duration = start_time_2nd_half - start_time_1st_half
    cmd = [
        'ffmpeg', '-i', input_video_path,
        '-ss', str(start_time_1st_half),
        '-t', str(duration),
        '-c', 'copy',  # Use stream copy for faster processing
        output_video_path,
        '-y'  # Overwrite output file if it exists
    ]

    try:
        subprocess.run(cmd, check=True)
        print(f"Video trimmed successfully: {output_video_path}")
        
        # トリミング後に入力動画を削除
        if os.path.exists(input_video_path):
            os.remove(input_video_path)
            print(f"Input video deleted: {input_video_path}")
        else:
            print(f"Input video not found: {input_video_path}")

    except subprocess.CalledProcessError as e:
        print(f"Error trimming video: {e}")



def authenticate():
    creds = None
    # トークンファイルが存在する場合、それを読み込む
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # トークンが存在しないか、無効な場合、ログインして新しいトークンを取得する
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # トークンを保存して、将来のために保存する
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return creds


if __name__ == "__main__":
    main()

# Example usage:
# python trim.py input.mp4 output.mp4 10 20