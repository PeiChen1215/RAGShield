# RAGShield 开发规范与 Git 工作流

> **文档标识**: RAGShield-DEVSTD-v1.0  
> **文档状态**: 已冻结  
> **创建日期**: 2026-04-28  
> **目标读者**: 三人开发团队  
> **用途**: 统一代码风格、Git 协作流程、测试规范，确保三人写出的代码像一个人写的。

---

## 一、文档控制

| 版本 | 日期 | 修订人 | 修订内容 |
|------|------|--------|---------|
| v1.0 | 2026-04-28 | 团队 | 初始版本，覆盖分支策略、代码风格、PR 规则、测试规范 |

---

## 二、Git 分支策略

### 2.1 分支模型

采用 **Git Flow 简化版**，只有 3 类分支：

```
main        ← 稳定发布分支，永远可运行，禁止直接推送
    ↑
dev         ← 日常集成分支，合并特性分支，跑通测试后才合到 main
    ↑
feat/xxx    ← 个人特性分支，从 dev 检出，完成后 PR 到 dev
```

### 2.2 分支命名规范

| 分支类型 | 命名格式 | 示例 |
|---------|---------|------|
| 特性分支 | `feat/{模块名}-{简述}` | `feat/layer1-outlier-detector` |
| 修复分支 | `fix/{模块名}-{简述}` | `fix/api-query-timeout` |
| 文档分支 | `docs/{简述}` | `docs/update-prd` |

### 2.3 完整工作流

```bash
# 1. 从 dev 更新最新代码
git checkout dev
git pull origin dev

# 2. 创建特性分支
git checkout -b feat/layer2-attention-analyzer

# 3. 开发... 提交...（遵循提交信息规范）

# 4. 推送分支到远程（首次推送）
git push -u origin feat/layer2-attention-analyzer

# 5. 在 GitHub 上发起 Pull Request → dev 分支
#    PR 标题格式: "feat: 实现 Layer2 注意力方差分析模块"
#    PR 描述必须包含: 改了什么、怎么测试的、有哪些风险

# 6. 至少 1 人 Review 后合并（学生团队简化：另一个人在微信里确认"看了，合吧"）

# 7. 合并后删除特性分支
git push origin --delete feat/layer2-attention-analyzer
```

### 2.4 禁止事项

- **禁止直接向 main 分支推送代码**（通过 GitHub Branch Protection 设置）
- **禁止 force push** 到 dev 或 main
- **禁止在 PR 中提交 API Key、密码等敏感信息**（.gitignore 必须配置好 `.env`）

---

## 三、代码风格规范

### 3.1 工具链

| 工具 | 用途 | 版本 | 配置方式 |
|------|------|------|---------|
| **Black** | 代码格式化 | `^24.0` | `pyproject.toml` |
| **isort** | 导入语句排序 | `^5.13` | `pyproject.toml` |
| **Flake8** | 静态检查 | `^7.0` | `setup.cfg` |

### 3.2 pyproject.toml 配置

```toml
[tool.black]
line-length = 100
target-version = ['py310']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
line_length = 100
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true
```

### 3.3 setup.cfg 配置

```ini
[flake8]
max-line-length = 100
extend-ignore = E203, W503
exclude = .git,__pycache__,build,dist,.venv
per-file-ignores = __init__.py:F401
```

### 3.4 提交前自动格式化

**推荐做法**：使用 pre-commit 钩子，在每次 `git commit` 前自动运行 Black + isort + Flake8。

```bash
# 安装 pre-commit
pip install pre-commit

# 在仓库根目录创建 .pre-commit-config.yaml
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/psf/black
    rev: 24.1.0
    hooks:
      - id: black
        language_version: python3.10

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
EOF

# 安装钩子
pre-commit install

# 手动运行检查（全仓库）
pre-commit run --all-files
```

> **学生团队简化**：如果 pre-commit 配置太复杂，可以**每次提交前手动运行**：
> ```bash
> black src/ tests/ && isort src/ tests/ && flake8 src/ tests/
> ```

### 3.5 Python 代码规范

**命名规范**：

| 类型 | 规范 | 示例 |
|------|------|------|
| 模块/文件 | 全小写，下划线分隔 | `outlier_detector.py` |
| 类 | 大驼峰 | `class OutlierDetector:` |
| 函数/方法 | 全小写，下划线分隔 | `def detect_outliers():` |
| 常量 | 全大写，下划线分隔 | `MAX_RISK_SCORE = 1.0` |
| 变量 | 全小写，下划线分隔 | `risk_score = 0.85` |
| 私有属性 | 单下划线前缀 | `_internal_cache` |

**类型注解**：所有函数参数和返回值必须标注类型。

