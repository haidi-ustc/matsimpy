# MatSimPy 更广泛代码质量与架构审查报告

日期：2026-07-06

## 摘要

本次审查是只读审查，覆盖 `core`、`io`、`storage`、`ai`、`calculator`、`transformation`、`builders`、测试、文档和 packaging。未发现新的 P0 问题，但发现多处 P1/P2 架构与契约问题：核心对象 mutation 路径可绕过坐标不变量，`Crystal` 的 PBC 未参与 equality/hash，VASP/LAMMPS calculator 仍有结果或输入正确性风险，AI runtime 和 storage skill 存在进程级共享状态，registry metadata 与 callable 不一致且测试没有抓住这些错误。

整体判断：项目已有较多回归测试和契约测试，基础导入和主要定向测试通过；当前主要风险不是“没有测试”，而是若干关键测试过宽、跳过策略过松，导致 registry、calculator、storage 等边界的错误可以通过测试套件。

## P0 问题

未发现新的 P0 问题。

## P1 问题

### [P1] Core mutation 和 `_construct` 可绕过坐标不变量

- 位置：`matsimpy/core/structure.py:141`、`matsimpy/core/structure.py:215`、`matsimpy/core/structure.py:325`、`matsimpy/core/crystal.py:199`、`matsimpy/core/crystal.py:588`、`matsimpy/core/molecule.py:147`、`matsimpy/core/molecule.py:486`
- 问题：公开构造器会通过 `_validate_positions()` 拒绝 NaN/Inf，并检查 species/positions 数量一致；但 `_construct()`、`Crystal._construct()`、`Molecule._construct()` 只检查二维 shape，`Crystal.add_atom()` 和 `Molecule.add_atom()` 也没有复用完整坐标验证。
- 影响：用户可以通过正常 mutation API 得到包含 NaN/Inf 坐标的不可变对象；内部 `_construct()` 还能构造 species 和 positions 数量不一致的对象。这会削弱 core value object 的基础契约，并向 IO、storage、transformation、calculator 传播坏数据。
- 证据：本地 probe 复现：`Molecule(...).add_atom("Ne", [nan, 0, 0])` 成功；`Crystal(...).add_atom("Ne", [nan, 0, 0])` 成功并生成 `[nan, nan, nan]` Cartesian 坐标。
- 建议：把 finite 检查、shape 检查、species/positions 长度检查集中到共享构造验证函数；`_construct()` 也必须执行核心不变量验证。为 `add_atom()`、transformation 重建路径和 `_construct()` 增加 NaN/Inf 与长度不一致回归测试。
- 验证状态：已本地复现；现有定向 core 测试通过但未覆盖该路径。

### [P1] `Crystal` equality 和 calculator structural hash 忽略 PBC

- 位置：`matsimpy/core/crystal.py:405`、`matsimpy/core/structure.py:535`、`matsimpy/core/structure.py:581`
- 问题：`set_pbc()` 可以返回 PBC 不同的新晶体，但 `Structure.__eq__()` 只比较 species、positions、lattice；`_structural_hash()` 也不包含 PBC。
- 影响：PBC 不同的晶体会被认为相等，并产生相同 structural hash。若 calculator 缓存或失效逻辑依赖该 hash，可能复用物理边界条件不同的结果。
- 证据：本地 probe 复现：`Crystal(... ) == Crystal(...).set_pbc([False, False, False])` 为 `True`，两者 `_structural_hash()` 也相同。
- 建议：将 PBC 纳入 `Crystal` equality 和 structural hash；如果需要几何等价判断，应新增显式 API，避免混用 simulation-state equality。
- 验证状态：已本地复现；未发现 PBC-sensitive equality/hash 测试。

### [P1] VASP calculator 读取 `vasprun.xml` 时丢弃普通 forces/stress

