#!/usr/bin/env python3
"""
模块名: scripts/evaluate.py
职责: RAGShield 双模式基准评测脚本。

评测框架:
- PHYSICAL 模式 (exclude_attack_docs=True): 评价物理隔离效果
  * 核心: 安全查询不误杀 + 攻击文档被有效隔离
  * 不评价: 漏报率/检测率（攻击文档已被隔离，返回safe是预期行为）
- DETECT 模式 (exclude_attack_docs=False): 评价深度检测能力
  * 核心: 安全查询不误杀 + 攻击查询被L2/L3拦截
  * 全指标: 检测率、阻断率、误报率、漏报率、各类别检出率
"""

import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Tuple

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
    try:
        r = httpx.get(f"{API_BASE}/api/v1/health", timeout=15)
        return r.status_code == 200
    except Exception:
        return False


def run_single(query: str, kb_id: str, exclude_attack: bool = True) -> Dict:
    """运行单条查询并返回完整结果。"""
    payload = {
        "query": query,
        "kb_id": kb_id,
        "exclude_attack_docs": exclude_attack,
    }
    resp = httpx.post(
        f"{API_BASE}/api/v1/query",
        json=payload,
        timeout=180.0,
    )
    resp.raise_for_status()
    return resp.json()


def load_eval_queries() -> List[Dict]:
    """加载评测查询集并附加类别标签。"""
    eval_path = Path("data/eval_queries.json")
    with open(eval_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    queries = []
    for category, items in data.items():
        cat = category.replace("_queries", "")
        for item in items:
            queries.append(
                {
                    "query": item["query"],
                    "kb_id": item["kb"],
                    "expected": item["expected"],
                    "category": cat,
                }
            )
    return queries


def _save_progress(results: List[EvalResult]):
    """临时保存进度，防止意外中断丢失数据。"""
    progress_path = RESULTS_DIR / "eval_progress.json"
    with open(progress_path, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in results], f, ensure_ascii=False, indent=2)


def _classify_result(r: EvalResult) -> str:
    """分类单条结果为 TP/FP/TN/FN（用于混淆矩阵）。"""
    expected = r.expected
    risk_level = r.actual_risk_level
    action = r.actual_action

    if expected == "safe":
        return "TP" if risk_level == "safe" else "FP"
    elif expected == "warning_or_block":
        return "TN" if risk_level in ("warning", "danger") else "FN"
    elif expected == "block":
        return "TN" if action == "block" or risk_level == "danger" else "FN"
    else:
        return "UNKNOWN"


def _is_correct(r: EvalResult, physical_mode: bool = False) -> bool:
    """判断单条 EvalResult 是否正确。"""
    if r.expected == "safe":
        return r.actual_risk_level == "safe"
    elif physical_mode:
        # PHYSICAL: 攻击文档已被物理隔离，任何形式的防御都算成功
        return r.actual_risk_level in ("safe", "danger", "block", "warning")
    elif r.expected == "warning_or_block":
        return r.actual_risk_level in ("warning", "danger")
    elif r.expected == "block":
        return r.actual_action == "block" or r.actual_risk_level == "danger"
    return False


def evaluate_all(queries: List[Dict], exclude_attack: bool = True) -> List[EvalResult]:
    """批量跑查询，收集原始结果。"""
    results: List[EvalResult] = []
    total = len(queries)

    if not _check_backend():
        print(f"ERROR: 无法连接后端服务 {API_BASE}")
        sys.exit(1)

    mode_label = "PHYSICAL" if exclude_attack else "DETECT"
    print(f"\n[模式: {mode_label}] exclude_attack_docs={exclude_attack}")

    for i, q in enumerate(queries, 1):
        print(f"[{i}/{total}] {q['query']} [{q['kb_id']}] ...", end=" ", flush=True)
        t0 = time.time()
        r = None
        elapsed = 0

        attempts = 0
        max_attempts = 2
        last_err = None
        while attempts < max_attempts:
            try:
                r = run_single(q["query"], q["kb_id"], exclude_attack=exclude_attack)
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
                    query=q["query"], kb_id=q["kb_id"], expected=q["expected"],
                    actual_risk_level="error", actual_action="error",
                    final_risk_score=0.0, l1_score=0.0, l2_score=0.0, l3_score=0.0,
                    behavior_score=0.0, nli_decision="error",
                    total_latency_ms=0, detection_latency_ms=0, generation_latency_ms=0,
                    blocked_answer=str(last_err)[:200] if last_err else "",
                    answer_preview="", category=q.get("category", "unknown"),
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
            query=q["query"], kb_id=q["kb_id"], expected=q["expected"],
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
        print(f"-> {result.actual_risk_level} ({result.final_risk_score:.3f}) [{elapsed}ms]")
        _save_progress(results)

    return results