```python
from typing import List, Dict, Tuple
import numpy as np

def detect_outliers(
    embeddings: np.ndarray,
    contamination: float = 0.1,
    n_neighbors: int = 20
) -> Tuple[List[str], List[float]]:
    """检测离群文档。
    
    Args:
        embeddings: 文档嵌入矩阵 (N x D)
        contamination: 异常比例估计
        n_neighbors: LOF 邻居数
        
    Returns:
        (suspicious_doc_ids, risk_scores)
    """
    ...
```

**文档字符串**：所有模块、类、函数必须有 docstring，遵循 Google Style。

```python
def cosine_baseline_outlier(
    doc_embedding: np.ndarray,
    all_embeddings: np.ndarray,
    threshold: float = 0.4
) -> Tuple[bool, float]:
    """计算单篇文档与知识库全量文档的平均余弦相似度。
    
    Args:
        doc_embedding: 目标文档向量 (D,)
        all_embeddings: 全量文档矩阵 (N x D)
        threshold: 离群判定阈值，默认 0.4
        
    Returns:
        (is_outlier, avg_similarity):
            - is_outlier: 是否低于阈值
            - avg_similarity: 平均相似度值
            
    Example:
        >>> flag, score = cosine_baseline_outlier(doc_emb, kb_embs, 0.4)
        >>> print(flag, score)
        True 0.32
    """
```

---

## 四、提交信息规范

采用 **Conventional Commits** 格式，便于自动生成 CHANGELOG 和版本号。

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 4.1 Type 枚举

| 类型 | 用途 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(layer1): 实现 Isolation Forest 离群检测` |
| `fix` | 修复 bug | `fix(api): 修复 query 路由空指针异常` |
| `docs` | 文档变更 | `docs(prd): 更新攻击场景 S1-002 描述` |
| `test` | 测试相关 | `test(layer2): 添加注意力方差单元测试` |
| `refactor` | 重构 | `refactor(core): 重构 embedder 为统一接口` |
| `perf` | 性能优化 | `perf(layer3): NLI 模型缓存优化，延迟降低 20ms` |
| `chore` | 杂项 | `chore(deps): 更新 requirements.txt` |

### 4.2 Scope 枚举

与 `src/` 目录模块对应：

- `core` — 核心基础设施
- `layer1` — 知识库层
- `layer2` — 检索层
- `layer3` — 生成层
- `fusion` — 风险融合
- `api` — FastAPI 服务
- `frontend` — Gradio 界面
- `docs` — 项目文档
- `test` — 测试相关

### 4.3 提交信息示例

```bash
# 好示例
git commit -m "feat(layer1): 实现余弦相似度基线规则兜底

- 新增 cosine_baseline_outlier() 函数
- 与 IF+LOF 做 OR 逻辑，适配小知识库场景
- 延迟 <1ms，不影响整体性能

Closes #12"

# 坏示例（禁止）
git commit -m "update"          # 无类型、无范围、无描述
git commit -m "修复bug"          # 中文提交信息（不规范）
git commit -m "feat: xxx"         # 无 scope，不知道改了哪个模块
```

---

## 五、Pull Request 规范

### 5.1 PR 模板

```markdown
## 变更内容
<!-- 简述改了什么，1-2 句话 -->

## 影响范围
<!-- 影响了哪些模块，是否有破坏性变更 -->

## 测试情况
<!-- 如何测试的，测试了哪些场景 -->
- [ ] 单元测试通过
- [ ] 本地手动测试通过
- [ ] API 响应格式符合契约

