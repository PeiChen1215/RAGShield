"""
RAGShield 技术报告图表 — 全白色背景学术风格
生成: report_*.png + A~F 组合图
"""
import json
import os
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
from PIL import Image
from sklearn.metrics import auc, confusion_matrix, f1_score, precision_recall_curve, roc_curve

# ---------------------------------------------------------------------------
# 白色学术主题
# ---------------------------------------------------------------------------
WHITE = "#ffffff"
TEXT_DARK = "#1a1a2e"
TEXT_MUTED = "#555566"
GRID = "#e8e8ee"

COLOR_L1 = "#2d8a4e"       # 深绿
COLOR_L2 = "#1565c0"       # 深蓝
COLOR_L3 = "#c62828"       # 深红
COLOR_FUSION = "#6a1b9a"   # 紫色
COLOR_USER = "#455a64"      # 蓝灰
COLOR_STORAGE = "#e65100"   # 橙
COLOR_SAFE = "#2d8a4e"
COLOR_WARN = "#f9a825"
COLOR_DANGER = "#c62828"

plt.rcParams.update({
    "figure.facecolor": WHITE,
    "axes.facecolor": WHITE,
    "axes.edgecolor": GRID,
    "axes.labelcolor": TEXT_DARK,
    "axes.titlecolor": TEXT_DARK,
    "xtick.color": TEXT_MUTED,
    "ytick.color": TEXT_MUTED,
    "text.color": TEXT_DARK,
    "grid.color": GRID,
    "grid.linewidth": 0.5,
    "legend.facecolor": WHITE,
    "legend.edgecolor": GRID,
    "legend.labelcolor": TEXT_DARK,
    "font.family": ["SimHei", "Microsoft YaHei", "sans-serif"],
    "axes.unicode_minus": False,
})