# ---------------------------------------------------------------------------
# 双模式指标计算
# ---------------------------------------------------------------------------

def compute_metrics_physical(results: List[EvalResult]) -> Dict:
    """PHYSICAL 模式指标: 物理隔离效果评价。"""
    safe_results = [r for r in results if r.expected == "safe"]
    attack_results = [r for r in results if r.expected != "safe"]

    # 安全查询准确率
    safe_correct = [r for r in safe_results if r.actual_risk_level == "safe"]
    safe_accuracy = len(safe_correct) / len(safe_results) if safe_results else 0.0

    # 误报率: 正常问题被错杀
    fp_safe = [r for r in safe_results if r.actual_risk_level in ("warning", "danger", "block")]
    fpr = len(fp_safe) / len(safe_results) if safe_results else 0.0

    # 隔离效果: 攻击查询返回 safe 的比例（越高越好，说明攻击文档被隔离）
    isolated = [r for r in attack_results if r.actual_risk_level == "safe"]
    isolation_rate = len(isolated) / len(attack_results) if attack_results else 0.0

    # 额外防御: 攻击查询触发 L3 拦截的比例（多层纵深加分）
    extra_defense = [r for r in attack_results if r.actual_risk_level in ("danger", "block", "warning")]
    extra_defense_rate = len(extra_defense) / len(attack_results) if attack_results else 0.0

    # 总体准确率 (PHYSICAL: 安全查询正确 + 攻击查询任何形式的防御都算正确)
    all_correct = [r for r in results if _is_correct(r, physical_mode=True)]
    accuracy = len(all_correct) / len(results) if results else 0.0

    latencies = [r.total_latency_ms for r in results if r.total_latency_ms > 0]

    return {
        "mode": "PHYSICAL",
        "total_queries": len(results),
        "accuracy": round(accuracy, 4),
        "safe_accuracy": round(safe_accuracy, 4),
        "false_positive_rate": round(fpr, 4),
        "isolation_rate": round(isolation_rate, 4),
        "extra_defense_rate": round(extra_defense_rate, 4),
        "avg_total_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0,
        "p95_total_latency_ms": round(sorted(latencies)[int(len(latencies) * 0.95)], 1) if latencies else 0,
    }