- 位置：`matsimpy/calculator/vasp/calculator.py:125`、`matsimpy/calculator/vasp/calculator.py:128`、`matsimpy/calculator/vasp/outputs.py:654`、`matsimpy/calculator/vasp/outputs.py:780`
- 问题：`VaspCalculator.read_results()` 读取 `vasprun.final_energy`，但只有存在 `force_constants` 时才从 `ionic_steps` 读取 forces；普通 `vasprun.xml` 的 final ionic step forces/stress 没有进入 `results`。
- 影响：用户解析已有 VASP 输出时会得到 energy，但 `get_forces()` / `get_stress()` 失败，即使输出文件中有这些数据。
- 证据：本地 probe 对 `tests/calculator/fixtures/vasp` 调用 `read_results()` 后，`calc.results.keys()` 只有 `["energy"]`。
- 建议：从 `vasprun.ionic_steps[-1]` 读取常规 forces/stress，并用真实 fixture 增加 energy、forces shape、stress shape 断言。
- 验证状态：已本地复现；当前测试只断言 energy。

### [P1] LAMMPS calculator 输入生成器丢失多元素和非正交晶胞信息

- 位置：`matsimpy/calculator/lammps/calculator.py:79`、`matsimpy/calculator/lammps/calculator.py:83`、`matsimpy/calculator/lammps/calculator.py:97`、`matsimpy/calculator/lammps/calculator.py:101`、`matsimpy/calculator/lammps/data.py:204`、`matsimpy/calculator/lammps/data.py:878`
- 问题：calculator 直接写 `data.lammps` 时硬编码 `1 atom types`、`1 1.0` mass，并把所有原子写为 type 1；周期盒子只使用 `lattice.a/b/c`，不处理 triclinic tilt。项目中已有更完整的 `LammpsData.from_structure()` 和 `lattice_2_lmpbox()`，但 calculator 未复用。
- 影响：多元素体系和非正交晶胞会生成物理错误的 LAMMPS 输入文件。
- 证据：源码确认；现有 calculator 测试没有覆盖 LAMMPS data 文件内容。
- 建议：让 LAMMPS calculator 复用 `LammpsData.from_structure()` 或共享转换 helper；增加多元素、triclinic、molecule box 和 round-trip fixture 测试。
- 验证状态：静态确认；未动态执行 LAMMPS。

### [P1] AI runtime 使用进程级 `_active_executor`，可能跨会话污染

- 位置：`matsimpy/ai/executor.py:267`、`matsimpy/ai/runtime.py:109`、`matsimpy/ai/runtime.py:128`、`matsimpy/ai/skills/io.py:137`、`matsimpy/ai/skills/calculator.py:41`
- 问题：当前 active executor 是 module-level 全局变量；skills 通过 `get_last_structure()` 读取该全局状态。
- 影响：同一 Python 进程内如果存在两个 runtime/engine，会话 A 的 skill 可能读取到会话 B 最近激活的 executor 或 last structure。
- 证据：源码确认；现有测试覆盖单 runtime 内复用，但没有覆盖两个 runtime 并发/交错执行隔离。
- 建议：把 executor/session context 显式注入 skill 调用，或给 runtime 持有独立 context 对象，移除 module-level active executor。
- 验证状态：静态确认；缺少隔离测试。

### [P1] AI storage skill 的“session-level”存储实际是进程级共享

- 位置：`matsimpy/ai/skills/storage.py:14`、`matsimpy/ai/skills/storage.py:15`、`matsimpy/ai/skills/storage.py:20`、`matsimpy/ai/skills/storage.py:29`、`matsimpy/ai/skills/storage.py:38`
- 问题：注释说明是 session-level store，但 `_store = DataStorage(backend=MemoryBackend())` 在模块 import 时创建，所有 session 共用。
- 影响：同一进程内不同用户/任务可以查询或取回彼此通过 AI storage skill 存入的结构。
- 证据：源码确认；没有发现 storage skill session isolation 测试。
- 建议：把 storage 归属移动到 `AgentRuntime`、workspace 或 session，并按 session/workspace namespace。
- 验证状态：静态确认；缺少隔离测试。

### [P1] raw dict storage 绕过 reserved metadata 校验