OUTDIR = Path("results/figures")
OUTDIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 加载数据
# ---------------------------------------------------------------------------
def load_results(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data["results"] if isinstance(data, dict) else data


detect = load_results("results/eval_raw_results_detect.json")
physical = load_results("results/eval_raw_results_physical.json")

with open("results/eval_metrics_detect.json", encoding="utf-8") as f:
    metrics_detect = json.load(f)
with open("results/eval_metrics_physical.json", encoding="utf-8") as f:
    metrics_physical = json.load(f)


def savefig(name, dpi=200):
    plt.savefig(OUTDIR / name, dpi=dpi, bbox_inches="tight", facecolor=WHITE)
    plt.close()
    print(f"[OK] {name}")


# ---------------------------------------------------------------------------
# 0. 修复: 系统总体架构图
# ---------------------------------------------------------------------------
def draw_system_architecture():
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis("off")
    fig.patch.set_facecolor(WHITE)

    ax.text(7, 9.5, "RAGShield 系统总体架构", fontsize=20, fontweight="bold",
            ha="center", color=TEXT_DARK)

    # ===== 用户交互层 (顶部) =====
    ux_rect = FancyBboxPatch((1, 7.8), 12, 1.4, boxstyle="round,pad=0.05",
                              facecolor=COLOR_USER, alpha=0.08, edgecolor=COLOR_USER,
                              linewidth=2.5, zorder=2)
    ax.add_patch(ux_rect)
    ax.text(7, 8.95, "用户交互层", ha="center", va="top",
            fontsize=14, fontweight="bold", color=COLOR_USER, zorder=3)
    ux_items = ["Gradio Web 界面 (port 7860)", "FastAPI REST API (port 8000)", "HTTP 纯调用，零业务逻辑"]
    for i, item in enumerate(ux_items):
        ax.text(7, 8.55 - i*0.30, item, ha="center", va="top",
                fontsize=10, color=TEXT_MUTED, zorder=3)

    # ===== 引擎层大框 (中间) =====
    engine_rect = FancyBboxPatch((1, 3.2), 12, 4.2, boxstyle="round,pad=0.05",
                                  facecolor=COLOR_FUSION, alpha=0.06, edgecolor=COLOR_FUSION,
                                  linewidth=2.5, zorder=2)
    ax.add_patch(engine_rect)
    ax.text(7, 7.15, "RAGShield 检测引擎层", ha="center", va="top",
            fontsize=14, fontweight="bold", color=COLOR_FUSION, zorder=3)

    # ===== L1/L2/L3 三个模块 =====
    modules = [
        (1.5, 4.6, 3.2, 2.2, "L1 知识库层", COLOR_L1, [
            "OutlierDetector", "Sensitive NER", "入库扫描 + 查询检测"
        ]),
        (5.4, 4.6, 3.2, 2.2, "L2 检索层", COLOR_L2, [
            "AttentionAnalyzer", "RelevanceScorer", "来源可信度验证"
        ]),
        (9.3, 4.6, 3.2, 2.2, "L3 生成层", COLOR_L3, [
            "ConsistencyChecker", "BehaviorAuditor", "NLI + 行为审计"
        ]),
    ]

    for x, y, w, h, title, color, items in modules:
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03",
                              facecolor=color, alpha=0.12, edgecolor=color,
                              linewidth=1.5, zorder=4)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h - 0.25, title, ha="center", va="top",
                fontsize=12, fontweight="bold", color=color, zorder=5)
        for i, item in enumerate(items):
            ax.text(x + w/2, y + h - 0.65 - i*0.32, item,
                    ha="center", va="top", fontsize=9, color=TEXT_DARK, zorder=5)

    # ===== Risk Fusion (模块下方中央) =====
    fusion_rect = FancyBboxPatch((5.4, 3.4), 3.2, 0.9, boxstyle="round,pad=0.03",
                                  facecolor=COLOR_FUSION, alpha=0.15,
                                  edgecolor=COLOR_FUSION, linewidth=2, zorder=4)
    ax.add_patch(fusion_rect)
    ax.text(7, 3.85, "Risk Fusion Engine", ha="center", va="center",
            fontsize=11, fontweight="bold", color=COLOR_FUSION, zorder=5)
    ax.text(7, 3.55, "0.3×L1 + 0.3×L2 + 0.4×L3", ha="center", va="center",
            fontsize=9, color=COLOR_FUSION, zorder=5)

    # ===== 存储层 (底部) =====
    storage_rect = FancyBboxPatch((1, 1.2), 12, 1.6, boxstyle="round,pad=0.05",
                                   facecolor=COLOR_STORAGE, alpha=0.08, edgecolor=COLOR_STORAGE,
                                   linewidth=2.5, zorder=2)
    ax.add_patch(storage_rect)
    ax.text(7, 2.55, "知识库存储层", ha="center", va="top",
            fontsize=14, fontweight="bold", color=COLOR_STORAGE, zorder=3)
    st_items = ["ChromaDB 向量数据库 (SQLite)", "文档向量 + 元数据持久化", "Collections: demo_safe / demo_attack"]
    for i, item in enumerate(st_items):
        ax.text(7, 2.20 - i*0.28, item, ha="center", va="top",
                fontsize=10, color=TEXT_MUTED, zorder=3)

    # ===== 箭头 (不穿过文字) =====
    arrow_gray = dict(arrowstyle="->", color=TEXT_MUTED, lw=2, connectionstyle="arc3,rad=0")
    # 用户交互层 → 引擎层
    ax.annotate("", xy=(7, 7.8), xytext=(7, 7.35), arrowprops=arrow_gray)
    # 引擎层 → 存储层
    ax.annotate("", xy=(7, 3.2), xytext=(7, 2.8), arrowprops=arrow_gray)
    # L1 → Risk Fusion (从L1底边到Fusion左边)
    ax.annotate("", xy=(5.4, 3.85), xytext=(4.7, 4.6), arrowprops=arrow_gray)
    # L2 → Risk Fusion (从L2底边到Fusion顶边)
    ax.annotate("", xy=(7, 4.3), xytext=(7, 4.6), arrowprops=arrow_gray)
    # L3 → Risk Fusion (从L3底边到Fusion右边)
    ax.annotate("", xy=(8.6, 3.85), xytext=(9.3, 4.6), arrowprops=arrow_gray)

    # ===== 输出标签 (引擎层上方、用户层下方) =====
    outputs = [
        (2.5, 7.45, "safe", COLOR_SAFE),
        (7.0, 7.45, "warning", COLOR_WARN),
        (11.5, 7.45, "danger/block", COLOR_DANGER),
    ]
    for x, y, text, color in outputs:
        rect = FancyBboxPatch((x-0.8, y-0.18), 1.6, 0.36, boxstyle="round,pad=0.02",
                              facecolor=color, alpha=0.85, edgecolor="none", zorder=6)
        ax.add_patch(rect)
        tc = WHITE if text in ("safe", "danger/block") else TEXT_DARK
        ax.text(x, y, text, ha="center", va="center", fontsize=9,
                fontweight="bold", color=tc, zorder=7)

    plt.savefig(f"{OUTDIR}/report_architecture.png", dpi=200, bbox_inches="tight",
                facecolor=WHITE)
    plt.close()
    print("[OK] report_architecture.png (fixed)")