## 风险说明
<!-- 是否有已知问题或后续 TODO -->
```

### 5.2 Review 规则

| 场景 | Review 要求 |
|------|------------|
| 单人特性分支 → dev | 至少 1 人 Review（学生团队简化：微信确认即可） |
| dev → main | **必须 2 人 Review**，确保全链路测试通过 |
| 文档更新 | 可自 Review 直接合（但需在群里同步） |

### 5.3 合并策略

- **特性分支 → dev**：Squash and Merge（压缩为一个干净提交）
- **dev → main**：Create a Merge Commit（保留完整历史）

---

## 六、目录结构与文件规范

### 6.1 与 04_SAD 对齐的目录结构

```
RAGShield/
├── README.md                          # 项目说明 + 快速开始
├── requirements.txt                   # 生产依赖
├── requirements-dev.txt               # 开发依赖（black, isort, flake8, pytest）
├── .env.example                       # 环境变量模板（API Key 等）
├── .gitignore                         # Git 忽略文件
├── .pre-commit-config.yaml            # 提交前自动格式化钩子（可选）
├── pyproject.toml                     # Black + isort 配置
├── setup.cfg                          # Flake8 配置
├── Dockerfile                         # Docker 构建
├── docker-compose.yml                 # Docker Compose
├── scripts/
│   ├── start.sh                       # 容器启动脚本
│   ├── download_models.py             # 预下载模型
│   ├── seed_data.py                   # 一键导入测试数据
│   ├── threshold_sweep.py             # 阈值扫描
│   ├── weight_ablation.py             # 权重消融实验
│   ├── evaluate.py                    # 评测主脚本
│   └── setup.sh                       # 本地环境初始化脚本
├── config/
│   ├── gpu_config.yaml                # GPU 高性能版配置
│   └── cpu_config.yaml                # CPU 轻量化版配置
├── src/                               # 核心源码
│   ├── __init__.py
│   ├── core/                          # 核心基础设施
│   │   ├── __init__.py
│   │   ├── config.py                  # 配置加载
│   │   ├── embedder.py                # 嵌入模型封装
│   │   └── vector_store.py            # 向量数据库封装
│   ├── layer1_kb/                     # 知识库层
│   │   ├── __init__.py
│   │   ├── outlier_detector.py
│   │   ├── sensitive_ner.py
│   │   ├── context_pollution_detector.py
│   │   └── bias_detector.py
│   ├── layer2_retrieval/              # 检索层
│   │   ├── __init__.py
│   │   ├── attention_analyzer.py
│   │   ├── relevance_scorer.py
│   │   └── diversity_monitor.py
│   ├── layer3_generation/             # 生成层
│   │   ├── __init__.py
│   │   ├── consistency_checker.py
│   │   ├── llm_client.py
│   │   └── bias_checker.py
│   ├── fusion/
│   │   ├── __init__.py
│   │   └── risk_fusion.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI 入口
│   │   ├── schemas.py                 # Pydantic 模型
│   │   └── routers/
│   │       ├── kb.py                # /kb/* 路由
│   │       └── query.py             # /query 路由
│   └── frontend/
│       └── app.py                     # Gradio 界面
├── tests/                             # 测试目录
│   ├── __init__.py
│   ├── conftest.py                    # pytest 共享 fixture
│   ├── test_core.py                   # core 模块测试
│   ├── test_layer1.py                 # Layer1 测试
│   ├── test_layer2.py                 # Layer2 测试
│   ├── test_layer3.py                 # Layer3 测试
│   ├── test_fusion.py                 # 融合模块测试
│   ├── test_api.py                    # API 集成测试
│   └── data/                          # 测试数据
│       └── sample_docs.json
├── data/                              # 运行时数据
│   ├── attack_kb/                    # 攻击模板库
│   ├── normal_kb/                    # 正常文档库
│   ├── queries/                      # 查询集合
│   └── chroma_db/                    # ChromaDB 持久化数据（.gitignore）
└── udocs/                             # 项目文档（frozen docs）
    ├── 01_PRD.md
    ├── 02_Technical_Selection_Report.md
    ├── 03_Attack_KB_and_Defense_Mapping.md
    ├── 04_System_Architecture_Design.md
    ├── 05_API_Contract.md
    ├── 06_Development_Standard.md
    ├── 07_Evaluation.md
    ├── 08_Environment_Setup.md
    └── reference/
        └── 01_OpenSource_Projects_and_Benchmarks.md
```

### 6.2 新文件创建规范

创建新模块文件时，必须包含：

```python
"""
模块名: {模块路径}
职责: {一句话描述}
作者: {姓名}
创建日期: {YYYY-MM-DD}
"""

from typing import ...

# 常量定义区
DEFAULT_THRESHOLD = 0.5
MAX_RETRY = 3


class NewModule:
    """类文档字符串，说明职责、输入、输出。"""
    
    def __init__(self, config: dict):
        """初始化。"""
        self.config = config
    
    def process(self, input_data: str) -> dict:
        """处理逻辑。
        
        Args:
            input_data: 输入描述
            
        Returns:
            输出描述
        """
        pass


if __name__ == "__main__":
    # 简单的本地测试代码
    module = NewModule({})
    result = module.process("test")
    print(result)
```

---

## 七、测试规范

### 7.1 测试框架

- **pytest**：单元测试 + 集成测试
- **pytest-asyncio**：异步测试（FastAPI 接口）
- **pytest-cov**：覆盖率报告（目标：核心模块 ≥70%）

### 7.2 测试文件命名

```
tests/
├── test_{模块名}.py        # 对应 src/{模块路径}
├── conftest.py            # 共享 fixture
└── data/                  # 测试数据
```

### 7.3 测试编写规范

```python
# tests/test_layer1.py
import pytest
import numpy as np
from src.layer1_kb.outlier_detector import OutlierDetector


