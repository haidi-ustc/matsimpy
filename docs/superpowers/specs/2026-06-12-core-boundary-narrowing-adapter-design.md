# MatSimPy Core 边界收窄 & Adapter 层设计

日期: 2026-06-12

## 1. 目标

收窄 `matsimpy/core/` 的职责边界，使其只包含数据模型和基本 mutation，不再依赖任何外层模块（adapters、calculator、io、transformation、symmetry、builders、analysis、code）。

## 2. 目标架构

```
                        ┌─────────────────────────────────┐
                        │        外部库 / 第三方            │
                        │   ase  pymatgen  pyxtal  rdkit  │
                        └──────┬──────────────────┬───────┘
                               │                  │
                               ▼                  ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ adapters/library/ │   │ adapters/code/    │   │ builders/        │
│  ase.py          │   │  python.py        │   │ calculator/      │
│  pymatgen.py     │   └────────┬─────────┘   │ io/              │
│  (future: rdkit) │            │              │ symmetry/        │
└────────┬─────────┘            │              │ transformation/  │
         │                      │              │ analysis/        │
         │    ┌─────────────────┴──────────────┴─────────────────┘
         │    │              全部依赖 core
         ▼    ▼
┌──────────────────────────────────────────────────────────────┐
│                        core/                                  │
│  constants.py          protocols.py                          │
│  exceptions.py         ├── StructureLike                     │
│  utils/                ├── CrystalLike                       │
│                        ├── MoleculeLike                      │
│  structure.py          ├── CalculatorLike  (new)             │
│  crystal.py            │                                      │
│  molecule.py           │                                      │
│  lattice.py            │                                      │
│  composition.py        │                                      │
│  site.py               │                                      │
│  periodic_table.py     │                                      │
│  symmop.py             │                                      │
│                                                              │
│  只 import: constants, exceptions, utils, protocols          │
│  绝不 import: adapters, calculator, io, transformation,      │
│              symmetry, builders, analysis, code              │
└──────────────────────────────────────────────────────────────┘
```

核心原则：**core 只做数据模型 + 基本 mutation，不做任何对外层模块的 import。所有外层模块单向依赖 core。**

## 3. 按问题分解

| 问题 | 类别 | 解法 |
|------|------|------|
| to_ase / to_pymatgen / from_ase / from_pymatgen | 外部库转换 | 新建 `adapters/library/` + LibraryAdapterRegistry |
| to_code / from_code | 代码生成 | 新建 `adapters/code/` + CodeAdapterRegistry |
| make_supercell / perturb / get_symmetry_info / random_crystal | 内部服务委托 | 从 core 删除 convenience method |
| Structure.calc | 策略委托 | CalculatorLike Protocol 替代直接 import |

## 4. CalculatorLike Protocol

### 4.1 定义

```python
# core/protocols.py

from typing import Protocol, runtime_checkable, Any

@runtime_checkable
class CalculatorLike(Protocol):
    """Structure 对 calculator 的唯一认知。"""

    def calculate(self, structure: StructureLike, **kwargs) -> None:
        """执行计算。"""
        ...

    @property
    def results(self) -> dict[str, Any]:
        """计算结果。key: 'energy', 'forces', 'stress'。"""
        ...

    @property
    def calculation_performed(self) -> bool:
        """是否已完成计算。"""
        ...
```

### 4.2 Structure 层改动

```python
# core/structure.py

class Structure(ABC, MSONable):
    _calc: CalculatorLike | None = None

    @property
    def calc(self) -> CalculatorLike | None:
        return self._calc

    @calc.setter
    def calc(self, calculator: CalculatorLike):
        # 只检查 Protocol，不 import 具体类
        from .protocols import CalculatorLike
        if not isinstance(calculator, CalculatorLike):
            raise TypeError(f"Expected CalculatorLike, got {type(calculator)}")
        self._calc = calculator
        self._reset_cache()

    def get_potential_energy(self) -> float:
        if self.calc is None:
            raise RuntimeError("No calculator attached")
        if self._needs_calculation():
            self.calc.calculate(self)
        return self.calc.results["energy"]

    def get_forces(self) -> np.ndarray:
        if self.calc is None:
            raise RuntimeError("No calculator attached")
        if self._needs_calculation():
            self.calc.calculate(self)
        return self.calc.results["forces"]
```

