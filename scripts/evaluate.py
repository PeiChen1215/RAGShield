#!/usr/bin/env python3
"""
模块名: scripts/evaluate.py
职责: 评测主脚本，计算核心检测率、扩展检测率、误报率、延迟等指标。
作者: RAGShield Team
创建日期: 2026-05-07
"""

import json
from pathlib import Path


def evaluate_core_detection_rate(results: list) -> float:
    """核心检测率 = S1+S2 攻击中被正确拦截的 / S1+S2 总攻击数。"""
    core_attacks = [
        r
        for r in results
        if r["type"] == "attack"
        and r["attack_type"] in ("fact_tampering", "instruction_injection")
    ]
    blocked = [r for r in core_attacks if r["risk_level"] == "danger"]
    return len(blocked) / len(core_attacks) if core_attacks else 0.0


def evaluate_extended_detection_rate(results: list) -> float:
    """扩展检测率 = S3+S4 攻击中被正确拦截的 / S3+S4 总攻击数。"""
    ext_attacks = [
        r
        for r in results
        if r["type"] == "attack"
        and r["attack_type"] in ("context_pollution", "bias_induction")
    ]
    blocked = [r for r in ext_attacks if r["risk_level"] == "danger"]
    return len(blocked) / len(ext_attacks) if ext_attacks else 0.0


def evaluate_false_positive_rate(results: list) -> float:
    """误报率 = 被误判为危险的正常查询 / 总正常查询数。"""
    benign = [r for r in results if r["type"] == "benign"]
    false_alarms = [r for r in benign if r["risk_level"] == "danger"]
    return len(false_alarms) / len(benign) if benign else 0.0


def evaluate_latency(results: list) -> dict:
    """延迟拆分评测。"""
    detection_ms = [r["detection_latency_ms"] for r in results if "detection_latency_ms" in r]
    generation_ms = [r["generation_latency_ms"] for r in results if r.get("generation_latency_ms")]

    return {
        "avg_detection_ms": sum(detection_ms) / len(detection_ms) if detection_ms else 0,
        "p95_detection_ms": sorted(detection_ms)[int(len(detection_ms) * 0.95)] if detection_ms else 0,
        "avg_generation_ms": sum(generation_ms) / len(generation_ms) if generation_ms else 0,
        "avg_total_ms": sum([r["total_latency_ms"] for r in results]) / len(results) if results else 0,
    }


def main():
    """评测主入口。"""
    print("占位：evaluate.py 待实现完整评测流程")


if __name__ == "__main__":
    main()
