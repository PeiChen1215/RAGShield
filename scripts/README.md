# scripts/ 目录说明

> **更新日期**: 2026-05-25
> **用途**: 说明 `scripts/` 目录下各脚本的职责和分类

---

## 核心链路脚本（根目录）

这些是 RAGShield 全链路运行所必需的脚本，**答辩现场直接执行**：

| 脚本 | 职责 | 执行时机 |
|------|------|---------|
| `download_models.py` | 预下载 BGE/reranker/NLI 模型到 `./models/` | 环境初始化时 |
| `seed_data.py` | 一键生成 100 篇正常 + 25 篇攻击文档，导入到 ChromaDB | 每次重建知识库时 |
| `evaluate.py` | 完整评测主脚本：读取 47 条查询，输出检测率/误报率/延迟 | 验证系统效果时 |
| `threshold_sweep.py` | 阈值扫描：离线计算不同 warning/danger 阈值组合的指标 | 调参时 |
| `weight_ablation.py` | 权重消融：验证 0.3/0.3/0.4 权重配置的最优性 | 调参时 |
| `start.sh` | 启动 FastAPI + Gradio 服务 | 部署时 |

**使用示例**：
```bash
# 1. 下载模型
python scripts/download_models.py

# 2. 启动后端
bash scripts/start.sh

# 3. 导入数据（后端启动后执行）
python scripts/seed_data.py

# 4. 运行完整评测
python scripts/evaluate.py

# 5. 阈值扫描（离线）
python scripts/threshold_sweep.py

# 6. 权重消融（离线）
python scripts/weight_ablation.py
```

---

## archive/ — 临时调试脚本归档

开发过程中产生的临时脚本，**不用于正式链路**，仅保留供追溯：

| 脚本 | 原始用途 |
|------|---------|
| `analyze_l1.py` | 分析 L1 检出率，查看每篇文档的多维分数 |
| `check_cache.py` | 检查 layer1_scan_cache 内容 |
| `check_kb.py` | 检查知识库文档列表 |
| `check_safe.py` | 检查 demo_safe 中最高分文档 |
| `find_false_positive.py` | 定位 evaluate.py 结果中的误报记录 |
| `show_dataset.py` | 展示数据集统计信息 |
| `test_*.py` | 各类临时测试脚本（demos/latency/queries/fix 等） |
| `trace_fp_direct.py` | 直接调用 query_detect 追踪误报根因 |
| `trace_false_positive.py` | HTTP 调用追踪误报 |

---

## analysis/ — 分析工具脚本

对评测结果进行二次分析的脚本：

| 脚本 | 职责 |
|------|------|
| `analyze_eval.py` | 分析 evaluate.py 输出，生成分类统计报表 |