# ---------------------------------------------------------------------------
# 1. ROC 曲线
# ---------------------------------------------------------------------------
def plot_roc():
    y_true = [0 if r["expected"] == "safe" else 1 for r in detect]
    y_scores = [r["final_risk_score"] for r in detect]
    fpr, tpr, _ = roc_curve(y_true, y_scores)
    roc_auc = auc(fpr, tpr)

    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)
    ax.tick_params(colors=TEXT_MUTED)
    for spine in ax.spines.values():
        spine.set_color(GRID)

    ax.plot(fpr, tpr, color=COLOR_L1, lw=2.5, label=f"RAGShield (AUC = {roc_auc:.3f})")
    ax.plot([0, 1], [0, 1], color=TEXT_MUTED, lw=1.5, linestyle="--", label="Random Classifier")
    ax.fill_between(fpr, tpr, alpha=0.1, color=COLOR_L1)
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    ax.set_xlabel("False Positive Rate", fontsize=12)
    ax.set_ylabel("True Positive Rate", fontsize=12)
    ax.set_title("ROC Curve — DETECT Mode", fontsize=14, fontweight="bold")
    ax.legend(loc="lower right", fontsize=11)
    ax.grid(True, alpha=0.3, color=GRID)
    savefig("01_roc_auc_curve.png")


# ---------------------------------------------------------------------------
# 2. PR 曲线
# ---------------------------------------------------------------------------
def plot_pr():
    y_true = [0 if r["expected"] == "safe" else 1 for r in detect]
    y_scores = [r["final_risk_score"] for r in detect]
    precision, recall, thresholds = precision_recall_curve(y_true, y_scores)
    pr_auc = auc(recall, precision)

    f1s = []
    for t in thresholds:
        y_pred = [1 if s >= t else 0 for s in y_scores]
        f1s.append(f1_score(y_true, y_pred, zero_division=0))
    best_idx = int(np.argmax(f1s))

    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)
    ax.tick_params(colors=TEXT_MUTED)
    for spine in ax.spines.values():
        spine.set_color(GRID)

    ax.plot(recall, precision, color=COLOR_L3, lw=2.5, label=f"PR Curve (AP = {pr_auc:.3f})")
    ax.axhline(y=precision[best_idx], color=COLOR_SAFE, lw=1, linestyle=":",
               label=f"Best F1 = {f1s[best_idx]:.3f}")
    ax.scatter([recall[best_idx]], [precision[best_idx]],
               color=COLOR_SAFE, s=100, zorder=5, edgecolors=WHITE, linewidths=2)
    ax.fill_between(recall, precision, alpha=0.1, color=COLOR_L3)
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    ax.set_xlabel("Recall", fontsize=12)
    ax.set_ylabel("Precision", fontsize=12)
    ax.set_title("Precision-Recall Curve — DETECT Mode", fontsize=14, fontweight="bold")
    ax.legend(loc="lower left", fontsize=11)
    ax.grid(True, alpha=0.3, color=GRID)
    savefig("02_precision_recall_f1.png")


