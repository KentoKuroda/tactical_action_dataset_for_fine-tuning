import pandas as pd
import numpy as np
from pathlib import Path
import json
import itertools
import krippendorff  # pip install krippendorff
from sklearn.metrics import confusion_matrix  # pip install scikit-learn
from collections import Counter

# --- グローバル設定 ---

# サンプリングレート (ms)
# 1000 = 1秒ごと, 100 = 0.1秒ごと
# 小さすぎるとメモリを大量消費し、大きすぎると短いアノテーションが欠落します
SAMPLE_RATE = 200 

# ベースディレクトリ
BASE_DIR = Path("data/raw/annotation")

# 出力ファイル
KRI_OUTPUT_FILE = BASE_DIR / "evaluate_annotation_krippendorfs.csv"
PAIRWISE_OUTPUT_FILE = BASE_DIR / "evaluate_annotation_pairwise.csv"

# 各グループの4人のアノテーターの列名
ANNOTATOR_COLS = ['Annotator_1', 'Annotator_2', 'Annotator_3', 'Annotator_4']

# "該当なし" を示す内部ラベル名
NO_LABEL = "No_Label"


def main():
    all_group_dfs = []
    global_labels = set([NO_LABEL]) # "NO_LABEL" を初期値として追加

    # 1. data/raw/annotation/ 内の全グループフォルダを処理
    group_folders = [d for d in BASE_DIR.iterdir() if d.is_dir() and '_' in d.name]
    
    for group_dir in sorted(group_folders):
        json_files = sorted(list(group_dir.glob("*.json")))
        
        if not json_files:
            continue

        if len(json_files) != 4:
            print(f"Warning: Expected 4 JSON files in {group_dir.name}, but found {len(json_files)}. Will still attempt to process existing files.")
        group_df = process_group(json_files, group_dir.name)
        if group_df is not None and len(group_df) > 0:
            all_group_dfs.append(group_df)
            for col in ANNOTATOR_COLS:
                global_labels.update(pd.unique(group_df[col].astype(str)))

    if not all_group_dfs:
        print("No valid data found to process.")
        return

    # 2. 全グループのDataFrameを縦に結合
    combined_df = pd.concat(all_group_dfs, ignore_index=True)
    # np.nan が混入している場合に備え、すべて "No_Label" (文字列) に置き換える
    combined_df = combined_df.fillna(NO_LABEL)
    # 分析に必要な列のみを抽出
    combined_df_for_calc = combined_df[ANNOTATOR_COLS]
    
    labels = sorted(list(global_labels))
    
    print(f"Total time steps sampled ({SAMPLE_RATE}ms): {len(combined_df_for_calc)}")
    print(f"Total unique labels found ({len(labels)}): {labels}")

    # --- 3. 重み付きAlphaの計算 ---
    # ユーザー定義の距離マップを構築
    distance_map = build_distance_map(labels)
    kripp_results = calculate_krippendorff_alpha(combined_df_for_calc, distance_map, labels)
    
    # 結果を保存
    kripp_df = pd.DataFrame([kripp_results])
    kripp_df.to_csv(KRI_OUTPUT_FILE, index=False)
    print(f"\nKrippendorff's Alpha results saved to {KRI_OUTPUT_FILE}")

    # --- 4. ペアワイズ混同行列の計算 ---
    pairwise_cm_df = calculate_pairwise_matrix(combined_df_for_calc, labels)
    
    # 結果を保存
    pairwise_cm_df.to_csv(PAIRWISE_OUTPUT_FILE)
    print(f"Pairwise confusion matrix saved to {PAIRWISE_OUTPUT_FILE}")
    print("\nProcessing complete.")