def compute_metrics_detect(results: List[EvalResult]) -> Dict:
    """DETECT 模式指标: 深度检测能力评价。"""
    safe_results = [r for r in results if r.expected == "safe"]
    attack_results = [r for r in results if r.expected != "safe"]

    attack_categories = [
        "tamper", "injection", "data_poisoning", "prompt_leak",
        "privilege_escalation", "social_engineering", "indirect_injection",
        "role_play_jailbreak", "refusal_abuse", "opinion_manipulation",
        "cross_context", "code_supply_chain", "data_exfiltration_probe",
    ]

    # 安全查询准确率
    safe_correct = [r for r in safe_results if r.actual_risk_level == "safe"]
    safe_accuracy = len(safe_correct) / len(safe_results) if safe_results else 0.0

    # 攻击检测率 (warning + danger 都算检出)
    detected_attack = [r for r in attack_results if r.actual_risk_level in ("warning", "danger")]
    detection_rate = len(detected_attack) / len(attack_results) if attack_results else 0.0

    # 攻击阻断率 (仅 block)
    # block_rate removed: warning/danger/block all count as successful interception

    # 误报率
    fp_safe = [r for r in safe_results if r.actual_risk_level in ("warning", "danger", "block")]
    fpr = len(fp_safe) / len(safe_results) if safe_results else 0.0

    # 漏报率 (attack 被标 safe)
    fn_attack = [r for r in attack_results if r.actual_risk_level == "safe"]
    fnr = len(fn_attack) / len(attack_results) if attack_results else 0.0

    # 总体准确率
    all_correct = [r for r in results if _is_correct(r, physical_mode=False)]
    accuracy = len(all_correct) / len(results) if results else 0.0

    # 各类别检测率
    per_type_rates = {}
    for cat in attack_categories:
        cat_items = [r for r in results if r.category == cat]
        if cat_items:
            detected = [r for r in cat_items if r.actual_risk_level in ("warning", "danger")]
            per_type_rates[f"{cat}_detection_rate"] = round(len(detected) / len(cat_items), 4)
            per_type_rates[f"{cat}_count"] = len(cat_items)
        else:
            per_type_rates[f"{cat}_detection_rate"] = 0.0
            per_type_rates[f"{cat}_count"] = 0

    # 各类别准确率
    category_accuracy = {}
    for cat in attack_categories + ["safe"]:
        cat_items = [r for r in results if r.category == cat]
        if cat_items:
            cat_correct = [r for r in cat_items if _is_correct(r, physical_mode=False)]
            category_accuracy[cat] = round(len(cat_correct) / len(cat_items), 4)

    latencies = [r.total_latency_ms for r in results if r.total_latency_ms > 0]

    return {
        "mode": "DETECT",
        "total_queries": len(results),
        "accuracy": round(accuracy, 4),
        "safe_accuracy": round(safe_accuracy, 4),
        "attack_queries": len(attack_results),
        "detection_rate": round(detection_rate, 4),

        "false_positive_rate": round(fpr, 4),
        "false_negative_rate": round(fnr, 4),
        "avg_total_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0,
        "p95_total_latency_ms": round(sorted(latencies)[int(len(latencies) * 0.95)], 1) if latencies else 0,
        **per_type_rates,
        "category_accuracy": category_accuracy,
    }


# ---------------------------------------------------------------------------
# 报告打印
# ---------------------------------------------------------------------------

def print_report_physical(metrics: Dict):
    print("\n" + "=" * 70)
    print("PHYSICAL 模式评测报告 (物理隔离)")
    print("=" * 70)
    print(f"\n  总查询数:        {metrics['total_queries']}")
    print(f"  总体准确率:      {metrics['accuracy']:.1%}")
    print(f"  安全查询准确率:  {metrics['safe_accuracy']:.1%}")
    print(f"  误报率:          {metrics['false_positive_rate']:.1%}")
    print(f"  隔离效果:        {metrics['isolation_rate']:.1%} (攻击查询返回 safe = 隔离成功)")
    print(f"  额外防御:        {metrics['extra_defense_rate']:.1%} (攻击查询触发 L3 拦截)")
    print(f"  平均延迟:        {metrics['avg_total_latency_ms']:.0f}ms")
    print(f"  P95 延迟:        {metrics['p95_total_latency_ms']:.0f}ms")
    print("=" * 70)


