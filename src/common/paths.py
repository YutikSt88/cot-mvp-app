from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class ProjectPaths:
    root: Path

    @property
    def configs(self) -> Path: return self.root / "configs"
    @property
    def data(self) -> Path: return self.root / "data"
    @property
    def raw(self) -> Path: return self.data / "raw"
    @property
    def canonical(self) -> Path: return self.data / "canonical"
    @property
    def indicators(self) -> Path: return self.data / "indicators"
    @property
    def reports(self) -> Path: return self.root / "reports"