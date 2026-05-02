"""
Faction Enum / 派系枚举
包含星际战甲中所有派系的中英文名称、代表颜色及图标。
"""
from enum import Enum

class FactionEnum(Enum):
    """派系枚举"""
    FC_GRINEER = ("Grineer", "#870507", "\ue401")
    FC_CORPUS = ("Corpus", "#5AB0CB", "\ue402")
    FC_INFESTATION = ("Infested", "#61814B", "\ue403")
    FC_OROKIN = ("奥罗金", "#B6A019", "\ue404")
    FC_CORRUPTED = ("堕落者", "#B6A019", "\ue404")
    FC_SENTIENT = ("Sentient", "#931B1B", "\ue405")
    FC_NARMER = ("合一众", "#A35F27", "\ue409")
    FC_MURMUR = ("低语者", "#B59B6D", "\ue410")
    FC_SCALDRA = ("炽蛇军", "#DC8E12", "\ue411")
    FC_TECHROT = ("科腐者", "#17A36A", "\ue412")
    FC_DUVIRI = ("双衍王境", "#000000", "")
    FC_MITW = ("墙中人", "#000000", "")
    FC_TENNO = ("TENNO", "#000000", "\ue400")
    FC_CROSSFIRE = ("多方交战", "#591A9C", "\ue413")
    FC_NONE = ("未知派系", "#000000", "")
    
    def __init__(self, name: str, color: str, icon: str) -> None:
        self._display_name = name
        self._color = color
        self._icon = icon
        
    @property
    def display_name(self) -> str:
        """派系显示名称"""
        return self._display_name
    
    @property
    def color(self) -> str:
        """派系代表颜色（十六进制）"""
        return self._color
    
    @property
    def icon(self) -> str:
        """派系图标（Unicode 字符）"""
        return self._icon