def process_group(json_files, group_name):
    """
    各アノテーターのJSONを読み、(game_id, start_video, end_video) ごとに合わせて
    サンプリングされた時系列ラベル行を作成して返す。
    戻り値: DataFrame (columns: group, game_id, seq_start, seq_end, interval_start, Annotator_1..4)
    """
    # 各アノテーターのシーケンスリストを読み込む (不足しているファイルは空リスト)
    annotator_sequences = []
    for i, json_file in enumerate(sorted(json_files)):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, list):
                    print(f"Warning: {json_file} doesn't contain a list. Treating as empty.")
                    annotator_sequences.append([])
                else:
                    annotator_sequences.append(data)
        except Exception as e:
            print(f"Error reading {json_file}: {e}")
            annotator_sequences.append([])

    # key = (game_id, start_video, end_video) -> { annotator_idx: sequence_dict }
    sequences_map = {}
    for annot_idx, seq_list in enumerate(annotator_sequences):
        for seq in seq_list:
            # validate minimal fields
            if 'game_id' not in seq or 'start_video' not in seq or 'end_video' not in seq or 'annotations' not in seq:
                print(f"Skipping malformed sequence (annotator {annot_idx+1}) in group {group_name}: missing fields.")
                continue
            key = (str(seq['game_id']), int(seq['start_video']), int(seq['end_video']))
            sequences_map.setdefault(key, {})[annot_idx] = seq

    if not sequences_map:
        print(f"No sequences found in group {group_name}.")
        return pd.DataFrame()  # 空DataFrameを返す

    rows = []
    for (game_id, seq_start, seq_end), annot_map in sorted(sequences_map.items(), key=lambda x: (x[0][0], x[0][1])):
        if seq_end <= seq_start:
            print(f"Skipping invalid sequence {game_id},{seq_start}-{seq_end} (end <= start).")
            continue

        # サンプリングするビン (left-closed intervals)
        time_bins = np.arange(seq_start, seq_end + SAMPLE_RATE, SAMPLE_RATE)
        if len(time_bins) < 2:
            # very short sequence, sample once at seq_start
            time_bins = np.array([seq_start, seq_end])
        intervals = pd.IntervalIndex.from_breaks(time_bins, closed='left')

        # 各アノテーター列を作る (デフォルトは NO_LABEL)
        annotator_series = {
            i: pd.Series(NO_LABEL, index=intervals, dtype=object)
            for i in range(len(ANNOTATOR_COLS))
        }

        # 各アノテーターのアノテーションを書き込む（そのアノテーターがこのシーケンスを持っている場合）
        for annot_idx in range(len(ANNOTATOR_COLS)):
            seq_obj = annot_map.get(annot_idx)
            if seq_obj is None:
                # このシーケンスをアノテーターが注釈していない -> NO_LABEL のまま
                continue
            for ann in seq_obj.get('annotations', []):
                try:
                    label = ann['label']
                    s = int(ann['start'])
                    e = int(ann['end'])
                except Exception:
                    continue
                if e <= s:
                    continue
                ann_interval = pd.Interval(s, e, closed='left')
                overlaps = intervals.overlaps(ann_interval)
                # 上書き（後のアノテーションが前のアノテーションを上書きする挙動）
                annotator_series[annot_idx][overlaps] = label

        # 各時間ビンごとに行を作る
        for interval in intervals:
            row = {
                "group": group_name,
                "game_id": game_id,
                "seq_start": seq_start,
                "seq_end": seq_end,
                "interval_start": int(interval.left)
            }
            for i, col in enumerate(ANNOTATOR_COLS):
                row[col] = annotator_series[i].get(interval, NO_LABEL)
            rows.append(row)

    df_group = pd.DataFrame(rows)
    # 型の整理（列順）
    df_group = df_group[["group", "game_id", "seq_start", "seq_end", "interval_start"] + ANNOTATOR_COLS]
    print(f"group {group_name}: built {len(df_group)} sampled rows from {len(sequences_map)} sequences.")
    return df_group


def build_distance_map(labels):
    """
    重み付きAlphaのための「ラベル間の意味的距離」を定義する関数。
    4つの局面（攻撃、守備、攻→守、守→攻）に基づいて距離を自動設定する。

    Args:
        labels (list): データセットに存在する全ラベルのリスト (NO_LABEL も含む)

    Returns:
        dict: {('LabelA', 'LabelB'): 0.25, ...} のような距離マップ
    """
    print("--- Defining Semantic Distance Map based on 4-phase model ---")
    distance_map = {}

    # --- 1. 局面（フェーズ）の定義 ---
    # (グローバル変数 NO_LABEL を 'No_Label' の代わりに使用)
    label_to_phase = {
        # 守備→攻撃 (Transition Defense to Offense)
        'Counter-attack': 'Trans_D_to_O',
        
        # 攻撃 (Offense)
        'Build up': 'Offense',
        'Progression': 'Offense',
        'Final third': 'Offense',
        
        # 攻撃→守備 (Transition Offense to Defense)
        'Counter-press': 'Trans_O_to_D',
        'Recovery': 'Trans_O_to_D',
        
        # 守備 (Defense)
        'High press': 'Defense',
        'Mid block': 'Defense',
        'Low block': 'Defense',
        
        # 該当なし
        NO_LABEL: 'No_Label' 
    }

    # 局面タイプのヘルパーセット
    transition_phases = {'Trans_D_to_O', 'Trans_O_to_D'}
    static_phases = {'Offense', 'Defense'}

    # --- 2. ルールに基づいて距離を計算 ---
    
    # 'labels' には、JSONから読み込まれた全てのユニークなラベルが入っている
    for l1 in labels:
        for l2 in labels:
            # 既に対称ペアで計算済みの場合はスキップ
            if (l1, l2) in distance_map:
                continue

            # (1) 自分自身との距離
            if l1 == l2:
                distance_map[(l1, l2)] = 0.0
                continue

            # 'labels' に含まれるが、上のマッピングにない未知のラベルを安全に処理
            phase1 = label_to_phase.get(l1, 'Unknown')
            phase2 = label_to_phase.get(l2, 'Unknown')

            distance = 1.0 # デフォルトは 1.0 (完全な不一致)

            if phase1 == 'Unknown' or phase2 == 'Unknown':
                # マッピングにないラベル (例: 'Unknown', 'Goalkick' など)
                print(f"Warning: Unknown label found. l1='{l1}'(p={phase1}), l2='{l2}'(p={phase2}). Setting dist=1.0")
                distance = 1.0
            elif phase1 == 'No_Label' or phase2 == 'No_Label':
                # (2) "No_Label" は他の全ての戦術と 1.0
                distance = 0.25 
            elif phase1 == phase2:
                # (3) ルール「同じ局面同士」
                distance = 0.25
            elif (phase1 in static_phases and phase2 in transition_phases) or \
                    (phase1 in transition_phases and phase2 in static_phases):
                # (4) ルール「攻撃・守備 と トランジション」
                distance = 0.50
            elif phase1 in transition_phases and phase2 in transition_phases:
                # (5) ルール「トランジション同士」
                distance = 0.50
            elif (phase1 == 'Offense' and phase2 == 'Defense') or \
                    (phase1 == 'Defense' and phase2 == 'Offense'):
                # (6) ルール「攻撃と守備」
                distance = 1.0
            
            # 対称性を担保してマップに格納
            distance_map[(l1, l2)] = distance
            distance_map[(l2, l1)] = distance

    print(f"Distance map defined for {len(distance_map)} pairs based on 4-phase model.")
    return distance_map


