from __future__ import annotations

from dataclasses import dataclass

from .cambion_cycle import CambionCycle
from .cetus_cycle import CetusCycle
from .earth_cycle import EarthCycle
from .vallis_cycle import VallisCycle
from .zariman_cycle import ZarimanCycle


@dataclass
class AllCycles:
    """聚合所有平原周期数据 / Aggregated cycle data for all open worlds."""

    earth: EarthCycle | None = None
    cetus: CetusCycle | None = None
    vallis: VallisCycle | None = None
    zariman: ZarimanCycle | None = None
    cambion: CambionCycle | None = None