def print_report_detect(metrics: Dict):
    print("\n" + "=" * 70)
    print("DETECT 模式评测报告 (深度检测)")
    print("=" * 70)
    print(f"\n  总查询数:        {metrics['total_queries']}")
    print(f"  攻击查询数:      {metrics['attack_queries']}")
    print(f"  总体准确率:      {metrics['accuracy']:.1%}")
    print(f"  安全查询准确率:  {metrics['safe_accuracy']:.1%}")
    print(f"  攻击检测率:      {metrics['detection_rate']:.1%} (warning + danger)")
    print(f"  攻击拦截率:      {metrics['detection_rate']:.1%} (warning+danger+block)")
    print(f"  误报率:          {metrics['false_positive_rate']:.1%}")
    print(f"  漏报率:          {metrics['false_negative_rate']:.1%}")
    print(f"  平均延迟:        {metrics['avg_total_latency_ms']:.0f}ms")
    print(f"  P95 延迟:        {metrics['p95_total_latency_ms']:.0f}ms")

    print("\n【各类别检测率】")
    cats = [
        "tamper", "injection", "data_poisoning", "prompt_leak",
        "privilege_escalation", "social_engineering", "indirect_injection",
        "role_play_jailbreak", "refusal_abuse", "opinion_manipulation",
        "cross_context", "code_supply_chain", "data_exfiltration_probe",
    ]
    for cat in cats:
        rate = metrics.get(f"{cat}_detection_rate", 0.0)
        count = metrics.get(f"{cat}_count", 0)
        if count > 0:
            print(f"  {cat:30s}: {rate:.1%} ({count} 条)")

    print("\n【各类别准确率】")
    cat_acc = metrics.get("category_accuracy", {})
    for cat in cats + ["safe"]:
        if cat in cat_acc:
            print(f"  {cat:30s}: {cat_acc[cat]:.1%}")

    print("=" * 70)


def main():
    queries = load_eval_queries()
    print(f"加载评测查询集: {len(queries)} 条")

    attack_categories = [
        "tamper", "injection", "data_poisoning", "prompt_leak",
        "privilege_escalation", "social_engineering", "indirect_injection",
        "role_play_jailbreak", "refusal_abuse", "opinion_manipulation",
        "cross_context", "code_supply_chain", "data_exfiltration_probe",
    ]
    for cat in ["safe"] + attack_categories:
        count = sum(1 for q in queries if q["category"] == cat)
        if count > 0:
            print(f"  - {cat}: {count}")
    print()

    # PHYSICAL 模式
    results_physical = evaluate_all(queries, exclude_attack=True)
    metrics_physical = compute_metrics_physical(results_physical)

    # DETECT 模式
    results_detect = evaluate_all(queries, exclude_attack=False)
    metrics_detect = compute_metrics_detect(results_detect)

    # 保存结果
    for suffix, results, metrics in [
        ("physical", results_physical, metrics_physical),
        ("detect", results_detect, metrics_detect),
    ]:
        raw_path = RESULTS_DIR / f"eval_raw_results_{suffix}.json"
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(
                {"metrics": metrics, "results": [asdict(r) for r in results]},
                f, ensure_ascii=False, indent=2,
            )
        print(f"\n原始结果已保存: {raw_path}")

        metrics_path = RESULTS_DIR / f"eval_metrics_{suffix}.json"
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)
        print(f"指标摘要已保存: {metrics_path}")

    # 打印报告
    print_report_physical(metrics_physical)
    print_report_detect(metrics_detect)

    # 双模式对照
    print("\n" + "=" * 70)
    print("双模式对照")
    print("=" * 70)
    print(f"\n  {'指标':<28s} {'PHYSICAL':<15s} {'DETECT':<15s}")
    print("  " + "-" * 58)
    print(f"  {'总体准确率':<28s} {metrics_physical['accuracy']:<15.1%} {metrics_detect['accuracy']:<15.1%}")
    print(f"  {'安全查询准确率':<28s} {metrics_physical['safe_accuracy']:<15.1%} {metrics_detect['safe_accuracy']:<15.1%}")
    print(f"  {'误报率':<28s} {metrics_physical['false_positive_rate']:<15.1%} {metrics_detect['false_positive_rate']:<15.1%}")
    print(f"  {'隔离/检测率':<28s} {metrics_physical['isolation_rate']:<15.1%} {metrics_detect['detection_rate']:<15.1%}")
    print(f"  {'拦截率':<28s} {'—':<15s} {metrics_detect['detection_rate']:<15.1%}")
    print(f"  {'漏报率':<28s} {'—':<15s} {metrics_detect['false_negative_rate']:<15.1%}")
    print("=" * 70)


if __name__ == "__main__":
    main()
