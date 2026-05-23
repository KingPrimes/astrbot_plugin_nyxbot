"""
NodeOverride Model / 节点覆盖模型

对应 Java: NodeOverride.java
继承 BastWorldState，但同时声明了自己的 activation 字段（覆盖父类字段）。
包含 node、hide、levelOverride、faction、customNpcEncounters、seed。
"""
from __future__ import annotations

from pydantic import Field

from .base import BastWorldState, DateField


class NodeOverride(BastWorldState):
    """节点覆盖 / Node Override

    对应 Java: NodeOverride extends BastWorldState
    注意：此模型有自己的 activation 字段，覆盖父类的 activation。
    """

    node: str | None = None
    hide: bool | None = None
    level_override: str | None = None
    # 覆盖父类 BastWorldState 的 activation 字段 / Override parent's activation field
    activation: DateField | None = None
    faction: str | None = None
    custom_npc_encounters: list[str] = Field(default_factory=list)
    seed: int | None = None
    enemy_spec: str | None = Field(default=None, alias="EnemySpec")
    extra_enemy_spec: str | None = Field(default=None, alias="ExtraEnemySpec")