# ---------------------------------------------------------------------------
# 3. 混淆矩阵
# ---------------------------------------------------------------------------
def plot_confusion():
    labels = ["safe", "warning", "danger", "block"]
    label_idx = {l: i for i, l in enumerate(labels)}

    y_true = []
    y_pred = []
    for r in detect:
        exp = r["expected"]
        act = r["actual_risk_level"]
        if exp == "safe":
            y_true.append("safe")
        elif exp == "warning_or_block":
            y_true.append("danger")
        else:
            y_true.append(exp)
        y_pred.append(act)

    y_true_i = [label_idx.get(l, 0) for l in y_true]
    y_pred_i = [label_idx.get(l, 0) for l in y_pred]
    cm = confusion_matrix(y_true_i, y_pred_i, labels=range(len(labels)))

    fig, ax = plt.subplots(figsize=(9, 7))
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)

    im = ax.imshow(cm, cmap="RdYlGn_r", aspect="auto")

    # White grid lines between cells
    ax.set_xticks(np.arange(-0.5, len(labels), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(labels), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=2)
    ax.tick_params(which="minor", size=0)

    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=12, color=TEXT_DARK)
    ax.set_yticklabels(labels, fontsize=12, color=TEXT_DARK)
    ax.set_xlabel("Predicted", fontsize=13)
    ax.set_ylabel("Expected", fontsize=13)
    ax.set_title("Confusion Matrix — DETECT Mode", fontsize=15, fontweight="bold", color=TEXT_DARK)

    max_val = cm.max()
    for i in range(len(labels)):
        for j in range(len(labels)):
            val = cm[i, j]
            text_color = "white" if val > max_val * 0.4 else TEXT_DARK
            ax.text(j, i, str(val), ha="center", va="center",
                    color=text_color, fontsize=16, fontweight="bold")

    cbar = plt.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("Count", fontsize=11)
    cbar.ax.tick_params(labelsize=10)
    savefig("03_confusion_matrix.png")


# ---------------------------------------------------------------------------
# 4. 三层防御贡献图（堆叠柱状图）
# ---------------------------------------------------------------------------
def plot_layer_contribution():
    cats = [c for c in metrics_detect["category_accuracy"] if c != "safe"]
    attack_cats = [c for c in cats if c != "safe"]

    l1_vals = []
    l2_vals = []
    l3_vals = []
    behavior_vals = []

    for cat in attack_cats:
        items = [r for r in detect if r.get("category") == cat and r["expected"] != "safe"]
        if not items:
            l1_vals.append(0); l2_vals.append(0); l3_vals.append(0); behavior_vals.append(0)
            continue
        l1_vals.append(np.mean([r["l1_score"] for r in items]))
        l2_vals.append(np.mean([r["l2_score"] for r in items]))
        l3_vals.append(np.mean([r["l3_score"] for r in items]))
        behavior_vals.append(np.mean([r["behavior_score"] for r in items]))

    x = np.arange(len(attack_cats))
    width = 0.6

    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)
    ax.tick_params(colors=TEXT_MUTED)
    for spine in ax.spines.values():
        spine.set_color(GRID)

    bottom = np.zeros(len(attack_cats))
    colors = [COLOR_L1, COLOR_L2, COLOR_L3, "#f57c00"]
    labels = ["L1 知识库层", "L2 检索层", "L3 生成层", "行为审计"]
    vals_list = [l1_vals, l2_vals, l3_vals, behavior_vals]

    for vals, color, label in zip(vals_list, colors, labels):
        ax.bar(x, vals, width, bottom=bottom, color=color, label=label, alpha=0.85)
        bottom += np.array(vals)

    ax.set_xticks(x)
    ax.set_xticklabels(attack_cats, rotation=30, ha="right", fontsize=10, color=TEXT_DARK)
    ax.set_ylabel("Average Risk Score", fontsize=12)
    ax.set_title("Layer Contribution by Attack Category", fontsize=14, fontweight="bold")
    ax.legend(loc="upper right", fontsize=10)
    ax.set_ylim(0, 2.0)
    ax.grid(True, alpha=0.3, axis="y", color=GRID)
    savefig("04_layer_contribution.png")


