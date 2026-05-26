"""State Type Enum / 状态类型枚举"""
from __future__ import annotations

from enum import StrEnum, unique


@unique
class StateTypeEnum(StrEnum):
    """Warframe 物品状态类型枚举 — value = 成员名称字符串

    每个成员的 key 为 Lotus 路径正则（空字符串表示无正则，仅作为回退类型）。
    """

    ALL = ("ALL", "", "未知")
    GEAR = ("GEAR", "", "道具")
    KEYS = ("KEYS", "", "钥匙")
    RESOURCES = ("RESOURCES", "", "资源")
    SENTINELS = ("SENTINELS", "", "守护/宠物")
    OTHER = ("OTHER", "", "加成")
    MODS = ("MODS", "", "MOD")
    WARFRAMES = ("WARFRAMES", "", "战甲")
    WEAPONS = ("WEAPONS", "", "武器")
    RELIC_BRONZE = ("RELIC_BRONZE", "/Lotus/Types/Game/Projections/.*?(Bronze)$", "完整遗物")
    RELIC_PLATINUM = ("RELIC_PLATINUM", "/Lotus/Types/Game/Projections/.*?(Platinum)$", "光辉遗物")
    RELIC_GOLD = ("RELIC_GOLD", "/Lotus/Types/Game/Projections/.*?(Gold)$", "无暇遗物")
    RELIC_SILVER = ("RELIC_SILVER", "/Lotus/Types/Game/Projections/.*?(Silver)$", "优良遗物")
    ENHANCERS = ("ENHANCERS", "/Lotus/Upgrades/CosmeticEnhancers/.*", "赋能")
    SKINS = ("SKINS", "/Lotus/Upgrades/Skins/.*", "外观")
    SHIP = ("SHIP", "/Lotus/Types/Ship/.*", "采集机")
    TENNO_ACCESSORY_SCARVES = ("TENNO_ACCESSORY_SCARVES", "/Lotus/Characters/Tenno/Accessory/Scarves/.*", "披饰")
    WEAPONS_TENNO_MELEE_SKIN = ("WEAPONS_TENNO_MELEE_SKIN", "/Lotus/Weapons/Tenno/Melee/.*Skin", "武器外观")
    KUBROW_PET_PATTERNS = ("KUBROW_PET_PATTERNS", "/Lotus/Types/Game/KubrowPet/Patterns/.*", "库狛花纹")
    CATBROW_PET_PATTERNS = ("CATBROW_PET_PATTERNS", "/Lotus/Types/Game/CatbrowPet/Patterns/.*", "库娃花纹")
    INFESTED_KAVAT_PET_PATTERNS = ("INFESTED_KAVAT_PET_PATTERNS", "/Lotus/Types/Game/InfestedKavatPet/Patterns/.*", "狐帕菲拉花纹")
    INFESTED_PREDATORS_PET_PATTERNS = ("INFESTED_PREDATORS_PET_PATTERNS", "/Lotus/Types/Game/InfestedPredatorPet/Patterns/.*", "扑猎达赛花纹")
    BACKGROUNDS = ("BACKGROUNDS", "/Lotus/Interface/Graphics/CustomUI/Backgrounds/.*", "背景")
    CURSORS = ("CURSORS", "/Lotus/Interface/Graphics/CustomUI/Cursors/.*", "指针")
    SOUNDS = ("SOUNDS", "/Lotus/Interface/Graphics/CustomUI/Sounds/.*", "登录音效")
    CUSTOM_UI_STYLE = ("CUSTOM_UI_STYLE", "/Lotus/Interface/Graphics/CustomUI/.*Style", "主题")
    ACTION_FIGURE_DIORAMAS = ("ACTION_FIGURE_DIORAMAS", "/Lotus/Types/Game/ActionFigureDioramas/.*", "景观")
    COLORS = ("COLORS", "/Lotus/Types/Game/(.*)/?Colors/.*", "颜色")
    NOTE_PACKS = ("NOTE_PACKS", "/Lotus/Types/Game/NotePacks/.*", "乐器")
    POSE_SETS = ("POSE_SETS", "/Lotus/Types/Game/PoseSets/.*", "姿势组")
    QUARTERS_WALLPAPERS = ("QUARTERS_WALLPAPERS", "/Lotus/Types/Game/QuartersWallpapers/.*", "壁纸模板")
    ARCADE = ("ARCADE", "/Lotus/Types/Items/Arcade/.*", "街机")
    EMOTES = ("EMOTES", "/Lotus/Types/Items/Emotes/.*", "表情")
    VIDEO_WALL_BACKDROPS = ("VIDEO_WALL_BACKDROPS", "/Lotus/Types/Items/VideoWallBackdrops/.*", "视频墙背景")
    VIDEO_WALL_SOUNDSCAPES = ("VIDEO_WALL_SOUNDSCAPES", "/Lotus/Types/Items/VideoWallSoundscapes/.*", "视频墙音景")
    AVATAR_IMAGES = ("AVATAR_IMAGES", "/Lotus/Types/StoreItems/AvatarImages/.*", "浮印")
    SUIT_CUSTOMIZATIONS = ("SUIT_CUSTOMIZATIONS", "/Lotus/Types/StoreItems/SuitCustomizations/.*", "颜色包")
    PACKAGES = ("PACKAGES", "/Lotus/Types/StoreItems/Packages/.*", "组合包")
    SHIP_SCENES = ("SHIP_SCENES", "/Lotus/Types/StoreItems/ShipScenes/.*", "轨道飞行器装饰")
    BLUEPRINT = ("BLUEPRINT", "/Lotus/.*Blueprint", "蓝图")

    def __new__(cls, value: str, key: str, label: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj._key = key  # type: ignore
        obj._label = label  # type: ignore
        return obj

    @property
    def key(self) -> str:
        """Lotus 路径正则"""
        return self._key  # type: ignore

    @property
    def label(self) -> str:
        """显示名称（如\"完整遗物\"），不覆盖 Enum 内置的 .name 成员名"""
        return self._label  # type: ignore