### 4.3 需要删除的 import

```python
# core/structure.py 删除:
from ..calculator.base import Calculator    # lazy import，删除
```

`calculator/base.py` 的 `Calculator` 类天然满足 `CalculatorLike` Protocol，零改动。

## 5. Adapter 层

### 5.1 分类

| | Library Adapter | Code Adapter |
|---|---|---|
| 输入 | 外部库对象 | 代码字符串 |
| 输出 | 外部库对象 | 代码字符串 |
| 依赖 | 可选第三方库 (ase, pymatgen) | 无第三方依赖 |
| 使用场景 | 互操作、计算器对接 | 脚本生成、notebook embedding |

### 5.2 文件结构

```
matsimpy/adapters/
├── __init__.py                 # 统一对外入口
├── library/
│   ├── __init__.py
│   ├── spec.py                 # LibraryAdapterSpec
│   ├── registry.py             # LibraryAdapterRegistry 单例
│   ├── _register.py            # 自动注册内置库适配器
│   ├── ase.py                  # Crystal/Molecule ↔ ase.Atoms
│   └── pymatgen.py             # Crystal/Molecule ↔ pymatgen.Structure
└── code/
    ├── __init__.py
    ├── spec.py                 # CodeAdapterSpec
    ├── registry.py             # CodeAdapterRegistry 单例
    ├── _register.py
    └── python.py               # Crystal/Molecule ↔ Python 构造代码
```

### 5.3 LibraryAdapterSpec

```python
# adapters/library/spec.py

from dataclasses import dataclass
from typing import Callable, Any

@dataclass(frozen=True)
class LibraryAdapterSpec:
    name: str                      # "ase", "pymatgen"
    to_external: Callable          # (Structure, **kwargs) -> external_obj
    from_external: Callable        # (external_obj, **kwargs) -> Structure
    external_type: type            # 目标类型，如 ase.Atoms
    supports_crystal: bool = True
    supports_molecule: bool = True
    optional_dependency: str | None = None   # pip 包名
    install_hint: str | None = None          # "pip install matsimpy[io]"
```

### 5.4 LibraryAdapterRegistry

```python
# adapters/library/registry.py

class LibraryAdapterRegistry:
    """单例。"""

    _instance: ClassVar["LibraryAdapterRegistry | None"] = None

    def __new__(cls) -> "LibraryAdapterRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._specs: dict[str, LibraryAdapterSpec] = {}
        return cls._instance

    def register(self, spec: LibraryAdapterSpec) -> None:
        if spec.name in self._specs:
            raise RegistryError(f"Library adapter '{spec.name}' already registered")
        self._specs[spec.name] = spec

    def get(self, name: str) -> LibraryAdapterSpec:
        spec = self._specs.get(name)
        if spec is None:
            raise RegistryError(f"Unknown library adapter: {name}")
        return spec

    def to_external(self, structure, target: str, **kwargs):
        spec = self.get(target)
        self._check_optional_dep(spec)
        if not spec.supports_crystal and isinstance(structure, Crystal):
            raise StructureTypeError(f"'{target}' adapter does not support Crystal")
        return spec.to_external(structure, **kwargs)

    def from_external(self, external_obj, target: str, **kwargs):
        spec = self.get(target)
        self._check_optional_dep(spec)
        if not isinstance(external_obj, spec.external_type):
            raise TypeError(
                f"Expected {spec.external_type.__name__}, "
                f"got {type(external_obj).__name__}"
            )
        return spec.from_external(external_obj, **kwargs)

    def _check_optional_dep(self, spec: LibraryAdapterSpec) -> None:
        if spec.optional_dependency is None:
            return
        try:
            importlib.import_module(spec.optional_dependency)
        except ImportError:
            raise ImportError(spec.install_hint or
                f"Optional dependency '{spec.optional_dependency}' required. "
                f"Install with: pip install matsimpy[io]")
```

