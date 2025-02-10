import pandas as pd
import cv2

# ラベル名と色の変換辞書
tactics_name = {
    "longcounter": "Long counter",
    "shortcounter": "Short counter",
    "opposition_half_possession": "Opposition half possession",
    "own_half_possession": "Own half possession",
    "counterpressing": "Counter-press",
    "highpressing": "High press",
    "middlepressing": "Middle press",
    "block": "Block"
}

tactics_colors = {
    "Long counter": (255, 0, 0),  # 青
    "Short counter": (255, 255, 0),  # 水色
    "Opposition half possession": (0, 255, 0),  # 緑
    "Own half possession": (173, 255, 47),  # 黄緑
    "Counter-press": (0, 0, 255),  # 赤
    "High press": (255, 105, 180),  # ピンク
    "Middle press": (170, 218, 255),  # 肌色
    "Block": (0, 165, 255)  # オレンジ
}

# Colors: all labels and bars are skin-colored, top value label in red
default_font_color = (255, 255, 255)  # White color
output_bar_color = (170, 218, 255)  # Skin color
label_bar_color = (255, 165, 0)  # orange color
highlight_font_color = (0, 0, 255)  # Red for highest value label

# Calculate bar position based on value
def calculate_bar_position(value, bar_length):
    if value <= 0.1:
        return 0
    elif value >= 0.6:
        return bar_length
    else:
        return int((value - 0.1) / (0.6 - 0.1) * bar_length)
    
# New function to calculate position for orange bar
def calculate_orange_bar_position(value, bar_length):
    return int(value * bar_length)  # Scale directly from 0 to 1 range

def make_resulting_video(input_video_path, output_video_path, resulting_df):
    cap = cv2.VideoCapture(input_video_path)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    frame_rate = cap.get(cv2.CAP_PROP_FPS)
    out = cv2.VideoWriter(output_video_path, fourcc, frame_rate, (int(cap.get(3)), int(cap.get(4))))

    resulting_df['frame'] = resulting_df.apply(lambda x: int((pd.to_datetime(x['time_seconds'], format='%M:%S.%f').hour * 3600 + # %H:
                                                              pd.to_datetime(x['time_seconds'], format='%M:%S.%f').minute * 60 +
                                                              pd.to_datetime(x['time_seconds'], format='%M:%S.%f').second) * frame_rate // 3 * 3), axis=1)

    columns_outputs_1 = [col for col in resulting_df.columns if col.startswith("output_1_")]
    columns_outputs_2 = [col for col in resulting_df.columns if col.startswith("output_2_")]
    columns_labels_1 = [col for col in resulting_df.columns if col.startswith("1_")]
    columns_labels_2 = [col for col in resulting_df.columns if col.startswith("2_")]

    bar_length = 200  # Bar max length
    bar_height = 10   # Bar height
    font_scale = 1.0  # Fixed font size
    y_shift = 700     # Shift up by 150 pixels
    x_1_position = 1450
    x_2_position = 30
    len_between_font_and_bar = 15

    # Predefined order of labels
    tactics_list = ["Long counter", "Short counter", "Opposition half possession", "Own half possession", "Counter-press", "High press", "Middle press", "Block"]

    for idx, row in resulting_df.iterrows():
        for _ in range(3):  # Show each data row for 3 frames
            ret, frame = cap.read()
            if not ret:
                break

            # Process output_1
            outputs_1 = {tactics_name[col.replace("output_1_", "")]: row[col] for col in columns_outputs_1}
            labels_1 = {tactics_name[col.replace("1_", "")]: row[col] for col in columns_labels_1}
            # top_output_1 = max(outputs_1, key=outputs_1.get)  # Highest value for color change

            for i, tactic in enumerate(tactics_list):
                output = outputs_1.get(tactic, 0)
                label = labels_1.get(tactic, 0)
                # Set color to red if output exceeds 0.5, otherwise use default color
                color = highlight_font_color if output > 0.3 else default_font_color
                y_position = frame.shape[0] - y_shift + i * 75  # Adjust y-position

                # Draw text
                cv2.putText(frame, tactic, (x_1_position, y_position), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, 2)

                # Draw bar
                output_bar_position = calculate_bar_position(output, bar_length)
                cv2.rectangle(frame, (x_1_position, y_position + len_between_font_and_bar), (x_1_position + output_bar_position, y_position + len_between_font_and_bar + bar_height), output_bar_color, -1)
                cv2.rectangle(frame, (x_1_position, y_position + len_between_font_and_bar), (x_1_position + bar_length, y_position + len_between_font_and_bar + bar_height), (255, 255, 255), 1)
                '''laabel_bar_position = calculate_orange_bar_position(label, bar_length)
                cv2.rectangle(frame, (x_1_position, y_position + len_between_font_and_bar + bar_height + 5), (x_1_position + laabel_bar_position, y_position + len_between_font_and_bar + bar_height + 5 + bar_height), label_bar_color, -1)
                cv2.rectangle(frame, (x_1_position, y_position + len_between_font_and_bar + bar_height + 5), (x_1_position + bar_length, y_position + len_between_font_and_bar + bar_height + 5 + bar_height), (255, 255, 255), 1)'''

            # Process output_2 (similar to output_1)
            outputs_2 = {tactics_name[col.replace("output_2_", "")]: row[col] for col in columns_outputs_2}
            labels_2 = {tactics_name[col.replace("2_", "")]: row[col] for col in columns_labels_2}
            # top_output_2 = max(outputs_2, key=outputs_2.get)  # Highest value for color change

            for i, tactic in enumerate(tactics_list):
                output = outputs_2.get(tactic, 0)
                label = labels_2.get(tactic, 0)
                # Set color to red if output exceeds 0.5, otherwise use default color
                color = highlight_font_color if output > 0.3 else default_font_color
                y_position = frame.shape[0] - y_shift + i * 75  # Adjust y-position

                # Draw text
                cv2.putText(frame, tactic, (x_2_position, y_position), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, 2)

                # Draw bar
                output_bar_position = calculate_bar_position(output, bar_length)
                cv2.rectangle(frame, (x_2_position, y_position + len_between_font_and_bar), (x_2_position + output_bar_position, y_position + len_between_font_and_bar + bar_height), output_bar_color, -1)
                cv2.rectangle(frame, (x_2_position, y_position + len_between_font_and_bar), (x_2_position + bar_length, y_position + len_between_font_and_bar + bar_height), (255, 255, 255), 1)
                '''laabel_bar_position = calculate_orange_bar_position(label, bar_length)
                cv2.rectangle(frame, (x_2_position, y_position + len_between_font_and_bar + bar_height + 5), (x_2_position + laabel_bar_position, y_position + len_between_font_and_bar + bar_height + 5 + bar_height), label_bar_color, -1)
                cv2.rectangle(frame, (x_2_position, y_position + len_between_font_and_bar + bar_height + 5), (x_2_position + bar_length, y_position + len_between_font_and_bar + bar_height + 5 + bar_height), (255, 255, 255), 1)'''

            out.write(frame)

        if idx % 100 == 0:
            print(idx)
        '''if idx >= 150:
            break'''

    cap.release()
    out.release()

if __name__ == '__main__':
    input_video_path = "data/real_vs_barca_4300-4435.mp4"
    output_video_path = "data/resulting_video.mp4"
    resulting_csv_path = "data/1498966_2_20240711_180201.csv"
    resulting_df = pd.read_csv(resulting_csv_path)

    make_resulting_video(input_video_path, output_video_path, resulting_df)