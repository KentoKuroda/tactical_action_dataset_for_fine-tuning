import xml.etree.ElementTree as ET
import re
import json
import argparse


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--video_id')
    parser.add_argument('--anno_id')
    parser.add_argument('--team_id')
    return parser.parse_args()


def main():
    args = parse_arguments()
    video_ids = [str(video_id) for video_id in args.video_id.split(",")]
    anno_ids = [str(anno_id) for anno_id in args.anno_id.split(",")]
    team_id = args.team_id

    for video_id in video_ids:
        for anno_id in anno_ids:
            # XMLファイルの読み込み
            xml_file = f'raw/{video_id}_{anno_id}_{team_id}.xml'

            # TXTファイルの読み込み
            txt_file = f'raw/videolist_{video_id}.txt'

            # output file
            output_file = f'annotation_data/{video_id}_{team_id}/{video_id}_{anno_id}_{team_id}.json'

            arrange_annotation(xml_file, txt_file, output_file)


def arrange_annotation(xml_file, txt_file, output_file):

    tree = ET.parse(xml_file)
    root = tree.getroot()

    with open(txt_file, "r") as f:
        video_files = [line.strip() for line in f.readlines()]

    # 動画情報を解析
    videos = {}
    for video_file in video_files:
        game_id, start_time, end_time = parse_time_range(video_file)
        if start_time is not None and end_time is not None:
            videos[video_file] = (game_id, start_time, end_time)

    # XMLのラベル解析
    annotations_data = []
    instances = root.find("ALL_INSTANCES").findall("instance")

    for i, instance in enumerate(instances):
        annotation_id = instance.find("ID").text
        start = float(instance.find("start").text)
        code = instance.find("code").text

        if code == "End":
            continue

        video, offset, video_start_time = find_video_and_offset(start, videos)
        if video:
            offset_time = video_start_time + offset
            start_formatted = format_time(offset_time)

            # Determine the end time
            if i + 1 < len(instances):
                next_start = float(instances[i + 1].find("start").text)
                next_video, next_offset, next_video_start_time = find_video_and_offset(next_start, videos)

                if video == next_video:
                    end_formatted = format_time(next_video_start_time + next_offset)
                else:
                    end_formatted = format_time(videos[video][2])
            else:
                end_formatted = format_time(videos[video][2])

            # Add to JSON structure
            existing_video = next((item for item in annotations_data if item["start_video"] == format_time(videos[video][1])), None)
            if existing_video:
                existing_video["annotations"].append({"label": code, "start": start_formatted, "end": end_formatted})
            else:
                annotations_data.append({
                    "game_id": videos[video][0],
                    "start_video": format_time(videos[video][1]),
                    "end_video": format_time(videos[video][2]),
                    "annotations": [
                        {"label": code, "start": start_formatted, "end": end_formatted}
                    ]
                })

    # JSONファイルの書き込み
    with open(output_file, "w") as f:
        json.dump(annotations_data, f, indent=2)

    print(f"JSON file saved to {output_file}")


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


def format_time(seconds):
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{int(minutes):02}:{int(seconds):02}"


def find_video_and_offset(annotation_start_in_seq, videos):
    elapsed_time = 0
    for video in videos:
        game_id, start_time, end_time = videos[video]
        video_duration = end_time - start_time
        if elapsed_time <= annotation_start_in_seq < elapsed_time + video_duration:
            annotation_start_in_video = annotation_start_in_seq - elapsed_time
            return video, annotation_start_in_video, start_time
        elapsed_time += video_duration
    return None, None, None


if __name__ == "__main__":
    main()
