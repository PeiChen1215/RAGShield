#!/usr/bin/env python3
"""
模块名: scripts/evaluate.py
职责: 评测主脚本，批量跑查询并统计检测率、误报率、延迟等指标。
运行方式: python scripts/evaluate.py
输出: results/eval_raw_results.json + 终端报告
作者: RAGShield Team
"""

import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List

import httpx

API_BASE = "http://localhost:8000"
RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)


@dataclass
class EvalResult:
    query: str
    kb_id: str
    expected: str
    actual_risk_level: str
    actual_action: str
    final_risk_score: float
    l1_score: float
    l2_score: float
    l3_score: float
    behavior_score: float
    nli_decision: str
    total_latency_ms: int
    detection_latency_ms: int
    generation_latency_ms: int
    blocked_answer: str
    answer_preview: str
    category: str


def _check_backend() -> bool:
    """检查后端服务是否可连接。"""
    try:
        # 尝试一个短超时连接，不关心具体响应
        httpx.get(API_BASE, timeout=5.0)
        return True
    except httpx.ConnectError:
        return False
    except Exception:
        # 其他错误（如 404）说明服务在运行
        return True


def _save_progress(results: List[EvalResult]):
    """保存当前进度到结果文件。"""
    raw_path = RESULTS_DIR / "eval_raw_results.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(
            {"results": [asdict(r) for r in results]},
            f,
            ensure_ascii=False,
            indent=2,
        )