class TestOutlierDetector:
    """OutlierDetector 单元测试。"""
    
    @pytest.fixture
    def detector(self):
        """测试用检测器实例。"""
        return OutlierDetector(contamination=0.1)
    
    @pytest.fixture
    def normal_embeddings(self):
        """正常文档嵌入（高斯分布）。"""
        np.random.seed(42)
        return np.random.randn(50, 512).astype(np.float32)
    
    @pytest.fixture
    def poisoned_embeddings(self):
        """含投毒文档的嵌入（最后 3 条明显偏离）。"""
        np.random.seed(42)
        normal = np.random.randn(47, 512).astype(np.float32)
        poisoned = np.random.randn(3, 512).astype(np.float32) + 5.0  # 明显偏离
        return np.vstack([normal, poisoned])
    
    def test_no_anomaly_in_clean_data(self, detector, normal_embeddings):
        """正常数据应无异常。"""
        suspicious, scores = detector.detect(normal_embeddings)
        assert len(suspicious) <= 2  # 误报容忍 ≤2 条
        assert all(0 <= s <= 1 for s in scores)
    
    def test_detects_poisoned_docs(self, detector, poisoned_embeddings):
        """应检测到投毒文档。"""
        suspicious, scores = detector.detect(poisoned_embeddings)
        # 最后 3 条（索引 47-49）是投毒的，应该被检测到
        assert len(suspicious) >= 2
        assert any(idx in suspicious for idx in [47, 48, 49])
    
    def test_risk_score_range(self, detector, poisoned_embeddings):
        """风险分数应在 0~1 范围内。"""
        _, scores = detector.detect(poisoned_embeddings)
        assert all(0 <= s <= 1 for s in scores)
    
    def test_latency_under_threshold(self, detector, poisoned_embeddings):
        """延迟应 <50ms。"""
        import time
        start = time.time()
        detector.detect(poisoned_embeddings)
        elapsed_ms = (time.time() - start) * 1000
        assert elapsed_ms < 50
```

### 7.4 必写测试场景

每个核心模块必须覆盖：

| 测试场景 | 说明 |
|---------|------|
| **正常输入** | 期望行为：正确返回，无异常 |
| **边界输入** | 空列表、单条数据、超大文本 |
| **异常输入** | 类型错误、格式错误、缺失字段 |
| **性能基准** | 延迟是否满足目标（如 <50ms） |
| **确定性** | 相同输入多次运行，输出一致（seed 固定） |

### 7.5 运行测试

```bash
# 运行全部测试
pytest tests/ -v

# 运行指定模块测试
pytest tests/test_layer1.py -v

# 生成覆盖率报告
pytest tests/ --cov=src --cov-report=term-missing

# 只运行标记了 smoke 的快速测试（用于提交前检查）
pytest tests/ -m smoke -v
```

---

## 八、环境变量与密钥管理

### 8.1 .env.example（模板文件，提交到 Git）

```bash
# === RAGShield 环境变量模板 ===
# 复制为 .env 后填入实际值，.env 不提交到 Git

# LLM API 配置
KIMI_API_KEY=sk-your-key-here
KIMI_BASE_URL=https://api.moonshot.cn/v1

# 备用 LLM API（DeepSeek）
DEEPSEEK_API_KEY=sk-your-backup-key-here

# 模型配置
DEFAULT_MODEL_PROFILE=gpu  # gpu | cpu
EMBEDDING_DEVICE=cuda      # cuda | cpu

# 检测阈值（可被 threshold_sweep.py 覆盖）
IF_CONTAMINATION=0.1
LOF_N_NEIGHBORS=20
NLI_SIMILARITY_THRESHOLD=0.3
NLI_CONTRADICTION_THRESHOLD=0.3

# 服务配置
API_HOST=0.0.0.0
API_PORT=8000
GRADIO_PORT=7860
```

### 8.2 .gitignore（必须包含）

```gitignore
# 环境变量（含 API Key）
.env
.env.local
.env.production

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# 虚拟环境
venv/
ENV/
env/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# 测试
.pytest_cache/
.coverage
htmlcov/

# 数据（大文件）
data/chroma_db/
*.tar
*.zip

# 模型缓存（运行时下载）
# 注意：Docker 构建时预下载到镜像中，.gitignore 中排除本地缓存
models/
```

---

## 九、每日站会模板

每天晚上 10 分钟，三人只说三件事：

```
[姓名]
1. 今天完成了：
   - feat/layer1-outlier-detector 的 IF 部分
   
2. 明天计划：
   - 完成余弦基线规则 + 单元测试
   
3. 阻塞问题：
   - BGE-M3 在 Conda 环境下安装失败，需要队友帮忙
```

**阻塞问题处理**：当场指派解决人，如果 10 分钟解决不了，升级到第二天优先处理。

---

*文档版本: v1.0 | 状态: 已冻结 | 下次评审: Week 3 对齐会*
