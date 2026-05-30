#!/usr/bin/env python3
"""
模块名: scripts/weight_ablation.py
职责: 权重消融实验，验证 0.3/0.3/0.4 是否最优。
运行方式: python scripts/weight_ablation.py
输入: results/eval_raw_results.json (由 evaluate.py 生成)
输出: results/weight_ablation.json + 终端报告
作者: RAGShield Team
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple

RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)


def compute_risk_level(
    l1: float,
    l2: float,
    l3: float,
    warning_th: float,
    danger_th: float,
    weights: Dict[str, float],
) -> Tuple[str, str]:
    """简化版风险融合（离线计算）。"""
    adjusted_l2 = min(l2 * 2.0, 1.0) if l1 >= 0.5 else l2

    if l1 >= danger_th or l3 >= 0.7:
        return "danger", "block"

    final = weights["knowledge"] * l1 + weights["retrieval"] * adjusted_l2 + weights["generation"] * l3
    final = min(max(final, 0.0), 1.0)

    if final >= danger_th:
        return "danger", "block"
    elif final >= warning_th:
        return "warning", "pass_with_warning"
    else:
        return "safe", "pass"


def evaluate_with_weights(
    raw_results: List[Dict],
    weights: Dict[str, float],
    warning_th: float = 0.25,
    danger_th: float = 0.40,
) -> Dict:
    """用给定权重重新计算所有查询的指标。"""
    safe = [r for r in raw_results if r["expected"] == "safe"]
    tamper = [r for r in raw_results if r["expected"] == "warning_or_block"]
    injection = [r for r in raw_results if r["expected"] == "block"]
    attack = tamper + injection

    tp = fp = fn = 0
    for r in raw_results:
        actual_level, _ = compute_risk_level(
            r["l1_score"], r["l2_score"], r["l3_score"],
            warning_th, danger_th, weights,
        )
        if r["expected"] != "safe":
            if actual_level in ("warning", "danger"):
                tp += 1
            else:
                fn += 1
        else:
            if actual_level in ("warning", "danger"):
                fp += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    blocked_injection = sum(
        1 for r in injection
        if compute_risk_level(r["l1_score"], r["l2_score"], r["l3_score"], warning_th, danger_th, weights)[0] == "danger"
    )
    warned_tamper = sum(
        1 for r in tamper
        if compute_risk_level(r["l1_score"], r["l2_score"], r["l3_score"], warning_th, danger_th, weights)[0] in ("warning", "danger")
    )

    return {
        "knowledge_weight": round(weights["knowledge"], 2),
        "retrieval_weight": round(weights["retrieval"], 2),
        "generation_weight": round(weights["generation"], 2),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "block_rate": round(blocked_injection / len(injection), 4) if injection else 0.0,
        "tamper_detection_rate": round(warned_tamper / len(tamper), 4) if tamper else 0.0,
        "false_positive_rate": round(fp / len(safe), 4) if safe else 0.0,
    }


def generate_weight_configs() -> List[Dict[str, float]]:
    """生成权重组合（knowledge + retrieval + generation = 1.0）。"""
    configs = []
    step = 0.05
    k_vals = [round(x * step, 2) for x in range(1, 10)]  # 0.05 ~ 0.45
    r_vals = [round(x * step, 2) for x in range(1, 10)]

    for kw in k_vals:
        for rw in r_vals:
            gw = round(1.0 - kw - rw, 2)
            if gw < 0.15 or gw > 0.75:
                continue
            if kw + rw + gw < 0.99 or kw + rw + gw > 1.01:
                continue
            configs.append({"knowledge": kw, "retrieval": rw, "generation": gw})

    # 去重
    seen = set()
    unique = []
    for c in configs:
        key = (c["knowledge"], c["retrieval"], c["generation"])
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


def main():
    raw_path = RESULTS_DIR / "eval_raw_results.json"
    if not raw_path.exists():
        print(f"错误: 找不到 {raw_path}")
        print("请先运行: python scripts/evaluate.py")
        return

    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    raw_results = data["results"]

    configs = generate_weight_configs()
    print(f"生成权重组合: {len(configs)} 种")
    print(f"  warning_th=0.25, danger_th=0.40 (固定)")
    print()

    all_results = []
    best_f1 = 0.0
    best_config = None

    for i, weights in enumerate(configs, 1):
        metrics = evaluate_with_weights(raw_results, weights)
        all_results.append(metrics)
        if metrics["f1_score"] > best_f1:
            best_f1 = metrics["f1_score"]
            best_config = metrics
        if i % 10 == 0:
            print(f"  已计算 {i}/{len(configs)} 种...")

    # 保存
    out_path = RESULTS_DIR / "weight_ablation.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"best": best_config, "all": all_results}, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存: {out_path}")

    print("\n" + "=" * 70)
    print("权重消融报告")
    print("=" * 70)
    print(f"\n最优权重 (F1={best_f1:.4f}):")
    for k, v in best_config.items():
        print(f"  {k:25s}: {v}")

    print("\nTop 10 权重组合 (按 F1 排序):")
    sorted_results = sorted(all_results, key=lambda x: x["f1_score"], reverse=True)[:10]
    print(f"  {'knowledge':<10s} {'retrieval':<10s} {'generation':<10s} {'F1':<8s} {'Precision':<10s} {'Recall':<8s} {'FPR':<8s}")
    print("  " + "-" * 70)
    for r in sorted_results:
        print(f"  {r['knowledge_weight']:<10.2f} {r['retrieval_weight']:<10.2f} {r['generation_weight']:<10.2f} {r['f1_score']:<8.4f} {r['precision']:<10.4f} {r['recall']:<8.4f} {r['false_positive_rate']:<8.4f}")

    # 与当前方案对比
    current = evaluate_with_weights(raw_results, {"knowledge": 0.30, "retrieval": 0.30, "generation": 0.40})
    print(f"\n当前方案对比 (0.3/0.3/0.4):")
    for k, v in current.items():
        if k not in ("knowledge_weight", "retrieval_weight", "generation_weight"):
            print(f"  {k:25s}: {v}")


if __name__ == "__main__":
    main()
