"""
TransformationPlan — serializable sequence of transformation steps.

Separates the description of "what to do" from the execution strategy.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TransformationStep:
    """A single step in a transformation plan.

    Attributes:
        spec_name: Registry key, e.g. ``"translate"``.
        params: Kwargs passed to the transformation function.
        label: Optional human-readable label for this step.
    """

    spec_name: str
    params: dict = field(default_factory=dict)
    label: str | None = None

    def to_dict(self) -> dict:
        return {
            "spec_name": self.spec_name,
            "params": self.params,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, d: dict) -> TransformationStep:
        return cls(
            spec_name=d["spec_name"],
            params=d.get("params", {}),
            label=d.get("label"),
        )


@dataclass
class TransformationPlan:
    """A serializable, reproducible sequence of transformation steps.

    Usage::

        plan = TransformationPlan(
            steps=[
                TransformationStep("make_supercell", {"scaling_matrix": [2, 2, 2]}),
                TransformationStep("create_vacancy", {"indices": [0]}),
            ],
            name="2x2x2 supercell with vacancy",
        )
        result = registry.apply_plan(plan, crystal)
    """

    steps: list[TransformationStep] = field(default_factory=list)
    name: str | None = None
    description: str | None = None

    def to_dict(self) -> dict:
        return {
            "steps": [s.to_dict() for s in self.steps],
            "name": self.name,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, d: dict) -> TransformationPlan:
        return cls(
            steps=[TransformationStep.from_dict(s) for s in d["steps"]],
            name=d.get("name"),
            description=d.get("description"),
        )


__all__ = ["TransformationStep", "TransformationPlan"]