- 位置：`matsimpy/storage/schema.py:76`、`matsimpy/storage/codec.py:39`、`matsimpy/storage/facade.py:53`
- 问题：`DocumentCodec.encode()` 会调用 `DocumentEnvelope.validate_metadata()`，但 `DataStorage.store_data()` 对 raw `dict` 分支直接构造 `DocumentEnvelope`，没有校验 metadata reserved fields。
- 影响：`DataStorage.store_data({"x": 1}, metadata={"doc_id": "shadow"})` 可以成功，而等价 MSONable 路径会拒绝；storage schema 契约不一致。
- 证据：本地/subagent probe 均确认 raw dict reserved metadata 被接受。
- 建议：raw dict 分支也调用 `DocumentEnvelope.validate_metadata(metadata)`；增加 dict metadata collision 回归测试。
- 验证状态：已复现；现有 storage/contract 测试通过但未覆盖该路径。

### [P1] Transformation registry 多个 spec 与 callable 签名不一致

- 位置：`matsimpy/transformation/registry.py:114`、`matsimpy/transformation/registry.py:115`、`matsimpy/transformation/_register.py:109`、`matsimpy/transformation/lattice/strain.py:11`、`matsimpy/transformation/_register.py:245`、`matsimpy/transformation/atomic/manipulation.py:93`
- 问题：registry 先按 spec schema 校验 kwargs，然后直接 `spec.callable(structure, **kwargs)`；但多个 spec 的参数名与实际 callable 不一致。例如 `apply_strain` schema 是 `strain`，callable 需要 `strain_matrix`；`swap_atoms` schema 是 `i/j`，callable 需要 `index1/index2`。
- 影响：registry-based workflow、TransformationPlan 或 plugin 可以通过 schema 校验但运行时失败。
- 证据：本地 probe 复现：`apply_strain` 报 `unexpected keyword argument 'strain'`；`swap_atoms` 报 `unexpected keyword argument 'i'`。
- 建议：统一 schema 与 callable 签名，或为每个 spec 提供 adapter；contract test 必须 fail unexpected keyword/missing required argument。
- 验证状态：已本地复现。

### [P1] `random_crystal` builder registry contract 失效

- 位置：`matsimpy/builders/_register.py:37`、`matsimpy/builders/_register.py:38`、`matsimpy/builders/_register.py:40`、`matsimpy/builders/bulk/random.py:11`、`matsimpy/utils/schema_validation.py:15`
- 问题：builder spec 使用 `sg` 和 `numIons`，但 callable 需要 `group` 和 `num_ions`，且 `dim` 没有由 schema default 自动应用。
- 影响：`registry.build("random_crystal", sg=..., species=..., numIons=...)` 通过 schema 后仍在 callable 层失败，且失败发生在 optional dependency 处理前。
- 证据：本地 probe 复现：`random_crystal() missing 3 required positional arguments: 'dim', 'group', and 'num_ions'`。
- 建议：对齐 schema 名称和 callable 签名，或者用 adapter 把 PyXtal 风格参数转成内部 callable 参数；增加 registry build contract 测试。
- 验证状态：已本地复现。

## P2 问题

### [P2] Contract tests 过度 skip，掩盖 registry 失效

- 位置：`tests/contracts/test_transformation_contract.py:105`、`tests/contracts/test_builder_contract.py:75`
- 问题：transformation/builder contract 对 `ValueError`、`TypeError`、`IndexError` 大范围 skip，导致 schema/callable mismatch 也能被当成“参数不够具体”跳过。
- 影响：registry 明显不可执行时，契约测试仍然通过。本次 transformation/builder contract 运行结果为 `37 passed, 99 skipped`。
- 建议：区分“测试数据语义不足”和“schema/callable 不一致”；unexpected keyword、missing required positional argument 应失败。
- 验证状态：已由 pytest 输出和 registry probe 交叉确认。

### [P2] AI 文件路径策略仍未集中到 workspace 层