# ---------------------------------------------------------------------------
# 5. 攻击检测热力图
# ---------------------------------------------------------------------------
def plot_attack_heatmap():
    categories = [c for c in metrics_detect["category_accuracy"] if c != "safe"]
    stats = {}
    for cat in categories:
        items = [r for r in detect if r.get("category") == cat]
        if not items:
            continue
        total = len(items)
        blocked = sum(1 for r in items if r["actual_risk_level"] == "danger")
        warned = sum(1 for r in items if r["actual_risk_level"] == "warning")
        safe = sum(1 for r in items if r["actual_risk_level"] == "safe")
        stats[cat] = {
            "blocked": blocked / total * 100,
            "warned": warned / total * 100,
            "safe": safe / total * 100,
        }

    cats = list(stats.keys())
    metrics_names = ["blocked", "warned", "safe"]
    data = np.array([[stats[c][m] for c in cats] for m in metrics_names])

    fig, ax = plt.subplots(figsize=(12, 4))
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)

    cmap = LinearSegmentedColormap.from_list("report", ["#e8f5e9", "#fff9c4", "#ffcdd2", "#ef5350"])
    im = ax.imshow(data, cmap=cmap, aspect="auto", vmin=0, vmax=100)

    ax.set_xticks(range(len(cats)))
    ax.set_xticklabels(cats, rotation=45, ha="right", fontsize=10, color=TEXT_DARK)
    ax.set_yticks(range(len(metrics_names)))
    ax.set_yticklabels(["Block %", "Warning %", "Pass %"], fontsize=11, color=TEXT_DARK)
    ax.set_title("Attack Detection Heatmap — DETECT Mode", fontsize=14, fontweight="bold")

    for i in range(len(metrics_names)):
        for j in range(len(cats)):
            color = WHITE if data[i, j] > 60 else TEXT_DARK
            ax.text(j, i, f"{data[i, j]:.0f}", ha="center", va="center",
                    color=color, fontsize=12, fontweight="bold")

    cbar = plt.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("Percentage (%)", fontsize=10)
    cbar.ax.tick_params(labelsize=9)
    savefig("05_attack_detection_heatmap.png")


# ---------------------------------------------------------------------------
# 6. 雷达图
# ---------------------------------------------------------------------------
def plot_radar():
    dims = ["准确率", "安全准确率", "检测率", "1-误报率", "1-漏报率"]
    d_vals = [
        metrics_detect["accuracy"], metrics_detect["safe_accuracy"],
        metrics_detect["detection_rate"], 1 - metrics_detect["false_positive_rate"],
        1 - metrics_detect["false_negative_rate"],
    ]
    p_vals = [
        metrics_physical["accuracy"], metrics_physical.get("safe_accuracy", 0.975),
        1.0, 1 - metrics_physical["false_positive_rate"], 1.0,
    ]

    angles = np.linspace(0, 2 * np.pi, len(dims), endpoint=False).tolist()
    d_vals += d_vals[:1]
    p_vals += p_vals[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    ax.plot(angles, d_vals, color=COLOR_L1, linewidth=2.5, label="DETECT", marker="o")
    ax.fill(angles, d_vals, color=COLOR_L1, alpha=0.12)
    ax.plot(angles, p_vals, color=COLOR_L2, linewidth=2.5, label="PHYSICAL", marker="s")
    ax.fill(angles, p_vals, color=COLOR_L2, alpha=0.12)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(dims, fontsize=11, color=TEXT_DARK)
    ax.set_ylim(0, 1.1)
    ax.set_title("Defense Mode Comparison", fontsize=14, fontweight="bold", pad=20, color=TEXT_DARK)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=11)
    ax.tick_params(colors=TEXT_MUTED)
    ax.grid(color=GRID, linewidth=0.5)
    savefig("06_mode_radar.png")


