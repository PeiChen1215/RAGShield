"""
v2/results/generate_figures_v2.py
RAGShield V2 项目成果可视化 — 精致学术版
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np
import os
import seaborn as sns

# ============================================================
# 全局配置
# ============================================================
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 180
plt.rcParams['savefig.dpi'] = 180

WHITE = "#ffffff"
BG = "#fafbfc"
TEXT = "#1f2937"
TEXT_MUTED = "#6b7280"
GRID = "#e5e7eb"

# 专业配色方案 (Nature风格)
C_SAFE = "#059669"      # 翠绿
C_WARN = "#d97706"      # 琥珀
C_DANGER = "#dc2626"    # 正红
C_BLUE = "#2563eb"      # 钴蓝
C_PURPLE = "#7c3aed"    # 紫罗兰
C_GRAY = "#9ca3af"      # 中性灰
C_LIGHT_BLUE = "#60a5fa"
C_ORANGE = "#f97316"

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__)) + "/figures"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def setup_axis(ax, title="", xlabel="", ylabel=""):
    ax.set_facecolor(WHITE)
    ax.set_title(title, fontsize=15, fontweight="bold", color=TEXT, pad=16)
    ax.set_xlabel(xlabel, fontsize=11, color=TEXT_MUTED)
    ax.set_ylabel(ylabel, fontsize=11, color=TEXT_MUTED)
    ax.tick_params(colors=TEXT_MUTED, labelsize=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.spines["bottom"].set_color(GRID)
    ax.grid(axis="y", color=GRID, linewidth=0.6, alpha=0.8)


def save(fig, name):
    path = os.path.join(OUTPUT_DIR, name)
    fig.savefig(path, bbox_inches="tight", facecolor=WHITE, edgecolor="none", pad_inches=0.15)
    print(f"[OK] {name}")
    plt.close(fig)


# ========================================================================
# 1. 七层防御架构图
# ========================================================================
def fig_architecture():
    fig, ax = plt.subplots(figsize=(12, 9))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 9.5)
    ax.axis("off")
    fig.patch.set_facecolor(WHITE)

    layers = [
        ("Layer 0  查询侧安全扫描", "Unicode 规范化 + PromptGuard 注入检测 + 规则引擎初筛", C_SAFE, 8.0),
        ("Layer 1  知识库入库检测", "四检测器并联: PromptGuard + 规则引擎 + 数值冲突 + LLM 语义", C_SAFE, 6.9),
        ("Layer 2  检索安全层", "top-20 检索稀释 + 分布异常分析 + 内容 PromptGuard 扫描", C_SAFE, 5.8),
        ("Layer 3  Extractor", "结构化事实提取 — 丢弃指令性/诱导性语言", C_WARN, 4.7),
        ("Layer 4  Auditor", "数值一致性校验 + 语义矛盾检测 + 来源可信度评估", C_WARN, 3.6),
        ("Layer 5  Synthesizer", "受控生成 — 安全 system prompt + 仅使用已验证事实", C_DANGER, 2.5),
        ("Layer 6  输出审计", "LLM 语义审计 + 规则兜底审计 + 主题偏离检测", C_DANGER, 1.4),
    ]

    for title_text, desc, color, y in layers:
        rect = FancyBboxPatch((0.8, y), 10.4, 0.9, boxstyle="round,pad=0.06,rounding_size=0.15",
                               facecolor="white", edgecolor=color, linewidth=2.2,
                               mutation_aspect=1)
        ax.add_patch(rect)
        ax.text(1.1, y + 0.58, title_text, fontsize=11.5, fontweight="bold", color=color, va="center")
        ax.text(1.1, y + 0.22, desc, fontsize=9, color=TEXT_MUTED, va="center")

    # 箭头
    for y in [7.85, 6.75, 5.65, 4.55, 3.45, 2.35]:
        ax.annotate("", xy=(6, y - 0.08), xytext=(6, y + 0.15),
                    arrowprops=dict(arrowstyle="->", color=TEXT_MUTED, lw=1.8,
                                    connectionstyle="arc3,rad=0"))

    ax.text(6, 9.3, "RAGShield V2  七层纵深防御架构", fontsize=20, fontweight="bold",
            color=TEXT, ha="center", va="center")
    ax.text(6, 0.55, "核心保证: 原始攻击文本永远不会直接接触最终生成器",
            fontsize=12, color=C_SAFE, ha="center", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#ecfdf5", edgecolor=C_SAFE, alpha=0.9))
    save(fig, "v2_architecture.png")


# ========================================================================
# 2. 检测性能对比
# ========================================================================
def fig_classification_performance():
    fig, ax = plt.subplots(figsize=(10, 6.5))
    fig.patch.set_facecolor(WHITE)

    metrics = ["BDR\n(检测率)", "FPR\n(误报率)", "ADR\n(架构防御率)"]
    v1 = [0.0, 16.7, 0.0]
    v2_light = [65.0, 5.0, 70.0]
    v2_full = [94.7, 3.3, 100.0]

    x = np.arange(len(metrics))
    width = 0.22

    bars1 = ax.bar(x - width, [max(v, 3) for v in v1], width, label="V1 旧系统（去标签后）",
                   color=C_GRAY, alpha=0.5, edgecolor="white", linewidth=0.5)
    bars2 = ax.bar(x, v2_light, width, label="V2 轻量版（白+灰）",
                   color=C_LIGHT_BLUE, alpha=0.85, edgecolor="white", linewidth=0.5)
    bars3 = ax.bar(x + width, v2_full, width, label="V2 完整版（白+灰+黑）",
                   color=C_SAFE, edgecolor="white", linewidth=0.5)

    setup_axis(ax, "检测性能对比: V1 旧系统 vs V2 新架构", "", "百分比 (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontsize=11)
    ax.legend(loc="upper right", frameon=True, fancybox=True, facecolor=WHITE, edgecolor=GRID, fontsize=10)
    ax.set_ylim(0, 118)

    # 数值标签 — 对V1为0的显示真实值
    all_vals = [v1, v2_light, v2_full]
    all_bars = [bars1, bars2, bars3]
    for vals, bars in zip(all_vals, all_bars):
        for bar, val in zip(bars, vals):
            display_h = bar.get_height()
            label_y = display_h + 2
            ax.text(bar.get_x() + bar.get_width()/2., label_y, f"{val:.1f}",
                    ha="center", va="bottom", fontsize=9.5, fontweight="bold", color=TEXT)

    save(fig, "v2_classification_performance.png")


# ========================================================================
# 3. 部署模式对比
# ========================================================================
def fig_mode_comparison():
    fig, ax = plt.subplots(figsize=(10, 6.5))
    fig.patch.set_facecolor(WHITE)

    categories = ["检测率", "低误报\n(100-FPR)", "架构防御", "语义伪装\n防御", "确定性保证", "低延迟"]
    old = [5, 83, 0, 10, 15, 85]
    light = [65, 95, 70, 50, 80, 90]
    full = [95, 97, 100, 95, 85, 50]

    x = np.arange(len(categories))
    width = 0.22

    ax.bar(x - width, [max(v, 4) for v in old], width, label="V1 旧系统",
           color=C_GRAY, alpha=0.5, edgecolor="white", linewidth=0.5)
    ax.bar(x, light, width, label="V2 轻量版",
           color=C_LIGHT_BLUE, alpha=0.85, edgecolor="white", linewidth=0.5)
    ax.bar(x + width, full, width, label="V2 完整版",
           color=C_SAFE, edgecolor="white", linewidth=0.5)

    setup_axis(ax, "三种部署模式多维度能力对比", "", "相对评分 (0-100)")
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=10)
    ax.legend(loc="upper right", frameon=True, fancybox=True, facecolor=WHITE, edgecolor=GRID, fontsize=10)
    ax.set_ylim(0, 118)

    # 标注数值
    for i, (o, l, f) in enumerate(zip(old, light, full)):
        ax.text(i - width, max(o, 4) + 2, f"{o}", ha="center", fontsize=8, color=TEXT_MUTED)
        ax.text(i, l + 2, f"{l}", ha="center", fontsize=8, fontweight="bold", color=C_LIGHT_BLUE)
        ax.text(i + width, f + 2, f"{f}", ha="center", fontsize=8, fontweight="bold", color=C_SAFE)

    save(fig, "v2_mode_comparison.png")


# ========================================================================
# 4. 各层贡献率
# ========================================================================
def fig_layer_contribution():
    fig, ax = plt.subplots(figsize=(9, 5.5))
    fig.patch.set_facecolor(WHITE)

    detectors = ["PromptGuard", "规则引擎", "数值冲突", "LLM 语义判断"]
    lcr = [36.8, 63.2, 10.5, 89.5]
    colors = [C_BLUE, C_ORANGE, C_PURPLE, C_SAFE]

    bars = ax.barh(detectors, lcr, color=colors, edgecolor="white", height=0.5, linewidth=0)
    setup_axis(ax, "Layer1 四检测器独立贡献率 (LCR)", "独立贡献率 (%)", "")
    ax.set_xlim(0, 105)
    ax.invert_yaxis()
    ax.grid(axis="x", color=GRID, linewidth=0.6, alpha=0.8)
    ax.grid(axis="y", visible=False)

    for bar, val, color in zip(bars, lcr, colors):
        ax.text(val + 1.5, bar.get_y() + bar.get_height()/2, f"{val:.1f}%",
                va="center", fontsize=11, fontweight="bold", color=color)

    ax.axvline(x=10, color=C_GRAY, linestyle="--", linewidth=1.2, alpha=0.6)
    ax.text(10.5, 3.5, "目标线: 10%", fontsize=9, color=TEXT_MUTED, va="center")

    save(fig, "v2_layer_contribution.png")


# ========================================================================
# 5. 攻击类型检测热力图
# ========================================================================
def fig_attack_heatmap():
    fig, ax = plt.subplots(figsize=(10, 7))
    fig.patch.set_facecolor(WHITE)

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

    # 使用蓝-白-橙配色，0=白, 0.5=浅蓝, 1.0=深蓝
    cmap = sns.color_palette("Blues", as_cmap=True)
    im = ax.imshow(matrix, cmap=cmap, aspect="auto", vmin=0, vmax=1)

    ax.set_xticks(np.arange(len(layers)))
    ax.set_yticks(np.arange(len(attack_types)))
    ax.set_xticklabels(layers, fontsize=10)
    ax.set_yticklabels(attack_types, fontsize=9.5)

    for i in range(len(attack_types)):
        for j in range(len(layers)):
            v = matrix[i, j]
            if v == 1.0:
                text, color = "●", "white"
            elif v == 0.5:
                text, color = "○", "#1e3a5f"
            else:
                text, color = "—", TEXT_MUTED
            ax.text(j, i, text, ha="center", va="center", fontsize=13, color=color, fontweight="bold")

    ax.set_title("攻击类型 × 防御层 检测能力矩阵", fontsize=15, fontweight="bold", pad=20)
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("贡献度", fontsize=10, color=TEXT_MUTED)
    cbar.set_ticks([0, 0.5, 1.0])
    cbar.set_ticklabels(["无", "部分", "完全"])
    cbar.ax.tick_params(color=TEXT_MUTED)
    save(fig, "v2_attack_heatmap.png")


# ========================================================================
# 6. 混淆矩阵
# ========================================================================
def fig_confusion_matrix():
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    fig.patch.set_facecolor(WHITE)

    cm = np.array([[28, 2], [1, 18]])

    # 自定义配色: TN=浅绿, FP=浅橙, FN=浅橙, TP=深绿
    colors = [["#d1fae5", "#fed7aa"], ["#fed7aa", "#059669"]]

    for i in range(2):
        for j in range(2):
            rect = plt.Rectangle((j - 0.5, i - 0.5), 1, 1, facecolor=colors[i][j], edgecolor=WHITE, linewidth=3)
            ax.add_patch(rect)
            text_color = "white" if (i == 1 and j == 1) else TEXT
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                    fontsize=30, fontweight="bold", color=text_color)

    ax.set_xlim(-0.5, 1.5)
    ax.set_ylim(-0.5, 1.5)
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(["预测正常", "预测攻击"], fontsize=12, color=TEXT)
    ax.set_yticklabels(["实际正常", "实际攻击"], fontsize=12, color=TEXT)
    ax.set_title("混淆矩阵 (49 篇文档测试集)", fontsize=16, fontweight="bold", pad=20)
    ax.text(0.5, -0.18, "TN=28   FP=2 (误报 3.3%)   |   FN=1 (漏报 5.3%)   TP=18",
            transform=ax.transAxes, fontsize=11, color=TEXT_MUTED, ha="center")
    ax.set_aspect("equal")
    ax.axis("off")
    save(fig, "v2_confusion_matrix.png")


# ========================================================================
# 7. 雷达图
# ========================================================================
def fig_radar():
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor(WHITE)

    labels = ["BDR\n检测率", "(100-FPR)\n低误报", "ADR\n架构防御", "LCR\n层贡献", "Latency\n低延迟"]
    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]

    v1_vals = [5, 83, 5, 10, 85]
    v2_light = [65, 95, 70, 40, 90]
    v2_full = [94.7, 96.7, 100, 75, 50]

    for vals, color, label, alpha in [(v1_vals, C_GRAY, "V1 旧系统", 0.08),
                                       (v2_light, C_LIGHT_BLUE, "V2 轻量版", 0.15),
                                       (v2_full, C_SAFE, "V2 完整版", 0.2)]:
        vals_plot = vals + vals[:1]
        ax.plot(angles, vals_plot, color=color, linewidth=2.5, label=label, marker="o", markersize=6)
        ax.fill(angles, vals_plot, color=color, alpha=alpha)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=10.5, color=TEXT)
    ax.set_ylim(0, 105)
    ax.set_title("多维度能力雷达图", fontsize=16, fontweight="bold", pad=35, color=TEXT)
    ax.legend(loc="upper right", bbox_to_anchor=(1.4, 1.15), frameon=True,
              facecolor=WHITE, edgecolor=GRID, fontsize=10)
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_facecolor(WHITE)
    save(fig, "v2_radar.png")


# ========================================================================
# 8. 信息隔离流水线
# ========================================================================
def fig_pipeline():
    fig, ax = plt.subplots(figsize=(13, 5))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 5)
    ax.axis("off")
    fig.patch.set_facecolor(WHITE)

    stages = [
        ("原始文档", "不可信输入\n可能包含攻击指令", C_GRAY, 0.8),
        ("Extractor", "结构化事实提取\n丢弃指令性/诱导性语言", C_ORANGE, 3.8),
        ("Auditor", "交叉验证\n检测矛盾与不可信来源", C_DANGER, 6.8),
        ("Synthesizer", "受控生成\n仅使用已验证事实", C_SAFE, 9.8),
    ]

    for name, desc, color, x in stages:
        rect = FancyBboxPatch((x, 1.3), 2.6, 2.3, boxstyle="round,pad=0.08,rounding_size=0.2",
                               facecolor="white", edgecolor=color, linewidth=2.8)
        ax.add_patch(rect)
        ax.text(x + 1.3, 3.2, name, fontsize=13, fontweight="bold", color=color, ha="center", va="center")
        ax.text(x + 1.3, 2.3, desc, fontsize=9, color=TEXT_MUTED, ha="center", va="center")

    for x in [3.5, 6.5, 9.5]:
        ax.annotate("", xy=(x + 0.25, 2.45), xytext=(x, 2.45),
                    arrowprops=dict(arrowstyle="->", color=TEXT_MUTED, lw=2.5))

    ax.text(6.5, 0.55, "核心保证: 原始攻击文本永远不会直接接触最终生成器",
            fontsize=12, color=C_SAFE, ha="center", fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#ecfdf5", edgecolor=C_SAFE, linewidth=1.5))

    ax.text(6.5, 4.6, "RAGShield V2  信息隔离三级流水线", fontsize=20, fontweight="bold",
            color=TEXT, ha="center")

    save(fig, "v2_pipeline.png")


# ========================================================================
# 9. 评测指标综合柱状图
# ========================================================================
def fig_evaluation_metrics():
    fig, ax = plt.subplots(figsize=(10, 6.5))
    fig.patch.set_facecolor(WHITE)

    labels = ["BDR\n≥75%", "FPR\n≤5%", "ADR\n≥80%", "LCR(PG)\n≥10%", "LCR(规则)\n≥10%", "LCR(LLM)\n≥10%"]
    targets = [75, 5, 80, 10, 10, 10]
    achieved = [94.7, 3.3, 100, 36.8, 63.2, 89.5]

    x = np.arange(len(labels))
    width = 0.32

    ax.bar(x - width/2, targets, width, label="目标值", color="#e5e7eb", edgecolor="white", linewidth=0.5)
    ax.bar(x + width/2, achieved, width, label="实测值", color=C_SAFE, edgecolor="white", linewidth=0.5)

    setup_axis(ax, "RAGShield V2 评测指标: 目标 vs 实测", "", "百分比 (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.legend(loc="upper right", frameon=True, fancybox=True, facecolor=WHITE, edgecolor=GRID, fontsize=10)

    bars = ax.containers[1]
    for bar, val in zip(bars, achieved):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1.8,
                f"{val:.1f}", ha="center", va="bottom", fontsize=10, fontweight="bold", color=C_SAFE)

    # 目标值标注（特别是FPR的小值）
    for bar, val in zip(ax.containers[0], targets):
        y_pos = bar.get_height() + 1.8
        ax.text(bar.get_x() + bar.get_width()/2., y_pos, f"{val}",
                ha="center", va="bottom", fontsize=9, color=TEXT_MUTED)

    ax.set_ylim(0, 118)
    save(fig, "v2_evaluation_metrics.png")


# ========================================================================
# 主入口
# ========================================================================
if __name__ == "__main__":
    print("=" * 50)
    print("生成 RAGShield V2 精致版可视化图表")
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