def run_single(query: str, kb_id: str, timeout: int = 120) -> Dict:
    """调用后端 API 跑单个查询。"""
    resp = httpx.post(
        f"{API_BASE}/api/v1/query",
        json={"query": query, "kb_id": kb_id, "top_k": 5, "generate_answer": True},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def load_eval_queries(path: str = "data/eval_queries.json") -> List[Dict]:
    """加载评测查询集，展平为统一列表，支持任意 *_queries 类别。"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 类别到 expected 的默认映射
    expected_map = {
        "safe": "safe",
        "tamper": "warning_or_block",
        "data_poisoning": "warning_or_block",
        "injection": "block",
        "prompt_leak": "block",
        "privilege_escalation": "block",
        "social_engineering": "block",
    }

    queries = []
    for category, items in data.items():
        cat = category.replace("_queries", "")
        default_expected = expected_map.get(cat, "safe")
        for item in items:
            queries.append(
                {
                    "query": item["query"],
                    "kb_id": item.get("kb", item.get("kb_id", "")),
                    "expected": item.get("expected", default_expected),
                    "category": cat,
                }
            )
    return queries


def judge(result: Dict, expected: str) -> str:
    """判定单条查询结果是否正确。"""
    risk_level = result.get("risk_level", "safe")
    action = result.get("action", "pass")

    if expected == "safe":
        return "TP" if risk_level == "safe" else "FP"
    elif expected == "warning_or_block":
        return "TP" if risk_level in ("warning", "danger") else "FN"
    elif expected == "block":
        return "TP" if action == "block" or risk_level == "danger" else "FN"
    else:
        return "UNKNOWN"


def _is_correct(r: EvalResult) -> bool:
    """判断单条 EvalResult 是否正确。"""
    if r.expected == "safe":
        return r.actual_risk_level == "safe"
    elif r.expected == "warning_or_block":
        return r.actual_risk_level in ("warning", "danger")
    elif r.expected == "block":
        return r.actual_action == "block" or r.actual_risk_level == "danger"
    return False


def evaluate_all(queries: List[Dict]) -> List[EvalResult]:
    """批量跑查询，收集原始结果。支持失败重试和每 1 条保存进度。"""
    results: List[EvalResult] = []
    total = len(queries)

    # 后端连通性检查
    if not _check_backend():
        print(f"ERROR: 无法连接后端服务 {API_BASE}")
        print("请确保服务已启动（如: uvicorn main:app --host 0.0.0.0 --port 8000）。")
        sys.exit(1)

    for i, q in enumerate(queries, 1):
        print(f"[{i}/{total}] {q['query']} [{q['kb_id']}] ...", end=" ", flush=True)
        t0 = time.time()
        r = None
        elapsed = 0

        # 尝试请求，失败则重试 1 次
        attempts = 0
        max_attempts = 2
        last_err = None
        while attempts < max_attempts:
            try:
                r = run_single(q["query"], q["kb_id"])
                elapsed = int((time.time() - t0) * 1000)
                break
            except Exception as e:
                attempts += 1
                last_err = e
                if attempts < max_attempts:
                    print(f"失败，重试({attempts}/{max_attempts})...", end=" ", flush=True)
                    time.sleep(1)
                else:
                    print(f"ERROR: {e}")

        if r is None:
            results.append(
                EvalResult(
                    query=q["query"],
                    kb_id=q["kb_id"],
                    expected=q["expected"],
                    actual_risk_level="error",
                    actual_action="error",
                    final_risk_score=0.0,
                    l1_score=0.0,
                    l2_score=0.0,
                    l3_score=0.0,
                    behavior_score=0.0,
                    nli_decision="error",
                    total_latency_ms=0,
                    detection_latency_ms=0,
                    generation_latency_ms=0,
                    blocked_answer=str(last_err)[:200] if last_err else "",
                    answer_preview="",
                    category=q.get("category", "unknown"),
                )
            )
            _save_progress(results)
            continue

        layer3 = r.get("layer3", {})
        consistency = layer3.get("consistency", {})

        behavior_score = 0.0
        if layer3.get("detection_method") == "behavior_audit":
            behavior_score = layer3.get("risk_score", 0.0)

        result = EvalResult(
            query=q["query"],
            kb_id=q["kb_id"],
            expected=q["expected"],
            actual_risk_level=r.get("risk_level", "safe"),
            actual_action=r.get("action", "pass"),
            final_risk_score=r.get("final_risk_score", 0.0),
            l1_score=r.get("layer1", {}).get("risk_score", 0.0),
            l2_score=r.get("layer2", {}).get("risk_score", 0.0),
            l3_score=layer3.get("risk_score", 0.0),
            behavior_score=behavior_score,
            nli_decision=consistency.get("final_decision", "skipped"),
            total_latency_ms=r.get("total_latency_ms", 0),
            detection_latency_ms=r.get("detection_latency_ms", 0),
            generation_latency_ms=r.get("generation_latency_ms") or 0,
            blocked_answer=(r.get("blocked_answer") or "")[:200],
            answer_preview=(r.get("answer") or "")[:100],
            category=q.get("category", "unknown"),
        )
        results.append(result)
        print(f"→ {result.actual_risk_level} ({result.final_risk_score:.3f}) [{elapsed}ms]")

        # 每 1 条保存一次进度
        _save_progress(results)

    return results


def compute_metrics(results: List[EvalResult]) -> Dict:
    """计算评测指标，支持 7 类查询的扩展统计。"""
    safe_results = [r for r in results if r.expected == "safe"]

    attack_categories = [
        "tamper",
        "injection",
        "data_poisoning",
        "prompt_leak",
        "privilege_escalation",
        "social_engineering",
    ]
    attack_results = [r for r in results if r.category in attack_categories]

    # 按类别分组
    category_results = {
        cat: [r for r in results if r.category == cat]
        for cat in attack_categories + ["safe"]
    }

    # Detection Rate: 攻击查询中被正确检出 (warning/danger) 的比例
    detected_attack = [
        r for r in attack_results if r.actual_risk_level in ("warning", "danger")
    ]
    detection_rate = len(detected_attack) / len(attack_results) if attack_results else 0.0

    # Block Rate: expected == block 的查询中被 block 或 danger 的比例
    block_expected = [r for r in results if r.expected == "block"]
    blocked = [
        r
        for r in block_expected
        if r.actual_action == "block" or r.actual_risk_level == "danger"
    ]
    block_rate = len(blocked) / len(block_expected) if block_expected else 0.0

    # Warning Rate: expected == warning_or_block 的查询中被 warning 或 danger 的比例
    warn_expected = [r for r in results if r.expected == "warning_or_block"]
    warned = [
        r for r in warn_expected if r.actual_risk_level in ("warning", "danger")
    ]
    warning_rate = len(warned) / len(warn_expected) if warn_expected else 0.0

    # False Positive Rate: safe 查询中被误判为 warning/danger 的比例
    fp_safe = [r for r in safe_results if r.actual_risk_level in ("warning", "danger")]
    fpr = len(fp_safe) / len(safe_results) if safe_results else 0.0

    # False Negative Rate: attack 查询中漏检为 safe 的比例
    fn_attack = [r for r in attack_results if r.actual_risk_level == "safe"]
    fnr = len(fn_attack) / len(attack_results) if attack_results else 0.0

    # Accuracy
    correct_results = [r for r in results if _is_correct(r)]
    accuracy = len(correct_results) / len(results) if results else 0.0

    # 按攻击类型细粒度检测率
    per_type_rates = {}
    for cat in attack_categories:
        cat_items = category_results.get(cat, [])
        if cat_items:
            detected = [
                r for r in cat_items if r.actual_risk_level in ("warning", "danger")
            ]
            per_type_rates[f"{cat}_detection_rate"] = round(
                len(detected) / len(cat_items), 4
            )
            per_type_rates[f"{cat}_count"] = len(cat_items)
        else:
            per_type_rates[f"{cat}_detection_rate"] = 0.0
            per_type_rates[f"{cat}_count"] = 0

    # 类别准确率
    category_accuracy = {}
    for cat in attack_categories + ["safe"]:
        cat_items = category_results.get(cat, [])
        if cat_items:
            cat_correct = [r for r in cat_items if _is_correct(r)]
            category_accuracy[cat] = round(len(cat_correct) / len(cat_items), 4)

    # Latency
    latencies = [r.total_latency_ms for r in results if r.total_latency_ms > 0]
    detection_latencies = [
        r.detection_latency_ms for r in results if r.detection_latency_ms > 0
    ]
    generation_latencies = [
        r.generation_latency_ms for r in results if r.generation_latency_ms > 0
    ]

    metrics = {
        "total_queries": len(results),
        "accuracy": round(accuracy, 4),
        "safe_queries": len(safe_results),
        "attack_queries": len(attack_results),
        "detection_rate": round(detection_rate, 4),
        "block_rate": round(block_rate, 4),
        "warning_rate": round(warning_rate, 4),
        "false_positive_rate": round(fpr, 4),
        "false_negative_rate": round(fnr, 4),
        "avg_total_latency_ms": round(sum(latencies) / len(latencies), 1)
        if latencies
        else 0,
        "p95_total_latency_ms": round(
            sorted(latencies)[int(len(latencies) * 0.95)], 1
        )
        if latencies
        else 0,
        "avg_detection_latency_ms": round(
            sum(detection_latencies) / len(detection_latencies), 1
        )
        if detection_latencies
        else 0,
        "avg_generation_latency_ms": round(
            sum(generation_latencies) / len(generation_latencies), 1
        )
        if generation_latencies
        else 0,
        **per_type_rates,
        "category_accuracy": category_accuracy,
    }
    return metrics


def print_detail_table(results: List[EvalResult]):
    """打印每个查询的详细结果表。"""
    print("\n【详细结果表】")
    print(
        f"  {'序号':<6s} {'查询':<32s} {'类别':<20s} {'预期':<16s} {'实际风险':<10s} {'实际动作':<10s} {'正确':<6s}"
    )
    print("  " + "-" * 104)
    for i, r in enumerate(results, 1):
        correct = "✅" if _is_correct(r) else "❌"
        query_display = (r.query[:30] + "..") if len(r.query) > 32 else r.query
        print(
            f"  {i:<6d} {query_display:<32s} {r.category:<20s} {r.expected:<16s} "
            f"{r.actual_risk_level:<10s} {r.actual_action:<10s} {correct:<6s}"
        )


def print_report(results: List[EvalResult], metrics: Dict):
    """打印评测报告。"""
    print("\n" + "=" * 70)
    print("RAGShield 评测报告")
    print("=" * 70)

    print("\n【查询统计】")
    print(f"  total_queries                 : {metrics['total_queries']}")
    print(f"  safe_queries                  : {metrics['safe_queries']}")
    print(f"  attack_queries                : {metrics['attack_queries']}")

    print("\n【核心指标】")
    print(f"  accuracy                      : {metrics['accuracy']:.3f}")
    print(f"  detection_rate                : {metrics['detection_rate']:.3f}")
    print(f"  block_rate                    : {metrics['block_rate']:.3f}")
    print(f"  warning_rate                  : {metrics['warning_rate']:.3f}")
    print(f"  false_positive_rate           : {metrics['false_positive_rate']:.3f}")
    print(f"  false_negative_rate           : {metrics['false_negative_rate']:.3f}")

    print("\n【按攻击类型细粒度统计】")
    attack_categories = [
        "tamper",
        "injection",
        "data_poisoning",
        "prompt_leak",
        "privilege_escalation",
        "social_engineering",
    ]
    for cat in attack_categories:
        rate = metrics.get(f"{cat}_detection_rate", 0.0)
        count = metrics.get(f"{cat}_count", 0)
        if count > 0:
            print(f"  {cat:<30s}: {rate:.3f} ({count} 条)")

    print("\n【延迟指标】")
    print(f"  avg_total_latency_ms          : {metrics['avg_total_latency_ms']:.1f}")
    print(f"  p95_total_latency_ms          : {metrics['p95_total_latency_ms']:.1f}")
    print(
        f"  avg_detection_latency_ms      : {metrics['avg_detection_latency_ms']:.1f}"
    )
    print(
        f"  avg_generation_latency_ms     : {metrics['avg_generation_latency_ms']:.1f}"
    )

    print_detail_table(results)
    print("\n" + "=" * 70)


def main():
    queries = load_eval_queries()
    print(f"加载评测查询集: {len(queries)} 条")

    # 动态打印各类别数量
    attack_categories = [
        "tamper",
        "injection",
        "data_poisoning",
        "prompt_leak",
        "privilege_escalation",
        "social_engineering",
    ]
    for cat in ["safe"] + attack_categories:
        count = sum(1 for q in queries if q["category"] == cat)
        if count > 0:
            print(f"  - {cat}: {count}")
    print()

    results = evaluate_all(queries)
    metrics = compute_metrics(results)

    # 保存原始结果
    raw_path = RESULTS_DIR / "eval_raw_results.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(
            {"metrics": metrics, "results": [asdict(r) for r in results]},
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"\n原始结果已保存: {raw_path}")

    # 保存指标摘要
    metrics_path = RESULTS_DIR / "eval_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    print(f"指标摘要已保存: {metrics_path}")

    print_report(results, metrics)


if __name__ == "__main__":
    main()
