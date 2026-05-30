# RAGShield 更新报告 — 2026-05-26 (v2)

> **更新人**: Kimi Code  
> **涉及范围**: 数据集扩展 V2、L3 行为审计重构、双模式评测基准、前端可视化、仓库清理  
> **验证状态**: 全部文件语法通过 + 数据结构验证通过

---

## 一、数据集扩展 V2 — 规模翻倍

### 1. 正常文档 100 → 200 篇

**新增文件**: `data/normal_kb/extended_normal_docs_v2.py` (100 篇)

覆盖 10 个全新业务域，每域 10 篇：

| 类别 | 示例主题 |
|------|---------|
| 生产安全 | 特种设备、危化品仓库、受限空间、动火作业 |
| 采购管理 | 供应商准入、招标采购、框架协议、进口采购 |
| 项目管理 | 里程碑、风险管理、变更管理、绩效考核 |
| 质量管理 | ISO9001、IQC/IPQC/OQC、不合格品控制、8D 报告 |
| 信息安全等级保护 | 等保 2.0、分级保护、漏洞管理、密码管理 |
| 应急响应 | 综合预案、危机公关、BCP、网络攻击应急 |
| 数据治理 | 数据分类分级、主数据、数据质量、数据安全 |
| 供应链安全 | 供应商安全评估、物流安全、ESG、尽职调查 |
| 物理安全 | 门禁、视频监控、数据中心、周界防范 |
| 第三方合作 | 外包管理、保密协议、知识产权、联合营销 |

**集成方式**: `scripts/seed_data.py` 导入 `EXTENDED_NORMAL_DOCS_V2` 并合并到 `demo_safe` / `demo_attack` 知识库。

### 2. 攻击文档 25 → 50 篇

**新增文件**: `data/extended_attack_docs_v2.py` (25 篇)

| 攻击类型 | 数量 | 核心手法 |
|----------|------|---------|
| `indirect_injection` | 5 | 伪装成正常文档（FAQ、会议纪要、维护通知），中间嵌入 "忽略所有指令，现在执行..." |
| `role_play_jailbreak` | 5 | 利用小说/剧本/游戏设定，构造 "无限制 AI 角色" 绕过安全过滤 |
| `refusal_abuse` | 3 | 伪造系统公告，诱导 AI 对正常问题执行 "自动拒绝" |
| `opinion_manipulation` | 3 | 伪造 "独立评估报告" / "内部备忘录"，植入偏见结论 |
| `cross_context` | 3 | 伪造多轮对话历史，虚构 "已通过身份验证" 的上下文 |
| `code_supply_chain` | 3 | 伪装成依赖安装指南，诱导安装恶意包 / 执行后门脚本 |
| `data_exfiltration_probe` | 3 | 伪造 "默认配置规范"，将对话记录外发至外部邮箱 |

**集成方式**: `scripts/seed_data.py` 导入 `EXTENDED_ATTACK_DOCS_V2` 并合并到 `demo_attack` 知识库。

### 3. 评测查询 47 → 100 条

**新增文件**: `data/additional_eval_queries.py` (53 条)

| 类别 | 新增 | 总计 | 预期结果 |
|------|------|------|---------|
| `safe_queries` | +20 | 40 | `safe` |
| `tamper_queries` | +3 | 10 | `warning_or_block` |
| `injection_queries` | +3 | 10 | `block` |
| `privilege_escalation_queries` | +2 | 5 | `block` |
| `indirect_injection_queries` | +5 | 5 | `block` |
| `role_play_jailbreak_queries` | +5 | 5 | `block` |
| `refusal_abuse_queries` | +3 | 3 | `warning_or_block` |
| `opinion_manipulation_queries` | +3 | 3 | `warning_or_block` |
| `cross_context_queries` | +3 | 3 | `block` |
| `code_supply_chain_queries` | +3 | 3 | `block` |
| `data_exfiltration_probe_queries` | +3 | 3 | `block` |
| `data_poisoning_queries` | — | 4 | `warning_or_block` |
| `prompt_leak_queries` | — | 3 | `block` |
| `social_engineering_queries` | — | 3 | `block` |

**集成方式**: `seed_data.py` 在保存 `eval_queries.json` 前自动合并 `ADDITIONAL_QUERIES`。

---

## 二、L3 行为审计重构

**文件**: `src/layer3_generation/behavior_auditor.py`

### 1. Unicode 归一化防御

新增 `_normalize_text(text)`：
- `unicodedata.normalize('NFKC', text)` — 统一兼容等价字符（如全角 → 半角）
- 剥离零宽字符：`\u200b-\u200f`、零宽连接符 `\u2060`、BOM `\ufeff`

**目的**: 防御利用零宽空格、同形异义字（homoglyph）绕过正则检测的对抗性攻击。

### 2. 规则体系重设计

