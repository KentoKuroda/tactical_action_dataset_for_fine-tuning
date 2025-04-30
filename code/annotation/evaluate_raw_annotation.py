import json
import csv
from collections import defaultdict
import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from statsmodels.stats.inter_rater import fleiss_kappa


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--video_id')
    parser.add_argument('--team_id')
    return parser.parse_args()


def main():
    args = parse_arguments()
    video_ids = [str(video_id) for video_id in args.video_id.split(",")]
    team_id = args.team_id

    for video_id in video_ids:
        input_files_dir = Path(f"data/raw/annotation/{video_id}_{team_id}")
        input_files = list(input_files_dir.glob("*.csv"))
        
        output_path = Path(f"data/raw/annotation/{video_id}_{team_id}_kappa.csv")
        calculate_kappa(input_files, output_path)


def calculate_kappa(input_files, output_path):
    all_rows = []

    for input_file in input_files:
        df = pd.read_csv(input_file)

        if "match_time" in df.columns:
            df = df.drop(columns=["match_time"])

        df["no tactics"] = 0.0

        for i, row in df.iterrows():
            current_sum = row.drop(labels=["no tactics"]).sum()
            missing = 1.0 - current_sum
            if missing < -1e-6:
                print(f"[警告] {input_file.name} の {i}行目で合計が1.0を超えています: {current_sum}")
            elif missing > 0:
                df.at[i, "no tactics"] = missing

        rating_matrix = (df.values * 4).astype(int)

        for i, row in enumerate(rating_matrix):
            total_votes = np.sum(row)
            if total_votes != 4:
                print(f"[警告] {input_file.name} の {i}行目で合計が4人でない: {total_votes}")

        all_rows.append(rating_matrix)

    if not all_rows:
        print("評価対象のデータがありません。")
        return

    full_matrix = np.vstack(all_rows)

    # -----------------------
    # Fleiss' kappa and components
    # -----------------------
    n, k = full_matrix.shape  # n=サンプル数, k=カテゴリ数
    N = 4  # 評者数

    # 一致度 P̄ (観測一致率)
    P_i = (np.sum(full_matrix ** 2, axis=1) - N) / (N * (N - 1))
    P_bar = np.mean(P_i)

    # 偶然一致度 P̄_e
    p_j = np.sum(full_matrix, axis=0) / (n * N)
    P_e_bar = np.sum(p_j ** 2)

    # Fleiss' kappa
    kappa = (P_bar - P_e_bar) / (1 - P_e_bar) if (1 - P_e_bar) != 0 else np.nan

    # 理論上最大一致度に対する割合
    normalized_agreement = kappa if (1 - P_e_bar) == 0 else kappa / (1 - P_e_bar)

    # 出力
    print(f"\n全ファイル統合後の評価:")
    print(f"単純一致率 (agreement_rate): {P_bar:.4f}")
    print(f"偶然一致率 (chance_agreement_rate): {P_e_bar:.4f}")
    print(f"Fleiss' kappa: {kappa:.4f}")
    print(f"normalized_agreement (理論上一致に対する割合): {normalized_agreement:.4f}")

    # 保存
    output_df = pd.DataFrame([{
        "agreement_rate": P_bar,
        "chance_agreement_rate": P_e_bar,
        "fleiss_kappa": kappa,
        "normalized_agreement": normalized_agreement
    }])
    output_df.to_csv(output_path, index=False)
    print(f"→ 結果を {output_path} に保存しました。")


if __name__ == "__main__":
    main()
