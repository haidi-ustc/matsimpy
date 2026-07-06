# MatSimPy 更广泛代码质量与架构审查 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 对 MatSimPy 做只读的全项目代码质量与架构审查，产出中文审查报告和中文分阶段修复计划。

**Architecture:** 本计划不修改产品代码。执行方式是先建立项目地图，再深读 Core 模块，随后检查 IO、AI、calculator、storage、transformation、builders、tests 和文档/API 契约，最后把证据整理成中文报告与修复计划。

**Tech Stack:** Python 3.12、pytest、ripgrep、git、MatSimPy 本地源码与测试套件。

---

## 文件结构

本计划创建一个审查产物文件，不修改源码：

- Create: `docs/superpowers/reports/2026-07-06-broader-code-quality-architecture-review.md`
  - 负责保存最终中文审查报告和中文分阶段修复计划。

只读检查的主要文件：

- Inspect: `matsimpy/core/structure.py`
- Inspect: `matsimpy/core/crystal.py`
- Inspect: `matsimpy/core/molecule.py`
- Inspect: `matsimpy/core/site.py`
- Inspect: `matsimpy/core/lattice.py`
- Inspect: `matsimpy/core/composition.py`
- Inspect: `matsimpy/core/periodic_table.py`
- Inspect: `matsimpy/io/core.py`
- Inspect: `matsimpy/io/registry.py`
- Inspect: `matsimpy/io/json.py`
- Inspect: `matsimpy/io/vasp.py`
- Inspect: `matsimpy/ai/runtime.py`
- Inspect: `matsimpy/ai/executor.py`
- Inspect: `matsimpy/ai/workspace.py`
- Inspect: `matsimpy/ai/skill_loader.py`
- Inspect: `matsimpy/ai/skills/*.py`
- Inspect: `matsimpy/calculator/base.py`
- Inspect: `matsimpy/calculator/vasp/calculator.py`
- Inspect: `matsimpy/calculator/gaussian/calculator.py`
- Inspect: `matsimpy/calculator/lammps/calculator.py`
- Inspect: `matsimpy/storage/*.py`
- Inspect: `matsimpy/transformation/**/*.py`
- Inspect: `matsimpy/builders/**/*.py`
- Inspect: `tests/**/*.py`
- Inspect: `README.md`
- Inspect: `docs/**/*.rst`
- Inspect: `pyproject.toml`

---

### Task 1: 建立项目地图和审查基线

**Files:**
- Inspect: `pyproject.toml`
- Inspect: `README.md`
- Inspect: `docs/superpowers/specs/2026-07-06-broader-code-quality-architecture-review-design.md`
- Create: `docs/superpowers/reports/2026-07-06-broader-code-quality-architecture-review.md`

- [ ] **Step 1: 读取项目入口和审查设计**

Run:

```bash
sed -n '1,220p' pyproject.toml
sed -n '1,220p' README.md
sed -n '1,220p' docs/superpowers/specs/2026-07-06-broader-code-quality-architecture-review-design.md
```

Expected: 输出项目依赖、公开功能承诺、审查范围和 Core 重点审查要求。

- [ ] **Step 2: 生成源码和测试规模地图**

Run:

```bash
find matsimpy -path '*/__pycache__' -prune -o -type f -name '*.py' -print | sort
find tests -path '*/__pycache__' -prune -o -type f -name 'test_*.py' -print | sort
```

Expected: 输出源码和测试文件清单，用于确认审查覆盖面。

- [ ] **Step 3: 统计模块文件规模**

Run:

```bash
find matsimpy -path '*/__pycache__' -prune -o -type f -name '*.py' -print | xargs wc -l | sort -n
find tests -path '*/__pycache__' -prune -o -type f -name 'test_*.py' -print | xargs wc -l | sort -n
```

Expected: 识别超大文件、测试热点和可能需要重点深读的模块。

- [ ] **Step 4: 创建报告骨架**

Create `docs/superpowers/reports/2026-07-06-broader-code-quality-architecture-review.md` with:

