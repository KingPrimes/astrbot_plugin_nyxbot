"""表结构 ↔ API 模型 对齐测试（离线）。

守住一条底线：**API 文档里的字段，本地表必须有列**（或明确记录为「不落库」）。
以后改模型或改表，任何一边漏了，这里会立刻失败。
"""
from __future__ import annotations

import pytest

from src.model.ephemeras import Ephemeras
from src.model.lich_sister_weapons import LichSisterWeapons
from src.model.market.entities import Ephemera, Item, LichWeapon, RivenWeapon
from src.model.orders_items import OrdersItems
from src.model.riven_items import RivenItems
from src.model.riven_tion import RivenTion

# API 字段（alias）→ 表列名。i18n 的子字段用 "i18n.xxx" 表示。
ITEM_TO_TABLE = {
    "id": "id",
    "slug": "slug",
    "gameRef": "gameRef",
    "tags": "tags",
    "setRoot": "setRoot",
    "setParts": "setParts",
    "quantityInSet": "quantityInSet",
    "rarity": "rarity",
    "bulkTradable": "bulkTradable",
    "subtypes": "subtypes",
    "maxRank": "maxRank",
    "maxCharges": "maxCharges",
    "maxAmberStars": "maxAmberStars",
    "maxCyanStars": "maxCyanStars",
    "baseEndo": "baseEndo",
    "endoMultiplier": "endoMultiplier",
    "ducats": "ducats",
    "vosfor": "vosfor",
    "reqMasteryRank": "reqMasteryRank",
    "vaulted": "vaulted",
    "tradingTax": "tradingTax",
    "tradable": "tradable",
    "i18n.name": "name",
    "i18n.enName": "enName",
    "i18n.icon": "icon",
    "i18n.thumb": "thumb",
    "i18n.subIcon": "subIcon",
    "i18n.description": "description",
    "i18n.wikiLink": "wikiLink",
}

RIVEN_TO_TABLE = {
    "id": "id",
    "slug": "slug",
    "gameRef": "gameRef",
    "group": "group",
    "rivenType": "rivenType",
    "disposition": "disposition",
    "reqMasteryRank": "reqMasteryRank",
    "i18n.name": "name",
    "i18n.enName": "enName",
    "i18n.icon": "icon",
    "i18n.thumb": "thumb",
    "i18n.subIcon": "subIcon",
    "i18n.wikiLink": "wikiLink",
}

LICH_TO_TABLE = {
    "id": "id",
    "slug": "slug",
    "gameRef": "gameRef",
    "reqMasteryRank": "reqMasteryRank",
    "i18n.name": "name",
    "i18n.enName": "enName",
    "i18n.icon": "icon",
    "i18n.thumb": "thumb",
    "i18n.wikiLink": "wikiLink",
}

EPHEMERA_TO_TABLE = {
    "id": "id",
    "slug": "slug",
    "gameRef": "gameRef",
    "animation": "animation",
    "element": "element",
    "i18n.name": "name",
    "i18n.icon": "icon",
    "i18n.thumb": "thumb",
}


def model_aliases(model: type) -> set[str]:
    return {field.alias or name for name, field in model.model_fields.items()}


def table_columns(model: type) -> set[str]:
    return set(model._meta.fields_map)


def _check(entity_model, entity_fields: set[str], orm_model, mapping: dict[str, str]) -> None:
    # 1) 模型里的每个字段都有落点（i18n 是容器，按子字段映射，单独排除）
    unmapped = entity_fields - set(mapping) - {"i18n"}
    assert not unmapped, f"{entity_model.__name__} 有字段没映射到表: {sorted(unmapped)}"

    # 2) 映射的表列真实存在
    columns = table_columns(orm_model)
    missing_cols = {col for col in mapping.values() if col not in columns}
    assert not missing_cols, f"{orm_model.__name__} 缺列: {sorted(missing_cols)}"

    # 3) 表里没有多余的列（除了主键别名 ids）
    extra = columns - set(mapping.values()) - {"ids"}
    assert not extra, f"{orm_model.__name__} 有多余列（未对应 API）: {sorted(extra)}"


def test_item_table_matches_api() -> None:
    _check(Item, model_aliases(Item), OrdersItems, ITEM_TO_TABLE)


def test_riven_item_table_matches_api() -> None:
    _check(RivenWeapon, model_aliases(RivenWeapon), RivenItems, RIVEN_TO_TABLE)


def test_lich_weapon_table_matches_api() -> None:
    _check(LichWeapon, model_aliases(LichWeapon), LichSisterWeapons, LICH_TO_TABLE)


def test_ephemera_table_matches_api() -> None:
    _check(Ephemera, model_aliases(Ephemera), Ephemeras, EPHEMERA_TO_TABLE)


@pytest.mark.parametrize(
    "field", ["negative_only", "positive_is_negative", "search_only"]
)
def test_riven_attribute_bools(field: str) -> None:
    """文档里是 boolean，不能再用 FloatField。"""
    assert RivenTion._meta.fields_map[field].__class__.__name__ == "BooleanField"


def test_riven_attribute_unit_column() -> None:
    """API 字段叫 unit，表列也应叫 unit。"""
    columns = table_columns(RivenTion)
    assert "unit" in columns
    assert "units" not in columns
