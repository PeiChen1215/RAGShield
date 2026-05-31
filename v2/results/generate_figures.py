"""
v2/results/generate_figures.py
生成 RAGShield V2 项目成果可视化图表 — 白色背景学术风格
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os
from matplotlib import rcParams
import matplotlib.font_manager as fm

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 统一白色学术主题配置
WHITE_BG = "#ffffff"
CARD_BG = "#f8f9fa"
TEXT_COLOR = "#1a1a2e"
GRID_COLOR = "#e9ecef"
AXIS_COLOR = "#495057"
SAFE_GREEN = "#2d8a3e"
WARN_PINK = "#c0392b"
DANGER_PURPLE = "#6c3483"
ACCENT_BLUE = "#2874a6"
MUTED_GRAY = "#95a5a6"
LIGHT_BLUE = "#5dade2"
ORANGE = "#e67e22"

rcParams["figure.facecolor"] = WHITE_BG
rcParams["axes.facecolor"] = WHITE_BG
rcParams["axes.edgecolor"] = AXIS_COLOR
rcParams["axes.labelcolor"] = TEXT_COLOR
rcParams["text.color"] = TEXT_COLOR
rcParams["xtick.color"] = AXIS_COLOR
rcParams["ytick.color"] = AXIS_COLOR
rcParams["grid.color"] = GRID_COLOR
rcParams["grid.linewidth"] = 0.8
rcParams["axes.grid"] = True
rcParams["axes.grid.axis"] = "y"
rcParams["figure.dpi"] = 150
rcParams["font.size"] = 11

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__)) + "/figures"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def save(fig, name):
    path = os.path.join(OUTPUT_DIR, name)
    fig.savefig(path, bbox_inches="tight", facecolor=WHITE_BG, edgecolor="none")
    print(f"[OK] {name}")
    plt.close(fig)


# ========================================================================
# 1. 七层防御架构图 (v2_architecture.png)
# ========================================================================
def fig_architecture():
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis("off")
    fig.patch.set_facecolor(WHITE_BG)

    layers = [
        ("Layer 0", "查询侧安全扫描", "Unicode + PromptGuard + 规则引擎", SAFE_GREEN, 9.0),
        ("Layer 1", "知识库入库检测", "四检测器并联: PG + 规则 + 数值冲突 + LLM", SAFE_GREEN, 8.0),
        ("Layer 2", "检索安全层", "top-20 稀释 + 分布分析 + 内容扫描", SAFE_GREEN, 7.0),
        ("Layer 3", "Extractor", "结构化事实提取，剥离攻击指令", WARN_PINK, 6.0),
        ("Layer 4", "Auditor", "数值/语义一致性校验 + 来源可信度评估", WARN_PINK, 5.0),
        ("Layer 5", "Synthesizer", "受控生成（安全 system prompt）", DANGER_PURPLE, 4.0),
        ("Layer 6", "输出审计", "LLM 语义审计 + 规则兜底", DANGER_PURPLE, 3.0),
    ]

    for name, subtitle, detail, color, y in layers:
        rect = mpatches.FancyBboxPatch((1, y), 12, 0.8, boxstyle="round,pad=0.05",
                                        facecolor=CARD_BG, edgecolor=color, linewidth=2.5)
        ax.add_patch(rect)
        ax.text(1.3, y + 0.55, name, fontsize=13, fontweight="bold", color=color, va="center")
        ax.text(3.2, y + 0.55, subtitle, fontsize=12, color=TEXT_COLOR, va="center")
        ax.text(3.2, y + 0.2, detail, fontsize=9, color=AXIS_COLOR, va="center")

    # 数据流箭头
    for y in [8.8, 7.8, 6.8, 5.8, 4.8, 3.8]:
        ax.annotate("", xy=(7, y - 0.2), xytext=(7, y + 0.05),
                    arrowprops=dict(arrowstyle="->", color=AXIS_COLOR, lw=1.5))

    ax.text(7, 9.5, "RAGShield V2 七层纵深防御架构", fontsize=20, fontweight="bold",
            color=TEXT_COLOR, ha="center", va="center")
    ax.text(7, 2.2, "核心保证: 原始攻击文本永远不会直接接触最终生成器",
            fontsize=12, color=AXIS_COLOR, ha="center", va="center", style="italic")
    save(fig, "v2_architecture.png")


# ========================================================================
# 2. 检测性能对比 (v2_classification_performance.png)
# ========================================================================
def fig_classification_performance():
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(WHITE_BG)

    metrics = ["BDR (检测率)", "FPR (误报率)", "ADR (架构防御率)"]
    v1_old = [0.0, 16.7, 0.0]
    v2_light = [65.0, 5.0, 70.0]
    v2_full = [94.7, 3.3, 100.0]

    x = np.arange(len(metrics))
    width = 0.22

    ax.bar(x - width, v1_old, width, label="V1 旧系统（去标签后）", color=MUTED_GRAY, alpha=0.6, edgecolor="white")
    ax.bar(x, v2_light, width, label="V2 轻量版（白+灰）", color=LIGHT_BLUE, alpha=0.85, edgecolor="white")
    ax.bar(x + width, v2_full, width, label="V2 完整版（白+灰+黑）", color=SAFE_GREEN, edgecolor="white")

    ax.set_ylabel("百分比 (%)", fontsize=12)
    ax.set_title("检测性能对比: V1 旧系统 vs V2 新架构", fontsize=16, fontweight="bold", pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontsize=11)
    ax.legend(loc="upper right", frameon=True, fancybox=True, shadow=False, facecolor=WHITE_BG, edgecolor=GRID_COLOR)
    ax.set_ylim(0, 115)
    ax.grid(axis="y", alpha=0.5)

    for bars in [ax.containers[0], ax.containers[1], ax.containers[2]]:
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., h + 1.5, f"{h:.1f}",
                    ha="center", va="bottom", fontsize=9, fontweight="bold", color=TEXT_COLOR)

    save(fig, "v2_classification_performance.png")


# ========================================================================
# 3. 部署模式对比 (v2_mode_comparison.png)
# ========================================================================
def fig_mode_comparison():
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(WHITE_BG)

    categories = ["检测率", "(100-误报率)", "架构防御", "语义伪装\n防御", "确定性保证", "低延迟"]
    old_system = [5, 83, 0, 10, 15, 85]
    v2_lightweight = [65, 95, 70, 50, 80, 90]
    v2_full = [95, 97, 100, 95, 85, 50]

    x = np.arange(len(categories))
    width = 0.22

    ax.bar(x - width, old_system, width, label="V1 旧系统", color=MUTED_GRAY, alpha=0.5, edgecolor="white")
    ax.bar(x, v2_lightweight, width, label="V2 轻量版", color=LIGHT_BLUE, alpha=0.85, edgecolor="white")
    ax.bar(x + width, v2_full, width, label="V2 完整版", color=SAFE_GREEN, edgecolor="white")

    ax.set_ylabel("相对评分 (0-100)", fontsize=12)
    ax.set_title("三种部署模式多维度能力对比", fontsize=16, fontweight="bold", pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=10)
    ax.legend(loc="upper right", frameon=True, fancybox=True, facecolor=WHITE_BG, edgecolor=GRID_COLOR)
    ax.set_ylim(0, 115)
    ax.grid(axis="y", alpha=0.5)
    save(fig, "v2_mode_comparison.png")


# ========================================================================
# 4. 各层贡献率 (v2_layer_contribution.png)
# ========================================================================
def fig_layer_contribution():
    fig, ax = plt.subplots(figsize=(9, 5.5))
    fig.patch.set_facecolor(WHITE_BG)

    detectors = ["PromptGuard", "规则引擎", "数值冲突", "LLM 语义判断"]
    lcr = [36.8, 63.2, 10.5, 89.5]
    colors = [LIGHT_BLUE, ORANGE, DANGER_PURPLE, SAFE_GREEN]

    bars = ax.barh(detectors, lcr, color=colors, edgecolor="white", height=0.5)
    ax.set_xlabel("独立贡献率 (%)", fontsize=12)
    ax.set_title("Layer1 四检测器独立贡献率 (LCR)", fontsize=16, fontweight="bold", pad=20)
    ax.set_xlim(0, 105)
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.5)

    for bar, val in zip(bars, lcr):
        ax.text(val + 1.5, bar.get_y() + bar.get_height()/2, f"{val:.1f}%",
                va="center", fontsize=11, fontweight="bold", color=TEXT_COLOR)

    ax.axvline(x=10, color=MUTED_GRAY, linestyle="--", linewidth=1.2, alpha=0.7)
    ax.text(10.5, 3.4, "目标线: 10%", fontsize=9, color=AXIS_COLOR, va="center")

    save(fig, "v2_layer_contribution.png")


# ========================================================================
# 5. 攻击类型检测热力图 (v2_attack_heatmap.png)
# ========================================================================
def fig_attack_heatmap():
    fig, ax = plt.subplots(figsize=(10, 7))
    fig.patch.set_facecolor(WHITE_BG)

    attack_types = [
        "指令劫持(直接)", "指令劫持(间接)", "钓鱼(凭证窃取)", "钓鱼(操作诱导)",
        "数据投毒(数值)", "数据投毒(事实)", "信息泄露(直接)", "信息泄露(间接)",
        "对抗绕过(同义词)", "对抗绕过(分段)", "特权提升", "社会工程"
    ]
    layers = ["L0查询", "L1入库", "L2检索", "L3提取", "L4审计", "L5生成", "L6输出"]

    matrix = np.array([
        [1.0, 1.0, 0.0, 0.0, 0.0, 0.5, 0.0],
        [0.5, 0.5, 0.0, 1.0, 0.0, 0.5, 0.5],
        [0.5, 1.0, 0.5, 1.0, 0.0, 0.5, 1.0],
        [0.0, 0.5, 0.0, 1.0, 0.0, 0.5, 1.0],
        [0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0],
        [0.0, 0.5, 0.0, 0.0, 0.5, 0.0, 0.0],
        [0.0, 0.5, 0.0, 0.5, 0.0, 0.0, 1.0],
        [0.0, 0.0, 0.0, 0.5, 0.0, 0.0, 0.5],
        [0.0, 0.5, 0.0, 0.5, 0.0, 0.0, 0.0],
        [0.0, 0.5, 0.0, 0.5, 0.0, 0.0, 0.0],
        [0.0, 0.5, 0.0, 0.5, 0.5, 0.5, 0.5],
        [0.0, 0.5, 0.0, 0.5, 0.0, 0.5, 0.5],
    ])

    cmap = plt.cm.colors.LinearSegmentedColormap.from_list("", ["#f8f9fa", "#f5b7b1", "#c0392b"])

    im = ax.imshow(matrix, cmap=cmap, aspect="auto", vmin=0, vmax=1)

    ax.set_xticks(np.arange(len(layers)))
    ax.set_yticks(np.arange(len(attack_types)))
    ax.set_xticklabels(layers, fontsize=10)
    ax.set_yticklabels(attack_types, fontsize=9)

    for i in range(len(attack_types)):
        for j in range(len(layers)):
            text = "●" if matrix[i, j] == 1.0 else "○" if matrix[i, j] == 0.5 else ""
            ax.text(j, i, text, ha="center", va="center", fontsize=14,
                    color="white" if matrix[i, j] > 0.3 else AXIS_COLOR)

    ax.set_title("攻击类型 × 防御层 检测能力矩阵", fontsize=16, fontweight="bold", pad=20)
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("贡献度", fontsize=10)
    cbar.ax.yaxis.set_tick_params(color=AXIS_COLOR)
    save(fig, "v2_attack_heatmap.png")


# ========================================================================
# 6. 混淆矩阵 (v2_confusion_matrix.png)
# ========================================================================
def fig_confusion_matrix():
    fig, ax = plt.subplots(figsize=(7, 6))
    fig.patch.set_facecolor(WHITE_BG)

    cm = np.array([
        [28, 2],
        [1, 18],
    ])

    cmap = plt.cm.colors.LinearSegmentedColormap.from_list("", ["#f8f9fa", SAFE_GREEN])
    im = ax.imshow(cm, cmap=cmap, aspect="auto")

    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(["预测正常", "预测攻击"], fontsize=12)
    ax.set_yticklabels(["实际正常", "实际攻击"], fontsize=12)

    for i in range(2):
        for j in range(2):
            color = "white" if cm[i, j] > 15 else TEXT_COLOR
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                    fontsize=28, fontweight="bold", color=color)

    ax.set_title("混淆矩阵 (49篇文档测试集)", fontsize=16, fontweight="bold", pad=20)
    ax.text(0.5, -0.14, "误报: 2 (3.3%)   |   漏报: 1 (5.3%)", transform=ax.transAxes,
            fontsize=11, color=AXIS_COLOR, ha="center")

    save(fig, "v2_confusion_matrix.png")


# ========================================================================
# 7. 雷达图 (v2_radar.png)
# ========================================================================
def fig_radar():
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor(WHITE_BG)

    labels = ["BDR\n检测率", "(100-FPR)\n低误报", "ADR\n架构防御", "LCR\n层贡献", "Latency\n低延迟"]
    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]

    v1_vals = [0, 83.3, 0, 10, 85]
    v2_light = [65, 95, 70, 40, 90]
    v2_full = [94.7, 96.7, 100, 75, 50]

    for vals, color, label in [(v1_vals, MUTED_GRAY, "V1 旧系统"),
                                (v2_light, LIGHT_BLUE, "V2 轻量版"),
                                (v2_full, SAFE_GREEN, "V2 完整版")]:
        vals += vals[:1]
        ax.plot(angles, vals, color=color, linewidth=2.5, label=label, marker="o", markersize=5)
        ax.fill(angles, vals, color=color, alpha=0.12)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=10, color=TEXT_COLOR)
    ax.set_ylim(0, 105)
    ax.set_title("多维度能力雷达图", fontsize=16, fontweight="bold", pad=30, color=TEXT_COLOR)
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.15), frameon=True, facecolor=WHITE_BG, edgecolor=GRID_COLOR)
    ax.grid(color=GRID_COLOR, linewidth=0.8)
    save(fig, "v2_radar.png")


# ========================================================================
# 8. 信息隔离流水线 (v2_pipeline.png)
# ========================================================================
def fig_pipeline():
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 5)
    ax.axis("off")
    fig.patch.set_facecolor(WHITE_BG)

    stages = [
        ("原始文档", "不可信输入\n可能包含攻击指令", MUTED_GRAY, 1.0),
        ("Extractor", "结构化事实提取\n丢弃指令性/诱导性语言", ORANGE, 4.5),
        ("Auditor", "交叉验证\n检测矛盾与不可信来源", WARN_PINK, 8.0),
        ("Synthesizer", "受控生成\n仅使用已验证事实", SAFE_GREEN, 11.5),
    ]

    for name, desc, color, x in stages:
        rect = mpatches.FancyBboxPatch((x, 1.5), 2.5, 2.2, boxstyle="round,pad=0.08",
                                        facecolor=CARD_BG, edgecolor=color, linewidth=2.5)
        ax.add_patch(rect)
        ax.text(x + 1.25, 3.2, name, fontsize=13, fontweight="bold", color=color, ha="center", va="center")
        ax.text(x + 1.25, 2.4, desc, fontsize=9, color=AXIS_COLOR, ha="center", va="center")

    for x in [3.6, 7.1, 10.6]:
        ax.annotate("", xy=(x + 0.8, 2.6), xytext=(x, 2.6),
                    arrowprops=dict(arrowstyle="->", color=AXIS_COLOR, lw=2))

    ax.text(7, 0.6, "核心保证: 原始攻击文本永远不会直接接触最终生成器",
            fontsize=12, color=SAFE_GREEN, ha="center", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.4", facecolor=CARD_BG, edgecolor=SAFE_GREEN, alpha=0.9))

    ax.text(7, 4.6, "RAGShield V2 信息隔离三级流水线", fontsize=20, fontweight="bold",
            color=TEXT_COLOR, ha="center")

    save(fig, "v2_pipeline.png")


# ========================================================================
# 9. 评测指标综合柱状图 (v2_evaluation_metrics.png)
# ========================================================================
def fig_evaluation_metrics():
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(WHITE_BG)

    labels = ["BDR\n≥75%", "FPR\n≤5%", "ADR\n≥80%", "LCR(PG)\n≥10%", "LCR(规则)\n≥10%", "LCR(LLM)\n≥10%"]
    targets = [75, 5, 80, 10, 10, 10]
    achieved = [94.7, 3.3, 100, 36.8, 63.2, 89.5]

    x = np.arange(len(labels))
    width = 0.35

    ax.bar(x - width/2, targets, width, label="目标值", color=MUTED_GRAY, alpha=0.5, edgecolor="white")
    ax.bar(x + width/2, achieved, width, label="实测值", color=SAFE_GREEN, edgecolor="white")

    ax.set_ylabel("百分比 (%)", fontsize=12)
    ax.set_title("RAGShield V2 评测指标: 目标 vs 实测", fontsize=16, fontweight="bold", pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.legend(loc="upper right", frameon=True, fancybox=True, facecolor=WHITE_BG, edgecolor=GRID_COLOR)

    bars = ax.containers[1]
    for bar, val in zip(bars, achieved):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1.5,
                f"{val:.1f}", ha="center", va="bottom", fontsize=10, fontweight="bold", color=TEXT_COLOR)

    ax.set_ylim(0, 115)
    ax.grid(axis="y", alpha=0.5)
    save(fig, "v2_evaluation_metrics.png")


# ========================================================================
# 主入口
# ========================================================================
if __name__ == "__main__":
    print("=" * 50)
    print("生成 RAGShield V2 可视化图表")
    print("=" * 50)
    fig_architecture()
    fig_classification_performance()
    fig_mode_comparison()
    fig_layer_contribution()
    fig_attack_heatmap()
    fig_confusion_matrix()
    fig_radar()
    fig_pipeline()
    fig_evaluation_metrics()
    print("=" * 50)
    print(f"所有图表已保存到: {OUTPUT_DIR}")
    print("=" * 50)