```markdown
# MatSimPy 更广泛代码质量与架构审查报告

日期：2026-07-06

## 摘要

## P0 问题

## P1 问题

## P2 问题

## P3 问题

## Core 模块审查

## IO / Storage / Serialization 审查

## AI Runtime / Skills 审查

## Calculator 审查

## Transformation / Builders 审查

## 测试质量审查

## 分阶段修复计划

## 已验证

## 未验证
```

Expected: 报告文件存在，后续任务只向该文件追加经证据支持的结论。

---

### Task 2: Core 模块深度审查

**Files:**
- Inspect: `matsimpy/core/structure.py`
- Inspect: `matsimpy/core/crystal.py`
- Inspect: `matsimpy/core/molecule.py`
- Inspect: `matsimpy/core/site.py`
- Inspect: `matsimpy/core/lattice.py`
- Inspect: `matsimpy/core/composition.py`
- Inspect: `matsimpy/core/periodic_table.py`
- Inspect: `tests/core/*.py`
- Modify: `docs/superpowers/reports/2026-07-06-broader-code-quality-architecture-review.md`

- [ ] **Step 1: 定位 Core 公共 API 和不变量入口**

Run:

```bash
rg -n "class (Structure|Crystal|Molecule|Site|Lattice|Composition|Element)|def (to_dict|from_dict|__eq__|__hash__|copy|add_|remove_|substitute|translate|rotate|sort|validate)" matsimpy/core tests/core
```

Expected: 输出 Core 对象职责、mutation API、serialization API、equality/hash 和测试覆盖位置。

- [ ] **Step 2: 深读核心对象实现**

Run:

```bash
sed -n '1,260p' matsimpy/core/structure.py
sed -n '1,260p' matsimpy/core/crystal.py
sed -n '1,260p' matsimpy/core/molecule.py
sed -n '1,240p' matsimpy/core/site.py
sed -n '1,260p' matsimpy/core/lattice.py
```

Expected: 记录坐标语义、内部状态存储、copy 行为、验证入口和错误类型。

- [ ] **Step 3: 深读 composition 和 element 行为**

Run:

```bash
sed -n '1,280p' matsimpy/core/composition.py
sed -n '1,260p' matsimpy/core/periodic_table.py
```

Expected: 记录 formula、mass cache、元素顺序、parser、hash/equality 是否稳定。

- [ ] **Step 4: 检查 Core 测试是否覆盖不变量**

Run:

```bash
rg -n "immut|copy|alias|to_dict|from_dict|hash|eq|fractional|cartesian|lattice|position|species|properties|raises" tests/core
```

Expected: 输出 Core 不变量测试覆盖点和明显缺口。

- [ ] **Step 5: 运行 Core 定向验证**

Run:

```bash
python -m pytest tests/core/test_immutability.py tests/core/test_hash_robustness.py tests/core/test_core_design_fixes.py tests/core/test_structure_edge_cases.py -q
```

Expected: 相关 Core 回归测试通过；如果失败，将失败作为审查证据写入报告，不修复代码。

- [ ] **Step 6: 写入 Core 审查结论**

Append findings to `docs/superpowers/reports/2026-07-06-broader-code-quality-architecture-review.md` under `Core 模块审查` and the matching P-level section using:

```markdown
### [P级别] 简短标题

- 位置：`path/to/file.py:line`
- 问题：
- 影响：
- 证据：
- 建议：
- 验证状态：
```

Expected: Core findings distinguish confirmed facts, evidence-backed inference, and unverified suspicion.

---

### Task 3: IO、Storage 和 Serialization 边界审查

**Files:**
- Inspect: `matsimpy/io/core.py`
- Inspect: `matsimpy/io/registry.py`
- Inspect: `matsimpy/io/json.py`
- Inspect: `matsimpy/io/*.py`
- Inspect: `matsimpy/storage/*.py`
- Inspect: `tests/io/*.py`
- Inspect: `tests/storage/*.py`
- Inspect: `tests/contracts/test_io_format_contract.py`
- Inspect: `tests/contracts/test_storage_backend_contract.py`
- Modify: `docs/superpowers/reports/2026-07-06-broader-code-quality-architecture-review.md`