- 位置：`matsimpy/ai/skills/io.py:42`、`matsimpy/ai/skills/io.py:108`、`matsimpy/ai/skills/io.py:125`、`matsimpy/ai/workspace.py:26`、`matsimpy/ai/runtime.py:312`
- 问题：上一轮修复已保护 `_write_structure()` 和 `_save_latex_table()`，但 `Workspace.resolve()` 仍接受 absolute path；runtime 对 tool 返回的 `saved_to` 使用 workspace 校验，其他 skills/read paths 仍各自处理路径。
- 影响：当前两个 IO writer 安全，但 workspace confinement 不是全局不变量；新增 skill 很容易重新引入路径逃逸。
- 建议：在 `Workspace` 增加统一的 `resolve_for_read()` / `resolve_for_write()` 或 `safe_relative_path()`，所有 file-capable skills 强制复用。
- 验证状态：现有 AI path tests 通过；中心化策略未测试。

### [P2] AI function argument validation 只覆盖部分 JSON Schema 类型

- 位置：`matsimpy/ai/executor.py:236`、`matsimpy/ai/executor.py:247`、`matsimpy/ai/executor.py:260`
- 问题：`_validate()` 只处理 required、string、number、integer、array，不验证 boolean、object、enum、items、additionalProperties 等。
- 影响：LLM 传入错误类型时可能进入 skill 内部才失败，错误信息取决于各 skill 实现。
- 建议：实现更完整的小型 schema validator，或引入已有 JSON Schema validator；增加 boolean/object/enum negative tests。
- 验证状态：源码确认；现有 executor tests 未覆盖这些类型。

### [P2] FormatRegistry 允许重复 handler name 覆盖

- 位置：`matsimpy/io/registry.py:84`、`matsimpy/io/registry.py:90`
- 问题：duplicate name guard 的条件只在 `existing.name != handler.name` 时抛错；实际 duplicate name 总是相等，因此后注册 handler 会覆盖 `_by_name`。
- 影响：plugin 或未来 handler 注册可破坏 name lookup，同时旧 extension 仍指向旧 handler。
- 建议：除非是同一 handler 对象，否则 duplicate name 应直接拒绝；或明确定义 replace API。
- 验证状态：subagent probe 确认第二个 `dup` handler 被接受。

### [P2] Storage backend contract 未覆盖 MaggmaBackend

- 位置：`tests/contracts/test_storage_backend_contract.py:27`、`tests/contracts/test_storage_backend_contract.py:33`
- 问题：文件注释说覆盖 MemoryBackend 和 MaggmaBackend，但 fixture params 只有 `["memory"]`。
- 影响：持久化 backend 的 put/get/query/delete/flush/close 回归可能通过官方 contract suite。
- 建议：安装 maggma 时参数化真实 MaggmaBackend；无 maggma CI 可用 fake-backed adapter 验证协议行为。
- 验证状态：IO/storage scoped tests 通过，但不能证明 MaggmaBackend contract parity。

### [P2] IO 有两套 registry/extension 数据源，缺少漂移保护

- 位置：`matsimpy/io/core.py:41`、`matsimpy/io/registry.py:117`、`matsimpy/io/utils.py:9`、`tests/io/test_io_utils.py:94`
- 问题：高层 read/write 使用 `FormatRegistry`，但 `io.utils` 维护独立的 `FORMAT_REGISTRY` 和 alias 表。
- 影响：public utility helpers 可能与实际 dispatch 行为漂移。
- 建议：让 `io.utils` 派生自 `FormatRegistry`，或增加 extension/support parity contract test。
- 验证状态：当前 probe 显示 extension 集合一致，但架构仍易漂移。

### [P2] Transformation metadata 不可靠

- 位置：`matsimpy/transformation/_register.py:46`、`matsimpy/transformation/geometric/translation.py:47`、`matsimpy/transformation/_register.py:388`、`matsimpy/transformation/structural/molecular.py:20`
- 问题：一些 spec 声称 `output_type=Crystal`，但对 `Molecule` 输入返回 `Molecule`；`fragment_molecule` 实际返回 `List[Molecule]`，spec 声称 `Molecule`。
- 影响：introspection、UI generation、plugin compatibility、plan validation 不能信任 metadata。
- 建议：引入 `same_as_input`、collection output type 或更准确的 output descriptor；增加 metadata-vs-real-result 测试。
- 验证状态：静态确认。

### [P2] Core `formula` 语义和文档/化学惯例不一致

