1. annotation
    1. arrange_annotation.py
    1. annotation_to_csv.py
    1. combine_right_and_left_annotation.py
    1. (evaluate_annotation.py)
1. tracking
    1. convert_raw_to_pitch_plane_csv.py
        * input: {match_id}_tracker_box_data.xml or {match_id}_{1, 2 or 3}_frame_data.json
        * output: {match_id}_pitch_plane_coordinates.csv or {match_id}_{1, 2 or 3}_pitch_plane_coordinates.csv
    1. combine_pitch_plane_csv.py
        * input: {match_id}_{1, 2 or 3}_pitch_plane_coordinates.csv
        * output: {match_id}_pitch_plane_coordinates.csv
    1. add_team_id_to_pitch_plane_csv.py
        * add team_id and position
    1. get_tracking_in_video_from_pitch_plane_csv.py
    1. arrange_tracking.py