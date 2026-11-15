"""图标注册表 / Icon registry

图标字体 ``warframe_font_icon.ttf`` 的**唯一事实源**：每个图标一条记录，
把「码位 → 别名 → 语义色」绑定在一起，供渲染层按需查询。

设计约束
--------
1. **一条记录 = 一个码位**：码位在注册表内唯一；同一码位的不同叫法写成别名
   （例如 ``OROKIN`` 与 ``FC_CORRUPTED`` 共用 U+E404，堕落者只是别名）。
2. **别名全局唯一**：任何别名只能指向一条记录，避免 ``cold`` 既指元素又指图标。
3. **语义色合法**：``#RRGGBB`` 大写；无专属色时用 ``NEUTRAL_COLOR``，
   其含义是「由主题/上下文决定」，不是黑色。
4. **字号下限 24**：``ICON_SIZE_MIN = 24``，``16`` 被显式禁止（图标细节不可辨）。
5. **唯一入口**：渲染层所有图标使用处都必须通过 :data:`ICONS` 获取，
   禁止再写死 ``"\\ue401"`` 这类字形字面量；字号统一走 :func:`validate_icon_size`。

字段命名
--------
``key``        稳定主键，大写蛇形（``CEPHALON_SUDA``），增删条目时不变。
``codepoint``  Unicode 码位整数（``0xE401``），必须落在私有区 ``U+E000–U+F8FF``。
``aliases``    小写别名元组，覆盖枚举名、中英文展示名、字体字形名。
``color``      语义色 ``#RRGGBB``，用于「该图标的默认代表色」。
``group``      :class:`IconGroup` 分组，决定文档与列表中的组织顺序。
``name``       展示名（中文优先），仅用于展示与日志，不参与查询。

用法
----
::

    from src.render.icon_registry import ICONS, IconSize, icon_char

    ICONS.require("grineer")        # 按别名
    ICONS.by_codepoint(0xE401)       # 按码位
    ICONS.get("U+E401")              # 码位字符串
    ICONS.get("\\ue401")             # 字形字符
    ICONS.by_color("#870507")        # 按语义色（返回全部命中）
    ICONS.by_group(IconGroup.FACTION)

    icon_char("corrupted")           # → "\\ue404"

自检
----
本模块只保留业务逻辑；字体覆盖、唯一性等校验全部在
``tests/test_icon_registry.py``，执行 ``pytest tests/test_icon_registry.py``。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum, StrEnum
from types import MappingProxyType
from typing import Iterable, Iterator, Mapping

# --------------------------------------------------------------------------- 字体常量

#: 图标字体文件名（位于 ``src/render/fonts/``）。
ICON_FONT_FILENAME = "warframe_font_icon.ttf"

#: 每 em 单位数（规范化后固定 1024）。
FONT_UPEM = 1024

#: 墨迹外接方框边长（0.875 em，四边各留 64 单位）。
INK_BOX = 896

#: 墨迹中心在 em 方框中的坐标（基线为 y=0，字面上沿 960）。
INK_CENTER = (512, 448)

#: 图标字号下限；低于此值细节不可辨，禁止使用。
ICON_SIZE_MIN = 24

#: 明确禁止的字号（历史遗留，图标在此尺寸下无法辨认）。
ICON_SIZE_FORBIDDEN = frozenset({16})

#: 无专属语义色时的占位色，表示「由主题或上下文决定」。
NEUTRAL_COLOR = "#D0D0D0"


class IconSize(IntEnum):
    """允许的图标字号刻度（像素 = 每 em 像素数）。

    只保留三档，避免历史上 22/24/28/32/36/44/48 混用；新增档位必须是
    ``>= ICON_SIZE_MIN`` 且不与禁止值冲突。
    """

    SM = 24
    MD = 32
    LG = 48


class IconGroup(StrEnum):
    """图标分组，决定条目在源码与文档中的排列顺序。"""

    FACTION = "faction"
    ELEMENT = "element"
    POLARITY = "polarity"
    RESOURCE = "resource"
    SYNDICATE = "syndicate"


# --------------------------------------------------------------------------- 条目定义

_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_COLOR_RE = re.compile(r"^#[0-9A-F]{6}$")


@dataclass(frozen=True, slots=True)
class IconEntry:
    """一条图标记录（不可变）。

    Attributes:
        key: 稳定主键，大写蛇形，全局唯一。
        codepoint: Unicode 码位整数。
        aliases: 小写别名元组，不含 ``key`` 本身（查询时会自动补上 ``key.lower()``）。
        color: 语义色 ``#RRGGBB``；无专属色用 :data:`NEUTRAL_COLOR`。
        group: 所属分组。
        name: 展示名。
    """

    key: str
    codepoint: int
    aliases: tuple[str, ...]
    color: str
    group: IconGroup
    name: str

    @property
    def char(self) -> str:
        """字形字符（可直接交给 PIL 绘制）。"""
        return chr(self.codepoint)

    @property
    def glyph(self) -> str:
        """码位的常规写法，如 ``U+E401``。"""
        return f"U+{self.codepoint:04X}"


#: 注册表条目。按分组分段排列，段内按语义归类，便于人工查找与增补。
#: 字段顺序：key, codepoint, aliases, color, group, name
ENTRIES: tuple[IconEntry, ...] = (
    # ---------------------------------------------------------------- 派系 FACTION
    IconEntry("GRINEER", 0xE401, ("grineer", "fc_grineer"), "#870507", IconGroup.FACTION, "Grineer"),
    IconEntry("CORPUS", 0xE402, ("corpus", "fc_corpus"), "#5AB0CB", IconGroup.FACTION, "Corpus"),
    IconEntry("INFESTATION", 0xE403, ("infestation", "infested", "fc_infestation"), "#61814B", IconGroup.FACTION, "Infested"),
    IconEntry("OROKIN", 0xE404, ("orokin", "fc_orokin", "corrupted", "fc_corrupted", "奥罗金", "堕落者"), "#B6A019", IconGroup.FACTION, "奥罗金 / 堕落者"),
    IconEntry("SENTIENT", 0xE405, ("sentient", "fc_sentient"), "#931B1B", IconGroup.FACTION, "Sentient"),
    IconEntry("NARMER", 0xE409, ("narmer", "fc_narmer", "合一众"), "#A35F27", IconGroup.FACTION, "合一众"),
    IconEntry("MURMUR", 0xE410, ("murmur", "the murmur", "fc_murmur", "低语者"), "#B59B6D", IconGroup.FACTION, "低语者"),
    IconEntry("SCALDRA", 0xE411, ("scaldra", "fc_scaldra", "炽蛇军"), "#DC8E12", IconGroup.FACTION, "炽蛇军"),
    IconEntry("TECHROT", 0xE412, ("techrot", "fc_techrot", "科腐者"), "#17A36A", IconGroup.FACTION, "科腐者"),
    IconEntry("TENNO", 0xE400, ("tenno", "fc_tenno"), NEUTRAL_COLOR, IconGroup.FACTION, "TENNO"),
    IconEntry("CROSSFIRE", 0xE413, ("crossfire", "fc_crossfire", "多方交战"), "#591A9C", IconGroup.FACTION, "多方交战"),

    # ---------------------------------------------------------------- 元素 ELEMENT
    IconEntry("ELECTRICITY", 0xE601, ("electricity", "电击"), "#955AB9", IconGroup.ELEMENT, "电击"),
    IconEntry("IMPACT", 0xE602, ("impact", "冲击"), "#929595", IconGroup.ELEMENT, "冲击"),
    IconEntry("RADIATION", 0xE603, ("radiation", "辐射"), "#9E940C", IconGroup.ELEMENT, "辐射"),
    IconEntry("MAGNETIC", 0xE604, ("magnetic", "磁力"), "#50575E", IconGroup.ELEMENT, "磁力"),
    IconEntry("COLD", 0xE605, ("cold", "冰冻"), "#2C53B5", IconGroup.ELEMENT, "冰冻"),
    IconEntry("TOXIN", 0xE606, ("toxin", "毒素"), "#4F822F", IconGroup.ELEMENT, "毒素"),
    IconEntry("HEAT", 0xE607, ("heat", "火焰"), "#E56E0C", IconGroup.ELEMENT, "火焰"),
    IconEntry("PUNCTURE", 0xE608, ("puncture", "穿刺"), "#8D8676", IconGroup.ELEMENT, "穿刺"),
    IconEntry("SLASH", 0xE609, ("slash", "切割"), "#876769", IconGroup.ELEMENT, "切割"),
    IconEntry("BLAST", 0xE610, ("blast", "爆炸"), "#A86668", IconGroup.ELEMENT, "爆炸"),
    IconEntry("CORROSIVE", 0xE611, ("corrosive", "腐蚀"), "#B2CA01", IconGroup.ELEMENT, "腐蚀"),
    IconEntry("GAS", 0xE612, ("gas", "毒气"), "#3AC490", IconGroup.ELEMENT, "毒气"),
    IconEntry("VIRAL", 0xE613, ("viral", "病毒"), "#E374B6", IconGroup.ELEMENT, "病毒"),
    IconEntry("VOID", 0xE614, ("void", "虚空"), "#016468", IconGroup.ELEMENT, "虚空"),
    IconEntry("TAU", 0xE615, ("tau",), "#DF191E", IconGroup.ELEMENT, "Tau"),
    IconEntry("TRUE", 0xE616, ("true",), "#66582E", IconGroup.ELEMENT, "真实"),

    # ---------------------------------------------------------------- 极性 POLARITY
    IconEntry("MADURAI", 0xE200, ("madurai", "madurai.1"), NEUTRAL_COLOR, IconGroup.POLARITY, "Madurai"),
    IconEntry("VAZARIN", 0xE202, ("vazarin", "vazarin.1"), NEUTRAL_COLOR, IconGroup.POLARITY, "Vazarin"),
    IconEntry("NARAMON", 0xE203, ("naramon", "naramon.1"), NEUTRAL_COLOR, IconGroup.POLARITY, "Naramon"),
    IconEntry("ZENURIK", 0xE204, ("zenurik", "zenurik.1"), NEUTRAL_COLOR, IconGroup.POLARITY, "Zenurik"),
    IconEntry("UNAIRU", 0xE205, ("unairu", "unairu.1"), NEUTRAL_COLOR, IconGroup.POLARITY, "Unairu"),
    IconEntry("PENJAGA", 0xE206, ("penjaga",), NEUTRAL_COLOR, IconGroup.POLARITY, "Penjaga"),
    IconEntry("UMBRA", 0xE207, ("umbra",), NEUTRAL_COLOR, IconGroup.POLARITY, "Umbra"),
    IconEntry("ANY", 0xE208, ("any",), NEUTRAL_COLOR, IconGroup.POLARITY, "Any"),

    # ---------------------------------------------------------------- 资源/通用 RESOURCE
    IconEntry("CREDITS", 0xE306, ("credits",), NEUTRAL_COLOR, IconGroup.RESOURCE, "Credits"),
    IconEntry("DUCATS", 0xE305, ("ducats",), NEUTRAL_COLOR, IconGroup.RESOURCE, "Ducats"),
    IconEntry("PLATINUM", 0xE309, ("platinum", "platinum.1"), NEUTRAL_COLOR, IconGroup.RESOURCE, "Platinum"),
    IconEntry("AYA", 0xE308, ("aya", "ayan"), NEUTRAL_COLOR, IconGroup.RESOURCE, "Aya"),
    IconEntry("CUBES", 0xE304, ("cubes",), NEUTRAL_COLOR, IconGroup.RESOURCE, "Cubes"),
    IconEntry("REFRESH", 0xE310, ("refresh",), NEUTRAL_COLOR, IconGroup.RESOURCE, "Refresh"),
    IconEntry("SMILE", 0xE300, ("smile",), NEUTRAL_COLOR, IconGroup.RESOURCE, "Smile"),
    IconEntry("MEH", 0xE302, ("meh",), NEUTRAL_COLOR, IconGroup.RESOURCE, "Meh"),
    IconEntry("SUN", 0xE101, ("sun",), NEUTRAL_COLOR, IconGroup.RESOURCE, "Sun"),
    IconEntry("NIGHT", 0xE102, ("night",), NEUTRAL_COLOR, IconGroup.RESOURCE, "Night"),

    # ---------------------------------------------------------------- 集团 SYNDICATE
    IconEntry("ARBITERS", 0xE500, ("arbiters", "arbiters of hexis", "arbiterssyndicate", "均衡仲裁者"), NEUTRAL_COLOR, IconGroup.SYNDICATE, "均衡仲裁者"),
    IconEntry("CEPHALON_SUDA", 0xE501, ("cephalon_suda", "cephalon suda", "cephalonsudasyndicate", "中枢苏达"), NEUTRAL_COLOR, IconGroup.SYNDICATE, "中枢苏达"),
    IconEntry("NEW_LOKA", 0xE502, ("new_loka", "new loka", "newlokasyndicate", "新世间"), NEUTRAL_COLOR, IconGroup.SYNDICATE, "新世间"),
    IconEntry("RED_VEIL", 0xE503, ("red_veil", "red veil", "redveilsyndicate", "血色面纱"), NEUTRAL_COLOR, IconGroup.SYNDICATE, "血色面纱"),
    IconEntry("STEEL_MERIDIAN", 0xE504, ("steel_meridian", "steel meridian", "steelmeridiansyndicate", "钢铁防线"), NEUTRAL_COLOR, IconGroup.SYNDICATE, "钢铁防线"),
    IconEntry("PERRIN_SEQUENCE", 0xE505, ("perrin_sequence", "the perrin sequence", "perrinsyndicate", "佩兰数列"), NEUTRAL_COLOR, IconGroup.SYNDICATE, "佩兰数列"),
    IconEntry("SYNDICATE_EVENT", 0xE407, ("syndicate_event", "syndicates", "eventsyndicate", "集团事件", "集团"), NEUTRAL_COLOR, IconGroup.SYNDICATE, "集团事件"),
    IconEntry("OSTRON", 0xE508, ("ostron", "cetus", "cetussyndicate"), NEUTRAL_COLOR, IconGroup.SYNDICATE, "Ostron"),
    IconEntry("QUILLS", 0xE509, ("quills", "the quills", "quillssyndicate", "夜羽"), NEUTRAL_COLOR, IconGroup.SYNDICATE, "夜羽"),
    IconEntry("SOLARIS_UNITED", 0xE510, ("solaris_united", "solaris united", "solarissyndicate", "索拉里斯联盟"), NEUTRAL_COLOR, IconGroup.SYNDICATE, "索拉里斯联盟"),
    IconEntry("VOX_SOLARIS", 0xE512, ("vox_solaris", "vox solaris", "voxsyndicate", "索拉里斯之声"), NEUTRAL_COLOR, IconGroup.SYNDICATE, "索拉里斯之声"),
    IconEntry("VENTKIDS", 0xE511, ("ventkids", "ventkidssyndicate", "通风小子"), NEUTRAL_COLOR, IconGroup.SYNDICATE, "通风小子"),
    IconEntry("NIGHTCAP", 0xE513, ("nightcap", "nightcapjournalsyndicate", "夜帽"), NEUTRAL_COLOR, IconGroup.SYNDICATE, "夜帽"),
    IconEntry("ENTRATI", 0xE514, ("entrati", "entratisyndicate", "英择谛"), NEUTRAL_COLOR, IconGroup.SYNDICATE, "英择谛"),
    IconEntry("ENTRATI_LAB", 0xE517, ("entrati_lab", "entratilabsyndicate", "cavia", "科维兽"), NEUTRAL_COLOR, IconGroup.SYNDICATE, "科维兽"),
    IconEntry("NECRALOID", 0xE515, ("necraloid", "necraloidsyndicate", "殁世械灵"), NEUTRAL_COLOR, IconGroup.SYNDICATE, "殁世械灵"),
    IconEntry("ZARIMAN", 0xE516, ("zariman", "zarimansyndicate", "the holdfasts", "坚守者"), NEUTRAL_COLOR, IconGroup.SYNDICATE, "坚守者"),
    IconEntry("KAHL", 0xE518, ("kahl", "kahlsyndicate", "kahl's garrison", "卡尔驻军"), NEUTRAL_COLOR, IconGroup.SYNDICATE, "卡尔驻军"),
    IconEntry("HEX", 0xE519, ("hex", "hexsyndicate", "the hex", "六人组"), NEUTRAL_COLOR, IconGroup.SYNDICATE, "六人组"),
    IconEntry("NIGHTWAVE", 0xE520, ("nightwave", "radiolegion", "nora", "午夜电波", "土星六号之狼"), NEUTRAL_COLOR, IconGroup.SYNDICATE, "午夜电波"),
)


# --------------------------------------------------------------------------- 注册表


class IconNotFound(LookupError):
    """按 token 找不到图标时抛出。"""


class IconRegistry:
    """不可变图标注册表，构建时校验唯一性并建立 O(1) 索引。

    索引均为只读视图：

    - ``by_key`` / ``by_alias``：``str → IconEntry``
    - ``by_codepoint``：``int → IconEntry``
    - ``by_char`` / ``by_glyph``：字形字符、``U+XXXX`` 字符串 → ``IconEntry``
    - ``by_color`` / ``by_group``：``str → tuple[IconEntry, ...]``（一对多）
    """

    def __init__(self, entries: Iterable[IconEntry]) -> None:
        items = tuple(entries)
        by_key: dict[str, IconEntry] = {}
        by_codepoint: dict[int, IconEntry] = {}
        by_alias: dict[str, IconEntry] = {}
        by_char: dict[str, IconEntry] = {}
        by_glyph: dict[str, IconEntry] = {}
        by_color: dict[str, list[IconEntry]] = {}
        by_group: dict[str, list[IconEntry]] = {}

        for entry in items:
            self._validate_entry(entry)
            if entry.key in by_key:
                raise ValueError(f"key 重复: {entry.key}")
            if entry.codepoint in by_codepoint:
                raise ValueError(
                    f"码位重复: {entry.glyph} 同时被 {by_codepoint[entry.codepoint].key} 与 {entry.key} 使用"
                )
            by_key[entry.key] = entry
            by_codepoint[entry.codepoint] = entry
            by_char[entry.char] = entry
            by_glyph[entry.glyph] = entry
            by_color.setdefault(entry.color, []).append(entry)
            by_group.setdefault(entry.group, []).append(entry)

            for alias in (entry.key.lower(), *entry.aliases):
                normalized = alias.strip().lower()
                if not normalized:
                    raise ValueError(f"{entry.key}: 别名不能为空")
                if normalized in by_alias and by_alias[normalized] is not entry:
                    raise ValueError(f"别名冲突: {normalized!r} 同时属于 {by_alias[normalized].key} 与 {entry.key}")
                by_alias[normalized] = entry

        self._entries = items
        self._by_key = MappingProxyType(by_key)
        self._by_codepoint = MappingProxyType(by_codepoint)
        self._by_alias = MappingProxyType(by_alias)
        self._by_char = MappingProxyType(by_char)
        self._by_glyph = MappingProxyType(by_glyph)
        self._by_color = MappingProxyType({k: tuple(v) for k, v in by_color.items()})
        self._by_group = MappingProxyType({k: tuple(v) for k, v in by_group.items()})

    @staticmethod
    def _validate_entry(entry: IconEntry) -> None:
        if not _KEY_RE.match(entry.key):
            raise ValueError(f"key 必须是大写蛇形: {entry.key!r}")
        if not 0xE000 <= entry.codepoint <= 0xF8FF:
            raise ValueError(f"{entry.key}: 码位 {entry.glyph} 不在私有区 U+E000–U+F8FF")
        if entry.color != entry.color.upper() or not _COLOR_RE.match(entry.color):
            raise ValueError(f"{entry.key}: 语义色必须是 #RRGGBB 大写，当前 {entry.color!r}")
        if not isinstance(entry.group, IconGroup):
            raise ValueError(f"{entry.key}: group 必须是 IconGroup，当前 {entry.group!r}")

    # ------------------------------------------------------------ 只读索引

    @property
    def entries(self) -> tuple[IconEntry, ...]:
        return self._entries

    @property
    def by_key(self) -> Mapping[str, IconEntry]:
        return self._by_key

    @property
    def by_alias(self) -> Mapping[str, IconEntry]:
        return self._by_alias

    @property
    def by_codepoint(self) -> Mapping[int, IconEntry]:
        return self._by_codepoint

    @property
    def by_color(self) -> Mapping[str, tuple[IconEntry, ...]]:
        return self._by_color

    @property
    def by_group(self) -> Mapping[str, tuple[IconEntry, ...]]:
        return self._by_group

    # ------------------------------------------------------------ 查询

    def get(self, token: str | int) -> IconEntry | None:
        """按主键 / 别名 / 码位 / 字形字符查询，找不到返回 ``None``。

        码位串非法（如 ``U+ZZZZ`` / ``0xZZ``）同样返回 ``None`` 而不是抛
        ``ValueError``（审查 P2-11：与文档串保持一致；需要强校验用
        :meth:`require`）。
        """
        if isinstance(token, int):
            return self._by_codepoint.get(token)

        raw = token.strip()
        if not raw:
            return None
        lowered = raw.lower()
        if lowered.startswith(("u+", "0x")):
            try:
                codepoint = int(lowered[2:] if lowered.startswith("u+") else lowered, 16)
            except ValueError:
                return None
            return self._by_codepoint.get(codepoint)
        if len(raw) == 1 and ord(raw) >= 0xE000:
            return self._by_codepoint.get(ord(raw))
        return self._by_alias.get(lowered) or self._by_key.get(raw)

    def require(self, token: str | int) -> IconEntry:
        """同 :meth:`get`，但找不到时抛 :class:`IconNotFound`。"""
        entry = self.get(token)
        if entry is None:
            raise IconNotFound(f"未注册的图标: {token!r}")
        return entry

    def by_codepoint_of(self, codepoint: int) -> IconEntry | None:
        """按码位整数查询（``by_codepoint`` 映射的显式方法形式）。"""
        return self._by_codepoint.get(codepoint)

    def entries_of_color(self, color: str) -> tuple[IconEntry, ...]:
        """按语义色查询，返回该色全部条目（可能为空）。"""
        return self._by_color.get(color.strip().upper(), ())

    def entries_of_group(self, group: IconGroup | str) -> tuple[IconEntry, ...]:
        """按分组查询，保持声明顺序。"""
        key = group.value if isinstance(group, IconGroup) else str(group)
        return self._by_group.get(key, ())

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[IconEntry]:
        return iter(self._entries)

    def __contains__(self, token: object) -> bool:
        return isinstance(token, (str, int)) and self.get(token) is not None

    # ------------------------------------------------------------ 校验

    def stats(self) -> dict[str, int]:
        """按分组的条目数统计。"""
        return {group.value: len(self._by_group.get(group.value, ())) for group in IconGroup}


def validate_icon_size(size: int) -> int:
    """校验图标字号是否符合规范，返回原值；违规抛 ``ValueError``。"""
    if size in ICON_SIZE_FORBIDDEN:
        raise ValueError(f"图标字号 {size} 已被禁用：该尺寸下图标细节不可辨，请使用 >= {ICON_SIZE_MIN}")
    if size < ICON_SIZE_MIN:
        raise ValueError(f"图标字号 {size} 小于下限 {ICON_SIZE_MIN}，请使用 >= {ICON_SIZE_MIN}")
    return size


#: 全局注册表实例。渲染层统一通过它取图标，禁止再写死码位。
ICONS = IconRegistry(ENTRIES)


def icon_char(token: str | int) -> str:
    """快捷方法：token → 字形字符。"""
    return ICONS.require(token).char


def icon_entry(token: str | int) -> IconEntry:
    """快捷方法：token → 条目。"""
    return ICONS.require(token)