- 位置：`matsimpy/core/structure.py:447`、`matsimpy/core/composition.py:327`、`matsimpy/core/molecule.py:21`
- 问题：`Structure.formula` 按 species 首次出现顺序生成；`Composition.canonical_formula` 另有 canonical 语义。文档示例容易让用户期待水为 `H2O`，实际 `Molecule(["O","H","H"]).formula` 是 `OH2`。
- 影响：用户可见 API 与化学惯例/文档预期不一致，可能影响展示、报告和比较。
- 建议：明确文档说明 `Structure.formula` 是 order-preserving；需要化学标准显示时使用 canonical formula。若改变默认行为，需要迁移说明。
- 验证状态：subagent probe 已确认。

### [P2] Core value object 承担过多 adapter/应用责任

- 位置：`matsimpy/core/crystal.py:1590`、`matsimpy/core/crystal.py:1658`、`matsimpy/core/crystal.py:1724`、`matsimpy/core/crystal.py:1789`、`matsimpy/core/molecule.py:1045`
- 问题：`Crystal`/`Molecule` 内直接承载 IO、第三方转换、代码接口、symmetry、transformation 等应用层方法。
- 影响：核心值对象边界变宽，每个上层模块变更都可能影响 core API、immutability、serialization 和测试复杂度。
- 建议：中期将 adapter 能力迁移到独立模块或服务函数，core 保留兼容 wrapper。
- 验证状态：静态架构发现。

### [P2] 外部 calculator parse 失败语义过弱

- 位置：`matsimpy/calculator/base.py:160`、`matsimpy/calculator/base.py:168`、`matsimpy/calculator/gaussian/calculator.py:106`、`matsimpy/calculator/lammps/calculator.py:133`
- 问题：base `read_results()` 在 `_parse_output()` 后无条件设置 `_calculation_performed=True`；Gaussian/LAMMPS output 文件缺失时直接 return。
- 影响：用户之后只得到 `Energy not available` / `Forces not available`，丢失具体文件路径和 parse failure 原因。
- 建议：区分 no output、parse failed、property absent；增加带 directory/file context 的异常或 warning。
- 验证状态：源码确认；现有测试未覆盖缺失外部输出语义。

### [P2] Calculator optional dependency 策略不一致

- 位置：`matsimpy/calculator/mattersim/dataloader.py:19`、`matsimpy/calculator/lj/calculator.py:8`
- 问题：MatterSim 延迟导入 optional dependency 并提供明确错误；LJ 在 module import 时直接导入 SciPy；其他 calculator 也缺少统一策略。
- 影响：用户难以预测不同 calculator 在缺少 optional stack 时是 import 失败、初始化失败还是运行失败。
- 建议：为 calculator family 定义统一 optional dependency policy，并用 packaging/import tests 锁住。
- 验证状态：本地环境目标测试通过；这是 portability 风险。

### [P2] Plugin discovery 行为在 transformation 和 builder 间不一致

- 位置：`matsimpy/plugins.py:44`、`matsimpy/plugins.py:68`、`matsimpy/plugins.py:72`
- 问题：transformation plugin discovery 接受单个 spec 或 list；builder discovery 假定返回 iterable，并吞掉所有异常。
- 影响：builder plugin 返回单个 `BuilderSpec` 时可能静默失败。
- 建议：统一 single/list handling，注册前验证 spec 类型，并避免吞掉所有异常。
- 验证状态：静态确认；未发现 plugin discovery tests。

## P3 问题

- IO format contract 在 writer exception 时 skip，可能掩盖 broken writer；建议对声明支持 writer 的 handler 失败而不是 skip。
- Storage backend lifecycle 语义不明确：`MemoryBackend.close()` 清空数据，但关闭后仍可写；建议统一 connected-state contract。
- Provider 边界对 HTTP error 和 malformed tool-call JSON 的测试较少；建议补 provider-level negative tests。
- Core mutation 内硬编码 `0.5 Angstrom` “chemical reasonableness” 距离策略；建议可配置或上移到 builder/sanitizer。
- transformation 中 structure rebuild/copy 逻辑和已有 helper 重复；建议低风险迁移到共享 helper。
- calculator parser/input 代码有少量 polish 问题，例如重复 future import、未使用 import；建议在行为测试补强后用 ruff/pyflakes 清理。