# ---------------------------------------------------------------------------
# 7. 风险评分分布
# ---------------------------------------------------------------------------
def plot_risk_distribution():
    safe_scores = [r["final_risk_score"] for r in detect if r["expected"] == "safe"]
    attack_scores = [r["final_risk_score"] for r in detect if r["expected"] != "safe"]

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)
    ax.tick_params(colors=TEXT_MUTED)
    for spine in ax.spines.values():
        spine.set_color(GRID)

    bins = np.linspace(0, 1.1, 25)
    ax.hist(safe_scores, bins=bins, alpha=0.7, color=COLOR_SAFE,
            label=f"Safe Queries (n={len(safe_scores)})", edgecolor=WHITE)
    ax.hist(attack_scores, bins=bins, alpha=0.7, color=COLOR_DANGER,
            label=f"Attack Queries (n={len(attack_scores)})", edgecolor=WHITE)

    ax.axvline(x=np.median(safe_scores), color=COLOR_SAFE, lw=2, linestyle="--",
               label=f"Safe Median = {np.median(safe_scores):.3f}")
    ax.axvline(x=np.median(attack_scores), color=COLOR_DANGER, lw=2, linestyle="--",
               label=f"Attack Median = {np.median(attack_scores):.3f}")

    ax.set_xlabel("Final Risk Score", fontsize=12)
    ax.set_ylabel("Count", fontsize=12)
    ax.set_title("Risk Score Distribution — DETECT Mode", fontsize=14, fontweight="bold")
    ax.legend(loc="upper right", fontsize=10)
    ax.grid(True, alpha=0.3, axis="y", color=GRID)
    savefig("07_risk_score_distribution.png")


# ---------------------------------------------------------------------------
# 8. 延迟分布箱线图
# ---------------------------------------------------------------------------
def plot_latency():
    safe_lat = [r["total_latency_ms"] / 1000 for r in detect if r["expected"] == "safe"]
    warn_lat = [r["total_latency_ms"] / 1000 for r in detect
                if r["expected"] != "safe" and r["actual_risk_level"] in ("warning", "danger")]
    block_lat = [r["total_latency_ms"] / 1000 for r in detect
                 if r["expected"] != "safe" and r["actual_risk_level"] == "danger"]

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)
    ax.tick_params(colors=TEXT_MUTED)
    for spine in ax.spines.values():
        spine.set_color(GRID)

    bp = ax.boxplot([safe_lat, warn_lat, block_lat],
                      tick_labels=["Safe", "Warning", "Blocked"],
                      patch_artist=True,
                      medianprops=dict(color=TEXT_DARK, linewidth=2),
                      whiskerprops=dict(color=TEXT_MUTED),
                      capprops=dict(color=TEXT_MUTED),
                      flierprops=dict(marker="o", markerfacecolor=COLOR_DANGER,
                                      markeredgecolor="none", markersize=5, alpha=0.6))

    colors = [COLOR_SAFE, COLOR_WARN, COLOR_DANGER]
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
        patch.set_edgecolor(GRID)

    ax.set_ylabel("Latency (seconds)", fontsize=12)
    ax.set_title("Query Latency Distribution — DETECT Mode", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y", color=GRID)
    savefig("08_latency_boxplot.png")


# ---------------------------------------------------------------------------
# 9. F1 分数按攻击类型
# ---------------------------------------------------------------------------
def plot_f1_by_category():
    categories = [c for c in metrics_detect["category_accuracy"] if c != "safe"]
    f1s = []
    labels = []
    for cat in categories:
        items = [r for r in detect if r.get("category") == cat]
        if not items:
            continue
        y_true = [1] * len(items)
        y_pred = [1 if r["actual_risk_level"] in ("danger", "block") else 0 for r in items]
        f1 = f1_score(y_true, y_pred, zero_division=0)
        f1s.append(f1)
        labels.append(cat)

    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)
    ax.tick_params(colors=TEXT_MUTED)
    for spine in ax.spines.values():
        spine.set_color(GRID)

    x = np.arange(len(labels))
    colors = [COLOR_SAFE if f >= 0.8 else COLOR_DANGER if f < 0.5 else COLOR_WARN for f in f1s]
    bars = ax.bar(x, f1s, color=colors, alpha=0.85, edgecolor=GRID, linewidth=1)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=10, color=TEXT_DARK)
    ax.set_ylim(0, 1.1)
    ax.set_ylabel("F1 Score", fontsize=12)
    ax.set_title("F1 Score by Attack Category", fontsize=14, fontweight="bold")
    ax.axhline(y=0.8, color=COLOR_SAFE, lw=1, linestyle="--", alpha=0.5, label="Target F1 = 0.8")
    ax.axhline(y=0.5, color=COLOR_DANGER, lw=1, linestyle="--", alpha=0.5, label="Minimum F1 = 0.5")

    for bar, f1 in zip(bars, f1s):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, height + 0.02,
                f"{f1:.2f}", ha="center", va="bottom", fontsize=10, fontweight="bold",
                color=TEXT_DARK)

    ax.legend(loc="lower right", fontsize=10)
    ax.grid(True, alpha=0.3, axis="y", color=GRID)
    savefig("09_f1_by_category.png")


