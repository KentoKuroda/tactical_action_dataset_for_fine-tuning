import argparse
import subprocess
import pickle
import os
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
    parser = argparse.ArgumentParser(description="Trim a video to a given start and end time.")
    parser.add_argument("input", help="Input video file path")
    parser.add_argument("output", help="Output video file path")
    parser.add_argument("start_time", type=float, help="Start time in seconds")
    parser.add_argument("end_time", type=float, help="End time in seconds")

    args = parser.parse_args()

    creds = authenticate()
    service = build('drive', 'v3', credentials=creds)

    # folder ID
    folder_ID_list = ['1kEf2xjis_i2GI2KhEOBM_OfEkfX1Wosy', '1L3GdAg64CimYrKjCmjIyPPbhatGDtNKz', '1LLSKrW1Li68X8cR8OymAHH0X7sChj1bY', '1CxoePbNWtDNnMC8Rbon2sJVK-RQRmLcT'] # tracking, match(skillcorner), match(statsbomb)

    trim_video(args.input, args.output, args.start_time, args.end_time)


def trim_video(input_video_path, output_video_path, start_time, end_time):
    """
    Trims a video to a specified start and end time using ffmpeg.

    Args:
        input_video_path (str): The path to the input video file.
        output_video_path (str): The path where the trimmed video will be saved.
        start_time (float): The start time in seconds to trim the video from.
        end_time (float): The end time in seconds to trim the video to.
    """
    duration = end_time - start_time
    cmd = [
        'ffmpeg', '-i', input_video_path,
        '-ss', str(start_time),
        '-t', str(duration),
        '-c', 'copy',  # Use stream copy for faster processing
        output_video_path,
        '-y'  # Overwrite output file if it exists
    ]
    subprocess.run(cmd, check=True)


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