## Core 模块审查

Core 是本次审查风险最高的模块。现有测试对不可变返回、只读 `_positions`、unhashable core classes、site property isolation、species validation、cache invalidation 有覆盖；但 mutation reconstruction 路径弱于公开构造器，PBC 没进入 equality/hash，formula 语义也需要明确。建议优先修复不变量绕过和 PBC equality/hash，再逐步收窄 `Crystal`/`Molecule` 的 adapter 责任。

## IO / Storage / Serialization 审查

IO/storage happy path 测试强，定向 suite 通过；主要问题集中在 contract gap 和重复元数据源：raw dict storage 没有走 reserved metadata 校验，FormatRegistry duplicate name guard 有缺陷，MaggmaBackend 未进入 backend contract，`io.utils` 与 runtime registry 有漂移风险。

## AI Runtime / Skills 审查

AI 测试覆盖较广，相关定向测试通过。架构风险集中在 process-global 状态：`_active_executor` 和 storage skill `_store` 都不是 session-local。上一轮路径写入修复有效，但 workspace 路径策略仍未中心化。schema validation 和 provider negative tests 也需要补强。

## Calculator 审查

VASP 和 LAMMPS 的用户可见正确性风险仍然较高：VASP fixture 中 forces/stress 没被读入，LAMMPS calculator 自写 data 文件丢失多元素和 triclinic 信息。外部输出缺失/parse failure 的错误语义也需要改进。

## Transformation / Builders 审查

最大问题是 registry contract：多个 transformation spec 和 builder spec 与 callable 签名不一致，且 contract tests 的 skip 策略没有抓住这些错误。metadata 的 output_type 表达能力也不足，影响未来 UI、plugin 和 plan validation。

## 测试质量审查

测试数量和覆盖面不错，但需要提高“契约测试的失败敏感度”。目前多个 contract suites 可以因为 broad skip 而放过真实 registry 错误。建议把 skip 用于 optional dependency 或语义无法自动生成参数的情况；unexpected keyword、missing required positional argument、reserved metadata bypass、duplicate registry name 等应成为明确失败。

## 分阶段修复计划

### 阶段 1：P1 正确性和隔离风险收敛

- 目标：修复最可能影响用户结果、数据隔离和 registry 可用性的 P1 问题。
- 涉及文件：`matsimpy/core/structure.py`、`matsimpy/core/crystal.py`、`matsimpy/core/molecule.py`、`matsimpy/calculator/vasp/calculator.py`、`matsimpy/calculator/lammps/calculator.py`、`matsimpy/storage/facade.py`、`matsimpy/ai/executor.py`、`matsimpy/ai/runtime.py`、`matsimpy/ai/skills/storage.py`、`matsimpy/transformation/_register.py`、`matsimpy/builders/_register.py`。
- 建议步骤：先写回归测试；修复 Core 不变量和 PBC hash/equality；修复 storage raw dict metadata；修复 VASP forces/stress；修复 registry 参数名；为 AI session isolation 设计 context 注入方案。
- 验证方式：运行 core、storage、calculator、AI、transformation/builder targeted tests，并增加针对每个 P1 的最小回归测试。
- 风险：PBC 纳入 equality/hash 可能影响既有比较语义；AI context 注入可能触及 skill 调用接口，应单独设计。

### 阶段 2：Registry 和 contract test 强化

- 目标：让 contract tests 能抓住 schema/callable mismatch、duplicate registry、metadata drift。
- 涉及文件：`tests/contracts/test_transformation_contract.py`、`tests/contracts/test_builder_contract.py`、`tests/contracts/test_io_format_contract.py`、`tests/contracts/test_storage_backend_contract.py`、`matsimpy/io/registry.py`。
- 建议步骤：收紧 broad skip；对 unexpected keyword 和 missing required arg 失败；增加 duplicate handler name 测试；让 storage backend contract 覆盖 MaggmaBackend 或 fake adapter。
- 验证方式：运行 `tests/contracts` 全部测试和相关 module suites。
- 风险：收紧 contract 后会暴露更多旧问题，建议分小 commit 修复。