- [ ] **Step 1: 定位 IO 和 storage 公共入口**

Run:

```bash
rg -n "def (read|write|to_|from_|register|detect|serialize|deserialize|save|load|insert|query|update|get)|class .*Registry|class .*Backend|class .*Storage|class .*Envelope" matsimpy/io matsimpy/storage tests/io tests/storage tests/contracts
```

Expected: 输出格式注册、读写入口、storage schema/codec/backend 契约。

- [ ] **Step 2: 深读 IO 核心和 JSON codec**

Run:

```bash
sed -n '1,260p' matsimpy/io/core.py
sed -n '1,260p' matsimpy/io/registry.py
sed -n '1,260p' matsimpy/io/json.py
sed -n '1,260p' matsimpy/storage/codec.py
sed -n '1,260p' matsimpy/storage/schema.py
```

Expected: 记录格式探测、错误处理、round-trip、core object serialization 依赖关系。

- [ ] **Step 3: 检查 IO/storage 测试契约**

Run:

```bash
rg -n "round|detect|registry|optional|raises|invalid|serialize|deserialize|sha|id|backend|contract" tests/io tests/storage tests/contracts
```

Expected: 输出覆盖充分的契约测试和缺失路径。

- [ ] **Step 4: 运行 IO/storage 定向验证**

Run:

```bash
python -m pytest tests/io/test_io_json.py tests/io/test_io_high_level.py tests/io/test_io_public_api.py tests/storage/test_storage.py tests/contracts/test_io_format_contract.py tests/contracts/test_storage_backend_contract.py -q
```

Expected: 相关 IO/storage 契约测试通过；如果失败，将失败作为审查证据写入报告。

- [ ] **Step 5: 写入 IO/storage 审查结论**

Append findings to the report under `IO / Storage / Serialization 审查` and the matching P-level section.

Expected: findings include file/line evidence and identify whether risk comes from architecture, API ambiguity, or missing tests.

---

### Task 4: AI Runtime、Workspace 和 Skills 审查

**Files:**
- Inspect: `matsimpy/ai/runtime.py`
- Inspect: `matsimpy/ai/engine.py`
- Inspect: `matsimpy/ai/executor.py`
- Inspect: `matsimpy/ai/workspace.py`
- Inspect: `matsimpy/ai/providers.py`
- Inspect: `matsimpy/ai/skill_loader.py`
- Inspect: `matsimpy/ai/skills/*.py`
- Inspect: `tests/ai/*.py`
- Modify: `docs/superpowers/reports/2026-07-06-broader-code-quality-architecture-review.md`

- [ ] **Step 1: 定位 AI 执行边界和外部交互**

Run:

```bash
rg -n "requests|subprocess|open\\(|Path\\(|resolve\\(|write|unlink|rmtree|eval|exec|import_module|FunctionDef|tool|provider|api_key|workspace|session|memory" matsimpy/ai tests/ai
```

Expected: 输出网络、文件系统、动态 import、tool execution 和 session/memory 边界。

- [ ] **Step 2: 深读 AI runtime 和 workspace**

Run:

```bash
sed -n '1,280p' matsimpy/ai/runtime.py
sed -n '1,280p' matsimpy/ai/executor.py
sed -n '1,260p' matsimpy/ai/workspace.py
sed -n '1,260p' matsimpy/ai/skill_loader.py
```

Expected: 记录 function calling、skill discovery、workspace path、last structure 和 error propagation 设计。

- [ ] **Step 3: 深读 AI skills**

Run:

```bash
for f in matsimpy/ai/skills/*.py; do printf '\n===== %s =====\n' "$f"; sed -n '1,240p' "$f"; done
```

Expected: 识别重复 schema、过宽 skill 职责、隐藏状态依赖、错误语义不一致和缺失测试。

