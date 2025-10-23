# <code>Tactical Action Dataset</code>

This is the repository for the paper:

>[Kento Kuroda](). [Recognition of Overlapped Tactical Action from Soccer Match Video](). .

| <img src=""> |
|:--:|
| examination with image |

## Overview

This tactical data set is a world first in two respects. The first is that it is based on FIFA definitions. The second is that the tactics are annotated with continuous values.
This repository describes how to download the annotation data and retrieve the corresponding match data from SoccerTrack-V2.

## Installation

## Ground Truth Creation Pipeline
### Quick Start
### Individual Steps

## Project Structure
```
Tactical_Action_Dataset/
├── code/
│   ├── annotation/
│   │   ├── arrange_annotation.py
│   │   ├── combine_right_and_left_annotation.py
│   │   ├── convert_annotation_to_csv.py
│   │   ├── evaluate_annotation.py
│   │   └── evaluate_raw_annotation.py
│   ├── tracking/
│   │   ├── add_team_id_to_pitch_plane_csv.py
│   │   ├── arrange_tracking.py
│   │   ├── combine_pitch_plane_csv.py
│   │   ├── convert_annotation_to_csv.py
│   │   ├── get_tracking_in_video_from_pitch_plane_csv.py
│   │   └── visualize_tracking.py
│   └──
└── data/       # Data storage (gitignored except .gitkeep)
    ├── interim/
    │   ├── {match_id}/
    │   │   ├── {match_id}_00_01-04_18_annotation_combined.csv
    │   │   ├── {match_id}_00_01-04_18_tracking_arranged.csv
    │   │   └── ...
    │   └── ...
    └── raw/
        ├── annotation/
        └── tracking/
```

## Usage
1. annotation
    1. arrange_annotation.py
    1. convert_annotation_to_csv.py
    1. combine_right_and_left_annotation.py
    1. (evaluate_annotation.py)
    1. (evaluate_raw_annotation.py)
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
1. sequence and label
    1. generate_sequence_and_label.py
### Data Processing
### Evaluation

## License

## Citation

If you use this code or dataset for your own research, please cite:

```
@article{Tactical Action,
   title={Recognition of Overlapped Tactical Action from Soccer Match Video},
   author={Kuroda, K},
   journal={},
   year={2025}
}
```

## Contact