"""
Boss Enum / Boss 枚举
包含星际战甲中突击/执刑官猎杀任务涉及的所有 Boss 信息。

重构为 StrEnum：value 即为成员名称字符串（与 Java enum 行为一致）。
mode="json" 序列化输出 "SORTIE_BOSS_KELA" 而非 ["Kela De Thaym", "Grineer"]。
"""
from __future__ import annotations

from enum import StrEnum


class BossEnum(StrEnum):
    """Boss 枚举（用于突击/执刑官猎杀） — value = 成员名称字符串"""

    # === Grineer 派系 ===
    SORTIE_BOSS_KELA = ("SORTIE_BOSS_KELA", "Kela De Thaym", "Grineer")
    SORTIE_BOSS_VOR = ("SORTIE_BOSS_VOR", "Vor 上尉", "Grineer")
    SORTIE_BOSS_RUK = ("SORTIE_BOSS_RUK", "Sargas Ruk 将军", "Grineer")
    SORTIE_BOSS_HEK = ("SORTIE_BOSS_HEK", "Vay Hek 委员", "Grineer")
    SORTIE_BOSS_KRIL = ("SORTIE_BOSS_KRIL", "Lech Kril 中尉", "Grineer")
    SORTIE_BOSS_TYL = ("SORTIE_BOSS_TYL", "Tyl Regor", "Grineer")

    # === Corpus 派系 ===
    SORTIE_BOSS_HYENA = ("SORTIE_BOSS_HYENA", "鬣狗群", "Corpus")
    SORTIE_BOSS_JACKAL = ("SORTIE_BOSS_JACKAL", "豺狼", "Corpus")
    SORTIE_BOSS_ALAD = ("SORTIE_BOSS_ALAD", "Alad V", "Corpus")
    SORTIE_BOSS_AMBULAS = ("SORTIE_BOSS_AMBULAS", "Ambulas", "Corpus")
    SORTIE_BOSS_NEF = ("SORTIE_BOSS_NEF", "Nef Anyo", "Corpus")
    SORTIE_BOSS_RAPTOR = ("SORTIE_BOSS_RAPTOR", "猛禽", "Corpus")

    # === Infestation 派系 ===
    SORTIE_BOSS_PHORID = ("SORTIE_BOSS_PHORID", "Phorid", "Infestation")
    SORTIE_BOSS_LEPHANTIS = ("SORTIE_BOSS_LEPHANTIS", "Lephantis", "Infestation")
    SORTIE_BOSS_INFALAD = ("SORTIE_BOSS_INFALAD", "异融者 Alad V", "Infestation")

    # === 堕落者 / Corrupted ===
    SORTIE_BOSS_CORRUPTED_VOR = ("SORTIE_BOSS_CORRUPTED_VOR", "堕落 Vor", "堕落者")

    # === 合一众 / Narmer (执刑官猎杀) ===
    SORTIE_BOSS_BOREAL = ("SORTIE_BOSS_BOREAL", "诡文枭主", "合一众")
    SORTIE_BOSS_AMAR = ("SORTIE_BOSS_AMAR", "欺谋狼主", "合一众")
    SORTIE_BOSS_NIRA = ("SORTIE_BOSS_NIRA", "混沌蛇主", "合一众")
    SORTIE_BOSS_PAAZUL = ("SORTIE_BOSS_PAAZUL", "帕祖", "合一众")

    def __new__(cls, value: str, display_name: str, faction: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj._display_name = display_name # type: ignore
        obj._faction = faction # type: ignore
        return obj

    @property
    def display_name(self) -> str:
        """Boss 显示名称"""
        return self._display_name # type: ignore

    @property
    def faction(self) -> str:
        """Boss 所属派系"""
        return self._faction # type: ignore