- [ ] **Step 4: 运行 AI 定向验证**

Run:

```bash
python -m pytest tests/ai/test_runtime.py tests/ai/test_executor.py tests/ai/test_skill_loader.py tests/ai/test_io_skill_paths.py tests/ai/test_session_store.py tests/ai/test_memory.py -q
```

Expected: 相关 AI 边界测试通过；如果失败，将失败作为审查证据写入报告。

- [ ] **Step 5: 写入 AI 审查结论**

Append findings to the report under `AI Runtime / Skills 审查` and matching P-level section.

Expected: findings identify user-facing risk and whether issue is security boundary, architecture boundary, or maintainability.

---

### Task 5: Calculator 边界审查

**Files:**
- Inspect: `matsimpy/calculator/base.py`
- Inspect: `matsimpy/calculator/vasp/*.py`
- Inspect: `matsimpy/calculator/gaussian/*.py`
- Inspect: `matsimpy/calculator/lammps/*.py`
- Inspect: `matsimpy/calculator/lj/*.py`
- Inspect: `matsimpy/calculator/mattersim/*.py`
- Inspect: `tests/calculator/*.py`
- Modify: `docs/superpowers/reports/2026-07-06-broader-code-quality-architecture-review.md`

- [ ] **Step 1: 定位 external calculator 边界**

Run:

```bash
rg -n "subprocess|run\\(|Popen|shell=|cwd=|Path\\(|write_file|read_file|optional|ImportError|RuntimeError|NotImplemented|calculate|results|directory|env" matsimpy/calculator tests/calculator
```

Expected: 输出外部进程、文件写入、结果解析、optional dependency 和错误处理路径。

- [ ] **Step 2: 深读 calculator base 和主要实现**

Run:

```bash
sed -n '1,260p' matsimpy/calculator/base.py
sed -n '1,220p' matsimpy/calculator/vasp/calculator.py
sed -n '1,260p' matsimpy/calculator/vasp/inputs.py
sed -n '1,220p' matsimpy/calculator/gaussian/calculator.py
sed -n '1,220p' matsimpy/calculator/lammps/calculator.py
```

Expected: 记录统一接口是否清晰、外部命令安全性、directory lifecycle、输入输出契约。

- [ ] **Step 3: 检查 calculator 测试契约**

Run:

```bash
rg -n "run|directory|subprocess|mock|fixture|parse|optional|raises|results|POTCAR|POSCAR|OUTCAR|vasprun|gaussian|lammps" tests/calculator
```

Expected: 输出真实 fixture 覆盖、mock 覆盖和缺失风险。

- [ ] **Step 4: 运行 calculator 定向验证**

Run:

```bash
python -m pytest tests/calculator/test_calculator_base.py tests/calculator/test_vasp_calculator.py tests/calculator/test_vasp_inputs.py tests/calculator/test_vasp_outputs.py tests/calculator/test_gaussian.py tests/calculator/test_calculator_lennard_jones.py -q
```

Expected: 相关 calculator 测试通过；如果失败，将失败作为审查证据写入报告。

- [ ] **Step 5: 写入 calculator 审查结论**

Append findings to the report under `Calculator 审查` and matching P-level section.

Expected: findings separate correctness bugs from architecture debt and optional dependency limitations.

---

### Task 6: Transformation、Builders 和 Registry 架构审查

**Files:**
- Inspect: `matsimpy/transformation/**/*.py`
- Inspect: `matsimpy/builders/**/*.py`
- Inspect: `matsimpy/plugins.py`
- Inspect: `tests/transformation/*.py`
- Inspect: `tests/builders/*.py`
- Inspect: `tests/contracts/test_builder_contract.py`
- Inspect: `tests/contracts/test_transformation_contract.py`
- Modify: `docs/superpowers/reports/2026-07-06-broader-code-quality-architecture-review.md`

- [ ] **Step 1: 定位 registry、builder 和 transformation 入口**

Run:

```bash
rg -n "Registry|register|discover|entry_points|TransformationSpec|TransformationPlan|Builder|build_|generate_|create_|apply|validate|optional|ImportError|copy" matsimpy/transformation matsimpy/builders matsimpy/plugins.py tests/transformation tests/builders tests/contracts
```

Expected: 输出注册机制、spec metadata、pipeline、可选依赖和测试契约。

- [ ] **Step 2: 深读 transformation core**

Run:

```bash
sed -n '1,260p' matsimpy/transformation/base.py
sed -n '1,260p' matsimpy/transformation/spec.py
sed -n '1,260p' matsimpy/transformation/registry.py
sed -n '1,260p' matsimpy/transformation/composite/pipeline.py
sed -n '1,260p' matsimpy/transformation/composite/plan.py
```

Expected: 记录 transformation API 是否依赖 Core 内部细节、是否清晰表达输入/输出契约。

- [ ] **Step 3: 深读 builder registry 和代表性 builder**

Run:

```bash
sed -n '1,260p' matsimpy/builders/registry.py
sed -n '1,260p' matsimpy/builders/bulk/prototype.py
sed -n '1,260p' matsimpy/builders/surface/slab.py
sed -n '1,260p' matsimpy/builders/alloy/random.py
```

Expected: 记录输入验证、返回对象一致性、可选依赖失败方式、重复逻辑。

- [ ] **Step 4: 运行 transformation/builder 定向验证**

Run:

```bash
python -m pytest tests/transformation/test_transformation.py tests/transformation/test_structural_transformations.py tests/transformation/test_transformation_regressions.py tests/builders/test_builders_interface.py tests/builders/test_builders_bulk.py tests/builders/test_builders_surface.py tests/contracts/test_builder_contract.py tests/contracts/test_transformation_contract.py -q
```

Expected: 相关转换和构建器测试通过；如果失败，将失败作为审查证据写入报告。

- [ ] **Step 5: 写入 transformation/builders 审查结论**

Append findings to the report under `Transformation / Builders 审查` and matching P-level section.

Expected: findings identify registry consistency, public API stability, dependency handling, and test coverage risks.

---

### Task 7: 测试质量、文档承诺和 Packaging 审查

**Files:**
- Inspect: `tests/**/*.py`
- Inspect: `README.md`
- Inspect: `docs/**/*.rst`
- Inspect: `pyproject.toml`
- Modify: `docs/superpowers/reports/2026-07-06-broader-code-quality-architecture-review.md`

- [ ] **Step 1: 检查测试组织和跳过策略**

Run:

```bash
rg -n "skip|xfail|mock|monkeypatch|tmp_path|fixture|parametrize|requires_|optional|ImportError|pytest.raises" tests
```

Expected: 输出测试依赖、跳过策略、mock 边界和错误路径覆盖。

- [ ] **Step 2: 检查文档公开承诺**

Run:

```bash
rg -n "immutable|read\\(|write\\(|storage|AI|calculator|VASP|Gaussian|LAMMPS|builder|transformation|optional|pip install|public API|from matsimpy" README.md docs
```

Expected: 输出用户可见承诺，供代码行为对照。

- [ ] **Step 3: 检查 package data 和 optional extras**

Run:

```bash
sed -n '1,220p' pyproject.toml
python - <<'PY'
import importlib
import matsimpy
print("matsimpy import ok", matsimpy.__version__ if hasattr(matsimpy, "__version__") else "no __version__")
for name in ["matsimpy.core", "matsimpy.io", "matsimpy.storage", "matsimpy.transformation", "matsimpy.builders", "matsimpy.calculator", "matsimpy.ai"]:
    importlib.import_module(name)
    print("import ok", name)
PY
```

Expected: package metadata is readable and main modules import without optional dependency crashes.

- [ ] **Step 4: 运行 packaging/import smoke tests**

Run:

```bash
python -m pytest tests/test_packaging_runtime_contracts.py -q
```

Expected: packaging/runtime contract tests pass; if failure occurs, report it as evidence.

