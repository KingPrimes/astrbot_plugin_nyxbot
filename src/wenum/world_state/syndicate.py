"""
Syndicate Enum / 集团枚举
包含星际战甲中所有集团的中文名称及 Warframe 字体图标。

Members count: 34
"""
from __future__ import annotations

from enum import StrEnum, unique


@unique
class SyndicateEnum(StrEnum):
    """集团枚举 / Syndicate Enum — value = 成员名称字符串"""

    # === 六大基础集团 / Six Core Syndicates ===
    ArbitersSyndicate = ("ArbitersSyndicate", "均衡仲裁者", "\ue500")
    CephalonSudaSyndicate = ("CephalonSudaSyndicate", "中枢苏达", "\ue501")
    NewLokaSyndicate = ("NewLokaSyndicate", "新世间", "\ue502")
    PerrinSyndicate = ("PerrinSyndicate", "佩兰数列", "\ue505")
    SteelMeridianSyndicate = ("SteelMeridianSyndicate", "钢铁防线", "\ue504")
    RedVeilSyndicate = ("RedVeilSyndicate", "血色面纱", "\ue503")

    # === 开放世界集团 / Open World Syndicates ===
    CetusSyndicate = ("CetusSyndicate", "Ostron", "\ue508")
    QuillsSyndicate = ("QuillsSyndicate", "夜羽", "\ue509")
    SolarisSyndicate = ("SolarisSyndicate", "索拉里斯联盟", "\ue510")
    VoxSyndicate = ("VoxSyndicate", "索拉里斯之声", "\ue512")
    VentKidsSyndicate = ("VentKidsSyndicate", "通风小子", "\ue511")
    NightcapJournalSyndicate = ("NightcapJournalSyndicate", "夜帽", "\ue513")
    EntratiSyndicate = ("EntratiSyndicate", "英择谛", "\ue514")
    EntratiLabSyndicate = ("EntratiLabSyndicate", "科维兽", "\ue517")
    HexSyndicate = ("HexSyndicate", "六人组", "\ue519")
    NecraloidSyndicate = ("NecraloidSyndicate", "殁世械灵", "\ue515")
    KahlSyndicate = ("KahlSyndicate", "卡尔驻军", "\ue518")
    ZarimanSyndicate = ("ZarimanSyndicate", "坚守者", "\ue516")

    # === 特殊集团 / Special Syndicates ===
    AssassinsSyndicate = ("AssassinsSyndicate", "刺客", "")
    EventSyndicate = ("EventSyndicate", "集团", "\ue407")

    # === 午夜电波系列 / Nightwave Radio Legion ===
    RadioLegionSyndicate = ("RadioLegionSyndicate", "土星六号之狼", "\ue520")
    RadioLegion2Syndicate = ("RadioLegion2Syndicate", "使徒", "\ue520")
    RadioLegion3Syndicate = ("RadioLegion3Syndicate", "玻璃匠", "\ue520")
    RadioLegionIntermissionSyndicate = ("RadioLegionIntermissionSyndicate", "Intermission", "\ue520")
    RadioLegionIntermission2Syndicate = ("RadioLegionIntermission2Syndicate", "Intermission II", "\ue520")
    RadioLegionIntermission3Syndicate = ("RadioLegionIntermission3Syndicate", "Intermission III", "\ue520")
    RadioLegionIntermission4Syndicate = ("RadioLegionIntermission4Syndicate", "Nora 的精选", "\ue520")
    RadioLegionIntermission5Syndicate = ("RadioLegionIntermission5Syndicate", "Nora 的混选 Vol. 1", "\ue520")
    RadioLegionIntermission6Syndicate = ("RadioLegionIntermission6Syndicate", "Nora 的混选 Vol. 2", "\ue520")
    RadioLegionIntermission7Syndicate = ("RadioLegionIntermission7Syndicate", "RadioLegionIntermission7Syndicate", "\ue520")
    RadioLegionIntermission8Syndicate = ("RadioLegionIntermission8Syndicate", "RadioLegionIntermission8Syndicate", "\ue520")
    RadioLegionIntermission9Syndicate = ("RadioLegionIntermission9Syndicate", "RadioLegionIntermission9Syndicate", "\ue520")
    RadioLegionIntermission10Syndicate = ("RadioLegionIntermission10Syndicate", "RadioLegionIntermission10Syndicate", "\ue520")
    RadioLegionIntermission11Syndicate = ("RadioLegionIntermission11Syndicate", "RadioLegionIntermission11Syndicate", "\ue520")
    RadioLegionIntermission12Syndicate = ("RadioLegionIntermission12Syndicate", "RadioLegionIntermission12Syndicate", "\ue520")
    RadioLegionIntermission13Syndicate = ("RadioLegionIntermission13Syndicate", "RadioLegionIntermission13Syndicate", "\ue520")

    def __new__(cls, value: str, display_name: str, icon: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj._display_name = display_name  # type: ignore
        obj._icon = icon  # type: ignore
        return obj

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
        return self._display_name  # type: ignore

    @property
    def icon(self) -> str:
        """集团图标（Warframe 字体 Unicode 字符）"""
        return self._icon  # type: ignore
