"""
Mission Type Enum / 任务类型枚举

包含星际战甲中所有任务类型的中文名称、排序权重及代表颜色。
"""

from enum import Enum

class MissionTypeEnum(Enum):
    """任务类型枚举"""
    MT_ASSASSINATION = ("刺杀", 0, "#FF6B6B")
    MT_EXTERMINATION = ("歼灭", 1, "#FF9F43")
    MT_SURVIVAL = ("生存", 2, "#CDA241")
    MT_RESCUE = ("救援", 3, "#1DD1A1")
    MT_SABOTAGE = ("破坏", 4, "#54A0FF")
    MT_CAPTURE = ("捕获", 5, "#5F27CD")
    MT_DEFAULT = ("未知", 6, "#000000")
    MT_INTEL = ("间谍", 7, "#00D2D3")
    MT_DEFENSE = ("防御", 8, "#FF9FF3")
    MT_MOBILE_DEFENSE = ("移动防御", 9, "#75B1E6")
    MT_PVP = ("武形秘仪", 10, "#000000")
    MT_SECTOR = ("黑暗地带", 11, "#000000")
    MT_TERRITORY = ("拦截", 13, "#01A3A4")
    MT_RETRIEVAL = ("劫持", 14, "#8395A7")
    MT_HIVE = ("清巢", 15, "#FFEAA7")
    MT_EXCAVATE = ("挖掘", 17, "#DDA0DD")
    MT_SALVAGE = ("资源回收", 21, "#A29BFE")
    MT_ARENA = ("竞技场", 22, "#000000")
    MT_PURSUIT = ("追击", 24, "#000000")
    MT_ASSAULT = ("强袭", 26, "#FF7675")
    MT_EVACUATION = ("叛逃", 27, "#FDCB6E")
    MT_LANDSCAPE = ("自由漫步", 28, "#E17055")
    MT_DISRUPTION = ("中断", 32, "#E17055")
    MT_ARTIFACT = ("中断", 33, "#6C5CE7")
    MT_VOID_FLOOD = ("虚空洪流", 34, "#A29BFE")
    MT_VOID_CASCADE = ("虚空覆涌", 35, "#2D3436")
    MT_VOID_ARMAGEDDON = ("虚空决战", 36, "#00B894")
    MT_ALCHEMY = ("元素转换", 38, "#E84393")
    MT_CAMBIRE = ("异化区", 39, "#FD79A8")
    MT_LEGACYTE_HARVEST = ("传承种收割", 40, "#E67EE2")
    MT_SHRINE_DEFENSE = ("祈运坛防御", 41, "#E74C3C")
    MT_FACEOFF = ("对战", 42, "#F39C12")
    MT_SKIRMISH = ("前哨战", 60, "#9B59B6")
    MT_VOLATILE = ("爆发", 61, "#3498DB")
    MT_ORPHEUS = ("奧菲斯", 62, "#000000")
    MT_ASCENSION = ("扬升", 90, "#000000")
    MT_RELAY = ("中继站", 100, "#000000")
    
    def __init__(self, name: str, order: int, color: str) -> None:
        self._display_name = name
        self._order = order
        self._color = color
    
    @property
    def display_name(self) -> str:
        """任务类型显示名称"""
        return self._display_name

    @property
    def order(self) -> int:
        """排序权重"""
        return self._order
    
    @property
    def color(self) -> str:
        """任务类型代表颜色（十六进制字符串）"""
        return self._color
    
    @classmethod
    def ordered_values(cls) -> list["MissionTypeEnum"]:
        """按 order 排序返回所有枚举成员"""
        return sorted(cls, key=lambda m: m.order)