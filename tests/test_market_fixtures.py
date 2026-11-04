"""市场 API 快照回归测试。

数据来源：2026-11-04 从 ``api.warframe.market`` 抓取的真实响应，抽样后放在
``tests/fixtures/market/``。**测试全程不联网**（见 ``conftest.py``）。

这组测试的目的不是验证业务逻辑，而是守住两条底线：

1. 官网返回的字段，我们的模型一个都不能少（防止字段被静默丢弃）；
2. 快照能被模型正常解析（防止改模型时把老数据解析坏）。
"""
from __future__ import annotations

import json
import pathlib

import pytest

from src.model.market.market_lich_sister import LichSisterAuction
from src.model.market.market_orders import MarketUser, OrderWithUser
from src.model.market.market_riven import RivenAuction
from src.util.i18n_utils import extract_i18n

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "market"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def aliases(model: type) -> set[str]:
    """模型接受的字段名（优先取 alias）。"""
    return {field.alias or name for name, field in model.model_fields.items()}


# ---------------------------------------------------------------- 物品 /items


def test_items_fixture_keeps_all_field_shapes() -> None:
    """快照要覆盖 API 返回的所有字段组合，否则抽样抽漏了。"""
    data = load("items.json")["data"]
    shapes = {frozenset(item) for item in data}
    assert len(shapes) >= 10, f"字段组合只有 {len(shapes)} 种，抽样可能失效"

    union = set().union(*shapes)
    assert {"id", "slug", "gameRef", "tags", "i18n"} <= union
    assert {"ducats", "vaulted", "maxRank", "subtypes", "endoMultiplier"} <= union


def test_items_i18n_has_both_languages() -> None:
    """插件请求头带 language: zh-hans，响应应同时含 en 与 zh-hans。"""
    data = load("items.json")["data"]
    langs = {lang for item in data for lang in (item.get("i18n") or {})}
    assert {"en", "zh-hans"} <= langs


def test_extract_i18n_returns_chinese() -> None:
    """extract_i18n 默认取 zh-hans 的 name/icon/thumb。"""
    data = load("items.json")["data"]
    item = next(i for i in data if i["slug"] == "secura_dual_cestra")
    out = extract_i18n(item)
    assert out["name"] == "保障·锡斯特双枪"
    assert out["icon"].endswith(".png") or out["icon"].endswith(".webp")
    assert out["thumb"]


# ---------------------------------------------------------------- 订单 /orders


def test_order_model_covers_api_fields() -> None:
    data = load("orders_frost_prime_set.json")["data"]
    order_keys = set().union(*(set(o) for o in data))
    user_keys = set().union(*(set(o.get("user") or {}) for o in data))

    missing_order = order_keys - aliases(OrderWithUser)
    missing_user = user_keys - aliases(MarketUser)
    assert not missing_order, f"OrderWithUser 缺字段: {sorted(missing_order)}"
    assert not missing_user, f"MarketUser 缺字段: {sorted(missing_user)}"


def test_orders_parse() -> None:
    data = load("orders_frost_prime_set.json")["data"]
    parsed = [OrderWithUser.model_validate(o) for o in data]
    assert parsed
    for order in parsed:
        assert order.type in {"buy", "sell"}
        assert order.platinum is not None
        assert order.user is not None
        assert order.user.ingame_name


# ---------------------------------------------------------------- 拍卖 /auctions


def test_riven_auction_model_covers_api_fields() -> None:
    auctions = load("auctions_riven_nagantaka.json")["payload"]["auctions"]
    keys = set().union(*(set(a) for a in auctions))
    assert not keys - aliases(RivenAuction), f"缺字段: {sorted(keys - aliases(RivenAuction))}"


def test_lich_auction_model_covers_api_fields() -> None:
    auctions = load("auctions_lich_kuva_bramma.json")["payload"]["auctions"]
    keys = set().union(*(set(a) for a in auctions))
    missing = keys - aliases(LichSisterAuction)
    assert not missing, f"缺字段: {sorted(missing)}"


def test_riven_auction_parse() -> None:
    auctions = load("auctions_riven_nagantaka.json")["payload"]["auctions"]
    parsed = [RivenAuction.model_validate(a) for a in auctions]
    assert parsed
    for auction in parsed:
        assert auction.item is not None
        assert auction.item.name
        assert auction.item.weapon_url_name
        assert auction.item.attributes
        assert auction.owner is not None
        assert auction.owner.ingame_name
        assert auction.owner.locale


def test_lich_auction_parse() -> None:
    auctions = load("auctions_lich_kuva_bramma.json")["payload"]["auctions"]
    parsed = [LichSisterAuction.model_validate(a) for a in auctions]
    assert parsed
    for auction in parsed:
        assert auction.item is not None
        assert auction.item.element
        assert isinstance(auction.item.damage, int)
        assert auction.owner is not None
        assert auction.owner.ingame_name


# ---------------------------------------------------------------- 物品详情 /item/{slug}/set


def test_item_set_has_localized_names() -> None:
    payload = load("item_set_frost_prime_set.json")
    items = payload["data"]["items"]
    assert items
    item = next(i for i in items if i["slug"] == "frost_prime_set")
    i18n = item["i18n"]
    assert i18n["en"]["name"] == "Frost Prime Set"
    assert i18n["zh-hans"]["name"] == "Frost Prime 一套"
    assert item["reqMasteryRank"] is not None or item["tradingTax"] is not None


# ---------------------------------------------------------------- 语言分布


@pytest.mark.parametrize("fixture", ["auctions_riven_nagantaka.json", "auctions_lich_kuva_bramma.json"])
def test_auctions_cover_multiple_locales(fixture: str) -> None:
    """私聊语句要按卖家 locale 选语言，快照必须覆盖多种 locale。"""
    auctions = load(fixture)["payload"]["auctions"]
    locales = {(a.get("owner") or {}).get("locale") for a in auctions}
    assert len(locales) >= 3, f"{fixture} 只有 {len(locales)} 种 locale，样本不够"


# ---------------------------------------------------------------- 离线保证


def test_network_is_blocked() -> None:
    """确认 conftest 的断网守卫生效，避免以后误加联网测试。"""
    import socket

    with pytest.raises(RuntimeError, match="测试禁止访问网络"):
        socket.create_connection(("api.warframe.market", 443), timeout=1)