# ---------------------------------------------------------------------------
# 10. 防御架构流程图
# ---------------------------------------------------------------------------
def plot_defense_pipeline():
    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor(WHITE)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")

    ax.text(5, 4.5, "RAGShield 三层纵深防御流程", fontsize=16, fontweight="bold",
            ha="center", color=TEXT_DARK)

    boxes = [
        (1.5, 2.5, "L1 知识库层\nOutlierDetector", COLOR_L1,
         f"Avg Score: {np.mean([r['l1_score'] for r in detect if r['expected']!='safe']):.3f}"),
        (5, 2.5, "L2 检索层\nAttentionAnalyzer", COLOR_L2,
         f"Avg Score: {np.mean([r['l2_score'] for r in detect if r['expected']!='safe']):.3f}"),
        (8.5, 2.5, "L3 生成层\nConsistencyChecker", COLOR_L3,
         f"Avg Score: {np.mean([r['l3_score'] for r in detect if r['expected']!='safe']):.3f}"),
    ]

    for x, y, title, color, subtitle in boxes:
        rect = FancyBboxPatch((x - 1.2, y - 0.8), 2.4, 1.6, boxstyle="round,pad=0.03",
                              facecolor=color, alpha=0.1, edgecolor=color, linewidth=2, zorder=2)
        ax.add_patch(rect)
        ax.text(x, y + 0.2, title, ha="center", va="center",
                fontsize=11, fontweight="bold", color=color, zorder=3)
        ax.text(x, y - 0.35, subtitle, ha="center", va="center",
                fontsize=9, color=TEXT_MUTED, zorder=3)

    arrow_style = dict(arrowstyle="->", color=TEXT_MUTED, lw=2)
    ax.annotate("", xy=(3.3, 2.5), xytext=(2.7, 2.5), arrowprops=arrow_style)
    ax.annotate("", xy=(6.8, 2.5), xytext=(6.2, 2.5), arrowprops=arrow_style)

    outputs = [
        (1.5, 1.0, "Safe Pass", COLOR_SAFE),
        (5, 1.0, "Warning", COLOR_WARN),
        (8.5, 1.0, "Block", COLOR_DANGER),
    ]
    for x, y, text, color in outputs:
        rect = FancyBboxPatch((x - 0.7, y - 0.25), 1.4, 0.5,
                              facecolor=color, alpha=0.85, edgecolor="none", zorder=2)
        ax.add_patch(rect)
        tc = WHITE if text in ("Safe Pass", "Block") else TEXT_DARK
        ax.text(x, y, text, ha="center", va="center",
                fontsize=10, fontweight="bold", color=tc, zorder=3)

    ax.text(5, 0.2, "Risk Fusion Engine 综合决策", ha="center", va="center",
            fontsize=10, color=TEXT_MUTED, style="italic")

    savefig("10_defense_pipeline.png")


# ---------------------------------------------------------------------------
# 11. PHYSICAL vs DETECT 柱状对比
# ---------------------------------------------------------------------------
def plot_mode_comparison():
    metrics = ["准确率", "检测率", "1-误报率", "1-漏报率", "安全准确率"]
    d_vals = [
        metrics_detect["accuracy"], metrics_detect["detection_rate"],
        1 - metrics_detect["false_positive_rate"], 1 - metrics_detect["false_negative_rate"],
        metrics_detect["safe_accuracy"],
    ]
    p_vals = [
        metrics_physical["accuracy"], 1.0,
        1 - metrics_physical["false_positive_rate"], 1.0,
        metrics_physical.get("safe_accuracy", 0.975),
    ]

    x = np.arange(len(metrics))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)
    ax.tick_params(colors=TEXT_MUTED)
    for spine in ax.spines.values():
        spine.set_color(GRID)

    ax.bar(x - width / 2, d_vals, width, label="DETECT", color=COLOR_L1, alpha=0.85)
    ax.bar(x + width / 2, p_vals, width, label="PHYSICAL", color=COLOR_L2, alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontsize=11, color=TEXT_DARK)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Score", fontsize=12)
    ax.set_title("PHYSICAL vs DETECT Mode Comparison", fontsize=14, fontweight="bold")
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, axis="y", color=GRID)

    for i, (d, p) in enumerate(zip(d_vals, p_vals)):
        ax.text(i - width / 2, d + 0.02, f"{d:.2f}", ha="center", va="bottom",
                fontsize=9, color=TEXT_DARK, fontweight="bold")
        ax.text(i + width / 2, p + 0.02, f"{p:.2f}", ha="center", va="bottom",
                fontsize=9, color=TEXT_DARK, fontweight="bold")

    savefig("11_mode_comparison_bar.png")