- [ ] **Step 5: 写入测试/文档/packaging 审查结论**

Append findings to the report under `测试质量审查` and matching P-level section.

Expected: findings distinguish real contract mismatch from low-priority documentation cleanup.

---

### Task 8: 生成中文分阶段修复计划

**Files:**
- Modify: `docs/superpowers/reports/2026-07-06-broader-code-quality-architecture-review.md`

- [ ] **Step 1: 汇总所有 findings 并去重**

Run:

```bash
rg -n "^### \\[P[0-3]\\]|^- 位置：|^- 问题：|^- 建议：" docs/superpowers/reports/2026-07-06-broader-code-quality-architecture-review.md
```

Expected: 输出所有候选问题，便于合并重复项和调整优先级。

- [ ] **Step 2: 按阶段组织修复计划**

Append this structure under `分阶段修复计划`:

```markdown
### 阶段 1：P0/P1 风险收敛

- 目标：
- 涉及文件：
- 建议步骤：
- 验证方式：
- 风险：

### 阶段 2：Core 与公共 API 边界稳定

- 目标：
- 涉及文件：
- 建议步骤：
- 验证方式：
- 风险：

### 阶段 3：IO/Storage/AI/Calculator 边界一致性

- 目标：
- 涉及文件：
- 建议步骤：
- 验证方式：
- 风险：

### 阶段 4：测试补强与低风险清理

- 目标：
- 涉及文件：
- 建议步骤：
- 验证方式：
- 风险：
```

Expected: 每个阶段有具体文件范围、可验证目标和明确风险，不包含空泛 cleanup。

- [ ] **Step 3: 记录已验证命令**

Append under `已验证`:

```markdown
- `command here`：结果摘要。
```

Expected: 每条已验证记录对应实际运行过的命令和结果。

- [ ] **Step 4: 记录未验证范围**

Append under `未验证`:

```markdown
- 未运行全量测试。
- 未测试需要外部二进制、网络服务、API key 或大型 optional dependency 的路径。
```

Expected: 未验证项真实反映审查限制。

---

### Task 9: 最终自查和提交报告

**Files:**
- Modify: `docs/superpowers/reports/2026-07-06-broader-code-quality-architecture-review.md`

- [ ] **Step 1: 检查报告是否有占位内容**

Run:

```bash
rg -n "TBD|TODO|待定|占位|问题：\\s*$|影响：\\s*$|证据：\\s*$|建议：\\s*$|验证状态：\\s*$" docs/superpowers/reports/2026-07-06-broader-code-quality-architecture-review.md
```

Expected: 无输出。如果有输出，补充具体内容或删除空段。

- [ ] **Step 2: 检查报告语言**

Run:

```bash
python - <<'PY'
from pathlib import Path
p = Path("docs/superpowers/reports/2026-07-06-broader-code-quality-architecture-review.md")
text = p.read_text()
print("chars", len(text))
print("contains report", "审查报告" in text)
print("contains plan", "分阶段修复计划" in text)
PY
```

Expected: 输出 `contains report True` 和 `contains plan True`。

- [ ] **Step 3: 检查工作区只新增报告文件**

Run:

```bash
git status --short
git diff --stat
```

Expected: 只显示 `docs/superpowers/reports/2026-07-06-broader-code-quality-architecture-review.md`，没有源码或测试修改。

- [ ] **Step 4: 提交报告**

Run:

```bash
git add -f docs/superpowers/reports/2026-07-06-broader-code-quality-architecture-review.md
git commit -m "Document broader architecture review findings" -m "Capture the read-only MatSimPy code quality and architecture review in Chinese, including evidence-backed findings and a phased repair plan." -m "Constraint: User requested analysis in English but final review and plan document in Chinese." -m "Confidence: medium" -m "Scope-risk: narrow" -m "Directive: Keep follow-up fixes in separate implementation plans and commits." -m "Tested: Targeted read-only review commands listed in the report." -m "Not-tested: Full repository test suite and external-service paths."
```

Expected: A commit is created containing only the final report.