def calculate_krippendorff_alpha(df_all, distance_map, labels):
    """
    データ全体でKrippendorff's Alpha (名義・重み付き) を計算する
    (TypeError: ... 'i1' を回避するため、*args, **kwargs を追加)
    """
    print("Calculating Krippendorff's Alpha...")

    # --- 1. データを数値IDにエンコード ---
    # (dtype='O' エラー回避のため)
    label_to_id = {label: i for i, label in enumerate(labels)}
    id_to_label = {i: label for label, i in label_to_id.items()}
    
    df_numeric = df_all.replace(label_to_id)
    data_matrix_numeric = df_numeric.T.values

    # --- 2. 名義Alpha (重みなし) ---
    alpha_nominal = krippendorff.alpha(data_matrix_numeric, level_of_measurement='nominal')
    
    # --- 3. 重み付きAlpha ---
    # 'i1' などのライブラリ内部引数を受け取れるよう、
    # 関数のシグネチャに *args と **kwargs を追加します。
    def custom_distance_metric_numeric(a, b, *args, **kwargs):
        
        # N = ラベルの総数
        n_labels_a = a.shape[0] # (N, 1) なので N
        n_labels_b = b.shape[1] # (1, N) なので N

        if n_labels_a != n_labels_b:
            # 万が一、形状が N, 1 と 1, N でない場合のフォールバック
            print("Warning: Distance metric received unexpected array shapes.")
            return 1.0 

        n_labels = n_labels_a
        
        # 返すべき (N, N) の距離行列を初期化
        matrix = np.zeros((n_labels, n_labels), dtype=float)
        
        # 行列を埋める
        for i in range(n_labels):
            for j in range(n_labels):
                
                # ベクトルからスカラ値（ID）を取得
                id_i = a[i, 0]
                id_j = b[0, j]
                
                # IDからラベル名（文字列）を取得
                label_i = id_to_label.get(id_i)
                label_j = id_to_label.get(id_j)
                
                if label_i is None or label_j is None:
                    matrix[i, j] = 1.0 # 安全策
                else:
                    # ユーザー定義の distance_map (dict) から距離を取得
                    matrix[i, j] = distance_map.get((label_i, label_j), 1.0)
        
        # (N, N) 行列を返す
        return matrix

    # `level_of_measurement` に、カスタム「関数」を渡す
    # (これは 'ndarray' (行列) を渡した前回のエラーからの差し戻しです)
    alpha_weighted = krippendorff.alpha(
        data_matrix_numeric, 
        level_of_measurement=custom_distance_metric_numeric # <--- 関数を渡す
    )
    
    print(f"Alpha (Nominal): {alpha_nominal:.4f}")
    print(f"Alpha (Weighted): {alpha_weighted:.4f}")
    
    return {
        "alpha_nominal": alpha_nominal,
        "alpha_weighted": alpha_weighted,
        "note": f"Weighted alpha depends on the user-defined `build_distance_map` function. Sampled at {SAMPLE_RATE}ms."
    }


def calculate_pairwise_matrix(df_all, labels):
    """
    全アノテーターのペア（4C2 = 6ペア）で混同行列を合計する
    """
    print("Calculating Pairwise Confusion Matrix...")
    n_labels = len(labels)
    total_cm = np.zeros((n_labels, n_labels), dtype=int)
    
    # 6通りの全ペア (A1-A2, A1-A3, A1-A4, A2-A3, A2-A4, A3-A4) でループ
    for col1, col2 in itertools.combinations(ANNOTATOR_COLS, 2):
        # 2列分のデータを抽出
        df_pair = df_all[[col1, col2]]
        
        # sklearnのconfusion_matrixで計算
        cm = confusion_matrix(
            df_pair[col1], 
            df_pair[col2], 
            labels=labels
        )
        total_cm += cm

    # Pandas DataFrameに変換して見やすくする
    cm_df = pd.DataFrame(total_cm, index=labels, columns=labels)
    cm_df.index.name = "Annotator_A"
    cm_df.columns.name = "Annotator_B"
    
    return cm_df


if __name__ == "__main__":
    main()