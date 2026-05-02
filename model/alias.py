"""
Alias Model / 别名模型
包含 Warframe 可交易物品的别名映射
"""
import re
from typing import Optional
from sqlmodel import SQLModel,Field

class Alias(SQLModel,table = True):
    """Warframe 物品的别名表"""
    
    __table_args__ = {'extend_existing': True}
    
    id: Optional[int] = Field(default=None,primary_key=True,description="自增主键")
    cn: str = Field(alias="cn",index=True,unique=True,description="别名名称")
    """别名名称"""
    en: str = Field(alias="en",index=True,description="原名称")
    """原名称/被映射的名称"""
    
    def is_valid_english(self) -> bool:
        """校验英文名称格式"""
        return bool(re.match(r"^([a-zA-Z]+)([ _&])?([0-9]+)?([a-zA-Z]+)?$", self.en))
    
    def is_valid_chinese(self) -> bool:
        """校验中文名称格式"""
        return bool(re.match(r"^[\u4e00-\u9fa5]+([ ·_&])?[\u4e00-\u9fa5]+$", self.cn))
    
    @property
    def equation(self) -> str:
        """序列化全部字段为 JSON 字符串"""
        return self.model_dump_json()