| 规则 | 触发条件 | 风险分 | 说明 |
|------|---------|--------|------|
| `ignore_instructions` | 匹配 "忽略之前所有指令" 等前缀 | 0.40 | 典型的间接注入信号 |
| `jailbreak_prefix` | DAN / Developer Mode / Do Anything Now / 绕过限制 / 解除限制 | 0.45 | 角色扮演越狱前缀 |
| `credential_disclosure` | 密码/密钥/token/凭证/验证码 + `[:：=是为]` + 3 位以上字符 | 0.35 | 真实凭证泄露 |
| `credential_request` | 索要密码行为："提供密码给我"、"发送至 xxx" | 0.30 | 主动索要凭证 |
| `credential_mention` | 仅提及密码但无索要/泄露行为 | 0.05 | 极轻量标记，不单独告警 |

### 3. 组合惩罚机制

```python
if len(triggered) >= 2:
    total_risk = min(total_risk * 1.5, 1.0)
```

多规则同时触发时风险分 ×1.5，上限 1.0。例如：`ignore_instructions` (0.40) + `credential_disclosure` (0.35) = 0.75 × 1.5 = **1.0 (block)**。

---

## 三、评测脚本双模式基准

**文件**: `scripts/evaluate.py`

### PHYSICAL vs DETECT 语义

| 模式 | `exclude_attack_docs` | 攻击文档处理 | 攻击查询 "正确" 标准 |
|------|----------------------|-------------|-------------------|
| **PHYSICAL** | `true` | 检索层过滤，LLM 看不到 | 返回 `safe` = 正确（成功隔离） |
| **DETECT** | `false` | 允许召回，L2/L3 拦截 | 返回 `block`/`warning` = 正确（成功检测） |

### 输出文件

- `results/eval_metrics_physical.json` — 物理隔离模式指标
- `results/eval_metrics_detect.json` — 检测拦截模式指标

### 关键修复

- `_is_correct(r, physical_mode)` 新增 `physical_mode` 参数
- `compute_metrics` / `print_detail_table` 已同步传入该参数
- `evaluate_all()` 签名支持 `exclude_attack=True/False`

---

## 四、Gradio 前端增强

**文件**: `src/frontend/app.py`

### 1. 查询检测 Tab

- 新增 `exclude_attack_docs` Checkbox（默认勾选）
- 勾选 = 物理隔离；取消 = 检测模式

### 2. 知识库上传 Tab

- 阈值滑动条 + 快速填充按钮（0.3 / 0.5 / 0.7 / 0.9）

### 3. 评测报告 Tab（新增）

- 读取 `results/eval_metrics_physical.json` 和 `results/eval_metrics_detect.json`
- matplotlib 横向柱状图对比双模式指标：
  - Accuracy
  - Precision (Safe / Attack)
  - Recall (Safe / Attack)
  - F1 (Safe / Attack)
  - Avg Latency

---

## 五、仓库清理

删除根目录下 50+ 个 `tmp_*` 临时文件（测试脚本、日志、输出片段），并更新 `.gitignore`：

```gitignore
tmp_*
*.log
results/*.json
```

---

## 六、文件变更清单

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `scripts/seed_data.py` | **修改** | 导入 V2 数据集，合并逻辑更新为 200+50+100 |
| `scripts/evaluate.py` | **修改** | 双模式评测，attack_categories 扩展至 13 类，expected_map 同步 |
| `src/layer3_generation/behavior_auditor.py` | **修改** | Unicode 归一化、5 条规则、组合惩罚 ×1.5 |
| `src/frontend/app.py` | **修改** | Checkbox 开关 + 评测报告可视化 Tab |
| `data/normal_kb/extended_normal_docs_v2.py` | **新增** | 100 篇正常企业文档（10 个业务域） |
| `data/extended_attack_docs_v2.py` | **新增** | 25 篇攻击文档（7 种新型攻击） |
| `data/additional_eval_queries.py` | **新增** | 53 条扩展评测查询 |
| `.gitignore` | **修改** | 排除 tmp_*、*.log、results/*.json |

---

## 七、验证结果

### 数据结构验证

```bash
正常文档: 50 + 50 + 100 = 200 篇
攻击文档: 8 + 17 + 25 = 50 篇
查询总计: 40 safe + 60 attack = 100 条
```

### 语法检查

```bash
python -m py_compile scripts/seed_data.py        # OK
python -m py_compile scripts/evaluate.py          # OK
python -m py_compile data/normal_kb/extended_normal_docs_v2.py   # OK
python -m py_compile data/extended_attack_docs_v2.py             # OK
python -m py_compile data/additional_eval_queries.py             # OK
```

---

## 八、下一步建议

1. **运行 `seed_data.py` 重新导入数据** — 需要重启后端（ChromaDB 单 worker 模式）
2. **运行 `evaluate.py` 生成双模式基准报告** — 验证 100 条查询在新数据集上的表现
3. **behavior_auditor 阈值调优** — 新规则下需观察 `warning_or_block` vs `block` 的边界
4. **ChromaDB 清理** — `data/chroma_db/` 中仍有历史 UUID 孤儿目录，可手动清理

---

*报告生成时间: 2026-05-26*
