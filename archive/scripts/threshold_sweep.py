#!/usr/bin/env python3
"""
模块名: scripts/threshold_sweep.py
职责: 阈值扫描，自动寻找最优 warning_threshold / danger_threshold 组合。
运行方式: python scripts/threshold_sweep.py
输入: results/eval_raw_results.json (由 evaluate.py 生成)
输出: results/threshold_sweep.json + 终端报告
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

    # 规则3：单层极高风险直接阻断
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


def evaluate_with_thresholds(
    raw_results: List[Dict],
    warning_th: float,
    danger_th: float,
    weights: Dict[str, float],
) -> Dict:
    """用给定阈值重新计算所有查询的指标。"""
    safe = [r for r in raw_results if r["expected"] == "safe"]
    tamper = [r for r in raw_results if r["expected"] == "warning_or_block"]
    injection = [r for r in raw_results if r["expected"] == "block"]
    attack = tamper + injection

    tp = 0  # 攻击被检出 (warning/danger)
    fp = 0  # 正常被误判 (warning/danger)
    fn = 0  # 攻击漏检 (safe)

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

    # block-specific metrics
    blocked_injection = sum(
        1 for r in injection
        if compute_risk_level(r["l1_score"], r["l2_score"], r["l3_score"], warning_th, danger_th, weights)[0] == "danger"
    )
    warned_tamper = sum(
        1 for r in tamper
        if compute_risk_level(r["l1_score"], r["l2_score"], r["l3_score"], warning_th, danger_th, weights)[0] in ("warning", "danger")
    )

    return {
        "warning_threshold": warning_th,
        "danger_threshold": danger_th,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "block_rate": round(blocked_injection / len(injection), 4) if injection else 0.0,
        "tamper_detection_rate": round(warned_tamper / len(tamper), 4) if tamper else 0.0,
        "false_positive_rate": round(fp / len(safe), 4) if safe else 0.0,
    }


def main():
    raw_path = RESULTS_DIR / "eval_raw_results.json"
    if not raw_path.exists():
        print(f"错误: 找不到 {raw_path}")
        print("请先运行: python scripts/evaluate.py")
        return

    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    raw_results = data["results"]

    weights = {"knowledge": 0.3, "retrieval": 0.3, "generation": 0.4}

    warning_range = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45]
    danger_range = [0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.60, 0.70]

    print("开始阈值扫描...")
    all_results = []
    best_f1 = 0.0
    best_config = None

    for wth in warning_range:
        for dth in danger_range:
            if wth >= dth:
                continue  # warning 必须小于 danger
            metrics = evaluate_with_thresholds(raw_results, wth, dth, weights)
            all_results.append(metrics)
            if metrics["f1_score"] > best_f1:
                best_f1 = metrics["f1_score"]
                best_config = metrics

    # 保存
    out_path = RESULTS_DIR / "threshold_sweep.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"best": best_config, "all": all_results}, f, ensure_ascii=False, indent=2)
    print(f"结果已保存: {out_path}")

    print("\n" + "=" * 70)
    print("阈值扫描报告")
    print("=" * 70)
    print(f"\n最优组合 (F1={best_f1:.4f}):")
    for k, v in best_config.items():
        print(f"  {k:25s}: {v}")

    print("\nTop 5 组合 (按 F1 排序):")
    sorted_results = sorted(all_results, key=lambda x: x["f1_score"], reverse=True)[:5]
    print(f"  {'warning_th':<12s} {'danger_th':<12s} {'F1':<8s} {'Precision':<10s} {'Recall':<8s} {'FPR':<8s}")
    print("  " + "-" * 60)
    for r in sorted_results:
        print(f"  {r['warning_threshold']:<12.2f} {r['danger_threshold']:<12.2f} {r['f1_score']:<8.4f} {r['precision']:<10.4f} {r['recall']:<8.4f} {r['false_positive_rate']:<8.4f}")


if __name__ == "__main__":
    main()