### 阶段 3：Workspace、optional dependency 和错误语义统一

- 目标：统一文件路径、optional dependency、external output failure 的用户体验。
- 涉及文件：`matsimpy/ai/workspace.py`、`matsimpy/ai/skills/*.py`、`matsimpy/calculator/base.py`、`matsimpy/calculator/*/calculator.py`、`matsimpy/transformation/lattice/transform.py`。
- 建议步骤：建立 workspace read/write path API；所有 file-capable skills 迁移；定义 calculator optional dependency policy；为 missing output/parse failure 增加明确异常。
- 验证方式：新增 negative tests：路径逃逸、缺依赖、缺输出文件、malformed provider/tool args。
- 风险：路径策略收紧可能影响现有用户使用 absolute path 的习惯，需要迁移说明或 trusted root 设计。

### 阶段 4：Core 边界收窄和低风险清理

- 目标：降低 core class 责任，减少重复和维护噪音。
- 涉及文件：`matsimpy/core/crystal.py`、`matsimpy/core/molecule.py`、`matsimpy/transformation/_helpers.py`、`matsimpy/transformation/**/*.py`、`matsimpy/calculator/vasp/inputs.py`。
- 建议步骤：保留兼容 wrapper，把第三方转换、code interface、builder-like 方法逐步移到 adapter/service 模块；迁移 transformation rebuild 逻辑到 helper；运行 lint/pyflakes 做 polish。
- 验证方式：先加 adapter contract tests，再分模块迁移；每步运行对应 targeted suite。
- 风险：公共 API 迁移需要兼容周期，避免一次性破坏用户导入。

## 已验证

- `python - <<'PY' ... import matsimpy/core/io/storage/transformation/builders/calculator/ai ... PY`：主模块导入成功，`matsimpy.__version__ == 0.8.0`。
- `python -m pytest tests/test_packaging_runtime_contracts.py -q`：`8 passed`。
- Core subagent：`pytest tests/core/test_core_design_fixes.py tests/core/test_immutability.py tests/core/test_hash_robustness.py tests/core/test_structure_mutations.py tests/core/test_site_properties_validation.py tests/core/test_composition_cache_and_errors.py -q`：`87 passed`。
- AI subagent：`conda run -n pmg python -m pytest tests/ai/test_io_skill_paths.py tests/ai/test_runtime.py tests/ai/test_skill_loader.py tests/ai/test_executor.py tests/ai/test_providers.py tests/ai/test_memory.py tests/ai/test_session_store.py`：`115 passed`。
- Calculator subagent：`PYTHONDONTWRITEBYTECODE=1 pytest -q -p no:cacheprovider tests/calculator/test_calculator_base.py tests/calculator/test_vasp_calculator.py tests/calculator/test_gaussian.py tests/calculator/test_calculator_mattersim.py tests/calculator/test_calculator_lennard_jones.py`：`77 passed`。
- Transformation/builders subagent：`PYTHONDONTWRITEBYTECODE=1 pytest -q tests/contracts/test_transformation_contract.py tests/contracts/test_builder_contract.py -p no:cacheprovider`：`37 passed, 99 skipped`；`PYTHONDONTWRITEBYTECODE=1 pytest -q tests/transformation tests/builders -p no:cacheprovider`：`199 passed`。
- IO/storage subagent：`pytest tests/io tests/storage tests/contracts/test_io_format_contract.py tests/contracts/test_storage_backend_contract.py -q`：`186 passed, 1 skipped`。
- 本地 probe 复现：Core NaN mutation、PBC equality/hash、raw dict reserved metadata bypass、VASP forces/stress omission、transformation registry 参数 mismatch、`random_crystal` builder mismatch。

## 未验证

- 未运行全仓库测试。
- 未运行真实 VASP、Gaussian、LAMMPS、MatterSim 外部二进制或模型推理。
- 未验证需要网络、API key 或外部服务的 AI provider 行为。
- 未在缺少 SciPy/ASE/pymatgen/spglib/maggma/torch/rdkit/pyxtal 的隔离环境中逐一验证 optional dependency 行为。
- 未动态验证 plugin entry point 发现流程。
