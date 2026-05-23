"""
Syndicate Enum / 集团枚举
包含星际战甲中所有集团的中文名称及 Warframe 字体图标。

Members count: 34
"""
from __future__ import annotations

from enum import Enum


class SyndicateEnum(Enum):
    """集团枚举 / Syndicate Enum"""

    # === 六大基础集团 / Six Core Syndicates ===
    ArbitersSyndicate = ("均衡仲裁者", "\ue500")
    CephalonSudaSyndicate = ("中枢苏达", "\ue501")
    NewLokaSyndicate = ("新世间", "\ue502")
    PerrinSyndicate = ("佩兰数列", "\ue505")
    SteelMeridianSyndicate = ("钢铁防线", "\ue504")
    RedVeilSyndicate = ("血色面纱", "\ue503")

    # === 开放世界集团 / Open World Syndicates ===
    CetusSyndicate = ("Ostron", "\ue508")
    QuillsSyndicate = ("夜羽", "\ue509")
    SolarisSyndicate = ("索拉里斯联盟", "\ue510")
    VoxSyndicate = ("索拉里斯之声", "\ue512")
    VentKidsSyndicate = ("通风小子", "\ue511")
    NightcapJournalSyndicate = ("夜帽", "\ue513")
    EntratiSyndicate = ("英择谛", "\ue514")
    EntratiLabSyndicate = ("科维兽", "\ue517")
    HexSyndicate = ("六人组", "\ue519")
    NecraloidSyndicate = ("殁世械灵", "\ue515")
    KahlSyndicate = ("卡尔驻军", "\ue518")
    ZarimanSyndicate = ("坚守者", "\ue516")

    # === 特殊集团 / Special Syndicates ===
    AssassinsSyndicate = ("刺客", "")
    EventSyndicate = ("集团", "\ue407")

    # === 午夜电波系列 / Nightwave Radio Legion ===
    RadioLegionSyndicate = ("土星六号之狼", "\ue520")
    RadioLegion2Syndicate = ("使徒", "\ue520")
    RadioLegion3Syndicate = ("玻璃匠", "\ue520")
    RadioLegionIntermissionSyndicate = ("Intermission", "\ue520")
    RadioLegionIntermission2Syndicate = ("Intermission II", "\ue520")
    RadioLegionIntermission3Syndicate = ("Intermission III", "\ue520")
    RadioLegionIntermission4Syndicate = ("Nora 的精选", "\ue520")
    RadioLegionIntermission5Syndicate = ("Nora 的混选 Vol. 1", "\ue520")
    RadioLegionIntermission6Syndicate = ("Nora 的混选 Vol. 2", "\ue520")
    RadioLegionIntermission7Syndicate = ("RadioLegionIntermission7Syndicate", "\ue520")
    RadioLegionIntermission8Syndicate = ("RadioLegionIntermission8Syndicate", "\ue520")
    RadioLegionIntermission9Syndicate = ("RadioLegionIntermission9Syndicate", "\ue520")
    RadioLegionIntermission10Syndicate = ("RadioLegionIntermission10Syndicate", "\ue520")
    RadioLegionIntermission11Syndicate = ("RadioLegionIntermission11Syndicate", "\ue520")
    RadioLegionIntermission12Syndicate = ("RadioLegionIntermission12Syndicate", "\ue520")
    RadioLegionIntermission13Syndicate = ("RadioLegionIntermission13Syndicate", "\ue520")

    def __init__(self, name: str, icon: str) -> None:
        self._display_name = name
        self._icon = icon

    @classmethod
    def _missing_(cls, value):
        """支持通过成员名称字符串匹配 Pydantic 验证 / Support name-based matching for Pydantic validation

        未知值回退到 EventSyndicate。
        """
        if isinstance(value, str):
            try:
                return cls[value]
            except KeyError:
                pass
        return cls.EventSyndicate

    @property
    def display_name(self) -> str:
        """集团显示名称"""
        return self._display_name

    @property
    def icon(self) -> str:
        """集团图标（Warframe 字体 Unicode 字符）"""
        return self._icon