### 5.5 CodeAdapterSpec

```python
# adapters/code/spec.py

@dataclass(frozen=True)
class CodeAdapterSpec:
    name: str                      # "python"
    language: str                  # "python"
    encode: Callable               # (Structure, **kwargs) -> str
    decode: Callable               # (str, **kwargs) -> Structure
```

### 5.6 CodeAdapterRegistry

```python
# adapters/code/registry.py

class CodeAdapterRegistry:
    """单例。"""

    _instance: ClassVar["CodeAdapterRegistry | None"] = None

    def __new__(cls) -> "CodeAdapterRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._specs: dict[str, CodeAdapterSpec] = {}
        return cls._instance

    def register(self, spec: CodeAdapterSpec) -> None:
        if spec.name in self._specs:
            raise RegistryError(f"Code adapter '{spec.name}' already registered")
        self._specs[spec.name] = spec

    def encode(self, structure, target: str = "python", **kwargs) -> str:
        spec = self._specs[target]
        return spec.encode(structure, **kwargs)

    def decode(self, code_str: str, target: str = "python", **kwargs) -> Structure:
        spec = self._specs[target]
        return spec.decode(code_str, **kwargs)
```

### 5.7 Code Adapter vs IO 层

| | IO (FormatRegistry) | Code Adapter |
|---|---|---|
| 输入输出 | 文件 ↔ Structure | 代码字符串 ↔ Structure |
| 媒介 | 磁盘文件 | 内存字符串 |
| 格式 | cif, vasp, xyz, json, pdb... | python (未来可扩展 julia, c++) |
| 用途 | 持久化、数据交换 | 脚本生成、notebook embedding |

`code` adapter 独立于 `io/`，是不同维度的序列化。

### 5.8 使用方式

```python
# 库适配器
from matsimpy.adapters.library import get_registry
atoms = get_registry().to_external(crystal, "ase")
pmg = get_registry().to_external(crystal, "pymatgen")
crystal2 = get_registry().from_external(atoms, "ase")

# 代码适配器
from matsimpy.adapters.code import CodeAdapterRegistry
code = CodeAdapterRegistry().encode(crystal, "python")
```

### 5.9 插件入口

```ini
# pyproject.toml
[project.entry-points."matsimpy.adapters"]
ase = "matsimpy.adapters.library.ase"
pymatgen = "matsimpy.adapters.library.pymatgen"
code-python = "matsimpy.adapters.code.python"
```

## 6. Core 冗余 Wrapper 删除

### 6.1 删除清单

| 方法 | 当前位置 | 迁移到 |
|------|----------|--------|
| `Crystal.to_ase` | crystal.py | `adapters/library` registry |
| `Crystal.from_ase` | crystal.py | `adapters/library` registry |
| `Crystal.to_pymatgen` | crystal.py | `adapters/library` registry |
| `Crystal.from_pymatgen` | crystal.py | `adapters/library` registry |
| `Molecule.to_ase` | molecule.py | `adapters/library` registry |
| `Molecule.from_ase` | molecule.py | `adapters/library` registry |
| `Molecule.to_pymatgen` | molecule.py | `adapters/library` registry |
| `Molecule.from_pymatgen` | molecule.py | `adapters/library` registry |
| `Crystal.to_code` | crystal.py | `adapters/code` registry |
| `Crystal.from_code` | crystal.py | `adapters/code` registry |
| `Molecule.to_code` | molecule.py | `adapters/code` registry |
| `Molecule.from_code` | molecule.py | `adapters/code` registry |
| `Crystal.make_supercell` | crystal.py:1834 | 用户直接调 `transformation.make_supercell(crystal, ...)` |
| `Crystal.perturb` | crystal.py:1864 | 用户直接调 `transformation.perturb(crystal, ...)` |
| `Molecule.perturb` | molecule.py:1153 | 用户直接调 `transformation.perturb(molecule, ...)` |
| `Crystal.get_symmetry_info` | crystal.py:1759 | 用户直接调 `symmetry.get_symmetry_info(crystal)` |
| `Crystal.get_conventional_cell` | crystal.py:1773 | 用户直接调 `symmetry.get_conventional_cell(crystal)` |
| `Crystal.random_crystal` | crystal.py | 用户直接调 `builders.random_crystal(...)` |

