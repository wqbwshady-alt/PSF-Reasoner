"""Optional-component status registry.

Wires optional integrations (LLM, cloud compute, FoldX, OpenBabel)
report whether they are enabled, available, and which implementation is
actually in use.  The registry powers the API /health payload and the
per-report runtime record, replacing silent ``except Exception: return
None`` degradation with observable state.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock


@dataclass(frozen=True, slots=True)
class ComponentStatus:
    """One optional component's effective state."""

    name: str
    enabled: bool
    available: bool
    implementation: str
    detail: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "available": self.available,
            "implementation": self.implementation,
            "detail": self.detail,
        }


class ComponentRegistry:
    """Thread-safe registry of ComponentStatus entries."""

    def __init__(self) -> None:
        self._statuses: dict[str, ComponentStatus] = {}
        self._lock = RLock()

    def set(self, status: ComponentStatus) -> None:
        with self._lock:
            self._statuses[status.name] = status

    def get(self, name: str) -> ComponentStatus | None:
        with self._lock:
            return self._statuses.get(name)

    def snapshot(self) -> dict[str, dict[str, object]]:
        """Serializable snapshot of all registered components."""
        with self._lock:
            return {name: status.to_dict() for name, status in self._statuses.items()}


component_registry = ComponentRegistry()
