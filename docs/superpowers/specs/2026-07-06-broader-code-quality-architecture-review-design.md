# MatSimPy 更广泛代码质量与架构审查设计

日期：2026-07-06

## 1. 目标

对 MatSimPy 做一次只读的全项目代码质量与架构审查，输出中文审查报告和中文分阶段修复计划。

本阶段不修改代码、不重构、不提交实现补丁。审查完成后，修复工作必须通过单独的实现计划进入后续阶段。

## 2. 输出

审查最终交付两部分：

1. 中文代码质量/架构审查报告。
2. 中文分阶段修复计划。

报告中的每个问题应包含：

- 优先级：P0、P1、P2 或 P3。
- 受影响文件和具体位置。
- 问题描述。
- 影响范围。
- 证据：代码引用、测试行为、命令输出或明确的推理链。
- 建议修复方向。

修复计划应包含：

- 阶段划分。
- 每阶段目标。
- 推荐修改范围。
- 推荐验证方式。
- 风险和依赖关系。

## 3. 审查范围

审查覆盖整个项目，但按风险和架构价值排序。

主要模块：

- `matsimpy/core/`：核心数据模型、不可变性、结构/分子/晶体边界、坐标语义、site/species 表示、序列化契约、hash/equality 行为和 mutation API。
- `matsimpy/io/`：格式注册、读写入口、格式探测、第三方对象转换、错误边界。
- `matsimpy/ai/`：runtime、providers、skills、workspace、session/memory 边界。
- `matsimpy/calculator/`：外部计算器接口、输入输出文件生成、子进程边界、可选依赖行为。
- `matsimpy/storage/`：存储抽象、document schema、codec、后端契约。
- `matsimpy/transformation/`：转换注册、组合 pipeline、结构变换契约。
- `matsimpy/builders/`：构建器注册、输入验证、可选依赖和返回对象一致性。
- `tests/`：契约测试、回归测试、集成测试、测试脆弱性和覆盖缺口。

次要范围：

- `docs/` 与 `README.md` 中公开承诺和实际行为不一致的问题。
- `pyproject.toml` 中 packaging、optional extras、test config 相关问题。

## 4. Core 模块重点审查内容

`matsimpy/core/` 是全项目最重要的架构边界，审查必须单独覆盖以下内容：

- `Structure`、`Crystal`、`Molecule`、`Site`、`Lattice`、`Composition`、`Element` 的职责是否清晰，是否存在互相泄漏实现细节的问题。
- `Crystal` 和 `Molecule` 的坐标约定是否一致、明确且不容易误用，尤其是 fractional/cartesian 转换边界。
- mutation API 是否真正保持 immutable-return 契约，是否存在共享 list、numpy array 或 site object 导致的别名修改。
- `species`、`positions`、`sites`、`lattice`、`properties` 等内部状态是否有统一的验证入口和错误语义。
- `to_dict`、`from_dict`、文件 IO、storage codec 是否依赖不稳定的内部表示。
- `__eq__`、`__hash__`、composition cache、formula 生成是否在浮点、元素顺序和 mutable state 下保持稳定。
- 核心对象是否承担过多格式转换、分析或 builder 责任，导致模块边界变宽。
- 核心测试是否覆盖对象不变量，而不是只覆盖当前实现细节。

Core 审查发现应优先判断为 P0/P1/P2，因为它们通常会影响 IO、storage、transformation、builders、calculator 和 AI skill 的上层行为。

## 5. 严重度定义

- **P0**：仍可能直接破坏用户数据、安全边界、科学正确性或公开 API 的基本可用性。
- **P1**：架构/API 边界问题，会显著增加未来 bug、破坏扩展或造成用户迁移成本。
- **P2**：局部代码质量、重复逻辑、测试脆弱性、错误处理不一致，建议近期修复。
- **P3**：低风险清理项，例如命名、组织、轻量重复、文档一致性，适合 cleanup 阶段处理。

这次审查允许报告 P3，但最终报告必须按优先级分层，不能让低风险清理掩盖关键架构风险。

## 6. 审查方法

审查采用“风险分层 + 证据驱动”的方式：

1. 项目地图：梳理模块边界、公共入口、测试布局和最近提交，明确当前架构形态。
2. Core 深读：先审查核心数据模型和不变量，因为其他模块都依赖这些基础契约。
3. 架构边界审查：检查核心对象、注册表、IO、AI skill、calculator、storage 和 transformation 之间的职责是否清晰。
4. 公共 API 审查：检查公开入口、optional dependency 行为、错误类型、返回对象和文档承诺。
5. 测试质量审查：检查是否有契约测试覆盖关键边界，是否存在过度 mock、实现细节耦合或遗漏高风险路径。
6. 局部质量审查：查找复杂函数、重复逻辑、隐式状态、异常吞噬、命名不清和可维护性问题。
7. 证据验证：对可疑点运行最小必要命令，例如 `rg`、定向 `pytest`、导入 smoke test 或小型 Python 片段。

审查可以使用静态阅读和命令验证，但不允许修改源代码、测试或配置。

## 7. 非目标

本审查不做以下事项：

- 不修复代码。
- 不重排目录。
- 不引入新依赖。
- 不跑耗时或需要网络/外部服务的全量验证，除非后续用户明确要求。
- 不把纯风格偏好包装成架构问题。

## 8. 成功标准

审查完成时必须满足：

- 覆盖主要模块和测试结构。
- Core 模块的不变量、坐标语义、不可变性和序列化边界被单独审查。
- 每个高优先级问题都有具体文件位置和证据。
- 报告区分事实、推理和未验证假设。
- 修复计划按阶段组织，能直接转化为后续 implementation plan。
- 最终审查报告和修复计划使用中文。

## 9. 后续流程

用户批准本设计后，下一步进入 implementation-planning 阶段，产出详细执行计划。执行计划应先定义审查命令、阅读顺序、证据收集方式和最终报告结构，再开始实际审查。