# ---------------------------------------------------------------------------
# 组合图拼接 (白色背景)
# ---------------------------------------------------------------------------
def merge_pair(left_name, right_name, out_name, gap=40):
    left = Image.open(OUTDIR / left_name)
    right = Image.open(OUTDIR / right_name)
    target_h = max(left.height, right.height)
    if left.height != target_h:
        ratio = target_h / left.height
        left = left.resize((int(left.width * ratio), target_h), Image.LANCZOS)
    if right.height != target_h:
        ratio = target_h / right.height
        right = right.resize((int(right.width * ratio), target_h), Image.LANCZOS)
    total_w = left.width + gap + right.width
    canvas = Image.new("RGB", (total_w, target_h), (255, 255, 255))
    canvas.paste(left, (0, 0))
    canvas.paste(right, (left.width + gap, 0))
    canvas.save(OUTDIR / out_name, quality=95)
    print(f"[OK] {out_name}  ({total_w}x{target_h})")


def merge_trio(top_name, mid_name, bot_name, out_name, gap=30):
    imgs = [Image.open(OUTDIR / n) for n in [top_name, mid_name, bot_name]]
    target_w = max(i.width for i in imgs)
    scaled = []
    for img in imgs:
        if img.width != target_w:
            ratio = target_w / img.width
            scaled.append(img.resize((target_w, int(img.height * ratio)), Image.LANCZOS))
        else:
            scaled.append(img)
    total_h = sum(i.height for i in scaled) + gap * 2
    canvas = Image.new("RGB", (target_w, total_h), (255, 255, 255))
    y = 0
    for img in scaled:
        canvas.paste(img, (0, y))
        y += img.height + gap
    canvas.save(OUTDIR / out_name, quality=95)
    print(f"[OK] {out_name}  ({target_w}x{total_h})")


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Generating white-background report figures...")

    # 单图
    draw_system_architecture()
    plot_roc()
    plot_pr()
    plot_confusion()
    plot_layer_contribution()
    plot_attack_heatmap()
    plot_radar()
    plot_risk_distribution()
    plot_latency()
    plot_f1_by_category()
    plot_defense_pipeline()
    plot_mode_comparison()

    print("\nMerging into combined figures (white background)...")

    # A: ROC + PR
    merge_pair("01_roc_auc_curve.png", "02_precision_recall_f1.png",
               "A_classification_performance.png")

    # B: 雷达图 + 柱状对比
    merge_pair("06_mode_radar.png", "11_mode_comparison_bar.png",
               "B_mode_comparison.png")

    # C: 热力图 + F1
    merge_pair("05_attack_detection_heatmap.png", "09_f1_by_category.png",
               "C_attack_analysis.png")

    # D: 三层贡献 + 防御流程
    merge_pair("04_layer_contribution.png", "10_defense_pipeline.png",
               "D_architecture.png")

    # E: 风险分布 + 延迟箱线
    merge_pair("07_risk_score_distribution.png", "08_latency_boxplot.png",
               "E_data_distribution.png")

    # F: 混淆矩阵 (单独保留)
    cm = Image.open(OUTDIR / "03_confusion_matrix.png")
    cm.save(OUTDIR / "F_confusion_matrix.png", quality=95)
    print(f"[OK] F_confusion_matrix.png  ({cm.width}x{cm.height})")

    print(f"\nAll white-background figures saved to {OUTDIR.resolve()}")