### 6.2 无向后兼容

不做 DeprecationWarning 过渡，直接删除。所有调用方同步更新为新 API。

## 7. IO 层改动

```
io/ase.py               删除 to_ase, from_ase; 保留 read_ASE, write_ASE
io/pymatgen.py          删除 to_pymatgen, from_pymatgen
io/__init__.py          删除四个函数的 re-export
```

`io/` 内部如需调用转换函数，改为从 `matsimpy.adapters.library` import。依赖方向：io → adapters → core。

## 8. 实施步骤

### Step 1: CalculatorLike Protocol (零破坏性)
- `core/protocols.py`: 新增 `CalculatorLike`
- `core/structure.py`: calc setter 改用 `CalculatorLike`；删除 `from ..calculator.base import Calculator`
- 验证: 现有 calculator 测试全部通过

### Step 2: 创建 adapters/ 包 (新增，零破坏性)
- `adapters/__init__.py`
- `adapters/library/__init__.py`, `spec.py`, `registry.py`
- `adapters/library/ase.py` ← 从 `io/ase.py` 迁移逻辑
- `adapters/library/pymatgen.py` ← 从 `io/pymatgen.py` 迁移逻辑
- `adapters/library/_register.py`
- `adapters/code/__init__.py`, `spec.py`, `registry.py`
- `adapters/code/python.py` ← 从 `core/crystal.py` / `core/molecule.py` 迁移逻辑
- `adapters/code/_register.py`
- 验证: 新增 adapter 单元测试

### Step 3: 删除 core 中的 convenience method (破坏性)
- `core/crystal.py`: 删除所有 4.1 列出的方法
- `core/molecule.py`: 删除所有 4.1 列出的方法
- 验证: 无 import 错误

### Step 4: 清理 io/ 层 (破坏性)
- `io/ase.py`: 删除 `to_ase`, `from_ase`
- `io/pymatgen.py`: 删除 `to_pymatgen`, `from_pymatgen`
- `io/__init__.py`: 删除 re-export
- 验证: io 测试更新

### Step 5: 更新所有调用方 (破坏性)
- `tests/`: 所有使用旧 API 的测试改为新 API
- `builders/`: 如 `random.py` 中的 `from_pymatgen` → 走 adapter registry
- `ai/skills/io.py`: wrapper 函数改为调用 adapter registry
- 验证: 全量测试通过

### Step 6: 注册插件入口
- `pyproject.toml`: 新增 `[project.entry-points."matsimpy.adapters"]`

## 9. Core import 清理后的最终状态

清理后 `core/` 中删除所有以下 import（包括 lazy import）：

```
from ..calculator import ...       → CalculatorLike Protocol 替代
from ..io import ...               → adapter registry 替代
from ..adapters import ...         → 删除
from ..transformation import ...   → wrapper 删除
from ..symmetry import ...         → wrapper 删除
from ..builders import ...         → wrapper 删除
from ..analysis import ...         → wrapper 删除
```

core 只保留内部 import：`constants`, `exceptions`, `utils`, `protocols`。
