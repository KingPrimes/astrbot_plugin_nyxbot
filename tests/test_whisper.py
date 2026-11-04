"""私聊语句生成与 /w 指令测试（离线）。

断言直接对应用户从 warframe.market 网页复制的两条真实样例。
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.model.market.market_orders import (
    OrderWithUser,
    TransactionEnum,
)
from src.model.market.market_riven import RivenAuction
from src.model.market.market_lich_sister import LichSisterAuction
from src.service import whisper as whisper_service
from src.service.whisper import (
    lich_whisper,
    order_whisper,
    pick_lang,
    riven_whisper,
)


def make_order(**kwargs) -> OrderWithUser:
    payload = {
        "id": "x",
        "type": "sell",
        "platinum": 20,
        "quantity": 1,
        "rank": None,
        "user": {
            "id": "u",
            "ingameName": "zyx6687",
            "locale": "zh-hans",
            "status": "online",
        },
    }
    payload.update(kwargs)
    return OrderWithUser.model_validate(payload)


# ---------------------------------------------------------------- 订单


def test_order_whisper_zh_matches_site_sample() -> None:
    """用户提供的真实样例（中文，买）。"""
    order = make_order(platinum=20, rank=5)
    entry = order_whisper(order, "主要·死首", "Primary Deadhead")
    assert entry is not None
    assert entry.lang == "zh"
    assert entry.text == (
        '/w zyx6687 你好! 我想以20白金购买: "主要·死首 (等级 5)"。(warframe.market)'
    )


def test_order_whisper_en_matches_site_sample() -> None:
    """用户提供的真实样例（英文，买，带数量与等级）。"""
    order = make_order(
        platinum=6,
        quantity=6,
        rank=0,
        user={"id": "u", "ingameName": "W0lfieAGR", "locale": "en", "status": "ingame"},
    )
    entry = order_whisper(order, "主要·死首", "Primary Deadhead")
    assert entry is not None
    assert entry.lang == "en"
    assert entry.text == (
        '/w W0lfieAGR Hi! I want to buy: x6 "Primary Deadhead (rank 0)" '
        "for 6 platinum. (warframe.market)"
    )


def test_order_whisper_sell_direction() -> None:
    """订单 type=buy（他在收）→ 我去卖。"""
    order = make_order(type=TransactionEnum.BUY, platinum=15)
    entry = order_whisper(order, "主要·死首", "Primary Deadhead")
    assert entry is not None
    assert "出售" in entry.text


def test_order_whisper_without_ingame_name() -> None:
    order = make_order(user={"id": "u", "locale": "zh-hans"})
    assert order_whisper(order, "物品", "Item") is None


def test_order_whisper_fallback_lang() -> None:
    """卖家没填 locale 时用兜底语言。"""
    order = make_order(user={"id": "u", "ingameName": "Someone"})
    zh = order_whisper(order, "物品", "Item", fallback="zh")
    en = order_whisper(order, "物品", "Item", fallback="en")
    assert zh is not None and en is not None
    assert zh.lang == "zh" and en.lang == "en"
    assert "你好!" in zh.text and "Hi!" in en.text


# ---------------------------------------------------------------- 紫卡


def _riven_auction(**kwargs) -> RivenAuction:
    payload = {
        "id": "a",
        "buyout_price": 5,
        "owner": {"ingame_name": "Mr_Bullet", "locale": "en", "status": "offline"},
        "item": {
            "type": "riven",
            "name": "satitio",
            "weapon_url_name": "nagantaka",
            "mod_rank": 0,
            "re_rolls": 0,
            "polarity": "naramon",
            "mastery_level": 15,
            "attributes": [
                {"value": 12.4, "positive": True, "url_name": "electric_damage"},
            ],
        },
    }
    payload.update(kwargs)
    return RivenAuction.model_validate(payload)


def test_riven_whisper_en() -> None:
    entry = riven_whisper(_riven_auction(), "噬蛇弩", "Nagantaka")
    assert entry is not None
    assert entry.text == '/w Mr_Bullet Hi! I want to buy your Nagantaka riven "Satitio"'
    assert entry.status == "offline"


def test_riven_whisper_zh() -> None:
    auction = _riven_auction(
        owner={"ingame_name": "卖家", "locale": "zh-hans", "status": "online"}
    )
    entry = riven_whisper(auction, "噬蛇弩", "Nagantaka")
    assert entry is not None
    assert entry.text == "/w 卖家 你好! 我想购买你的「噬蛇弩」紫卡 Satitio"


# ---------------------------------------------------------------- 玄骸


def _lich_auction(**kwargs) -> LichSisterAuction:
    payload = {
        "id": "b",
        "buyout_price": 120,
        "owner": {"ingame_name": "NOPE-Azurax", "locale": "de", "status": "offline"},
        "item": {
            "type": "lich",
            "element": "magnetic",
            "damage": 38,
            "having_ephemera": False,
            "weapon_url_name": "kuva_bramma",
        },
    }
    payload.update(kwargs)
    return LichSisterAuction.model_validate(payload)


def test_lich_whisper_en() -> None:
    entry = lich_whisper(_lich_auction(), "赤毒·布拉玛", "Kuva Bramma")
    assert entry is not None
    assert entry.text == "/w NOPE-Azurax Hi! I want to buy your Kuva Bramma (38% Magnetic)"


def test_lich_whisper_zh_and_ephemera() -> None:
    auction = _lich_auction(
        owner={"ingame_name": "卖家", "locale": "zh-hans", "status": "online"},
        item={
            "type": "lich",
            "element": "toxin",
            "damage": 25,
            "having_ephemera": True,
            "weapon_url_name": "kuva_bramma",
        },
    )
    entry = lich_whisper(auction, "赤毒·布拉玛", "Kuva Bramma")
    assert entry is not None
    assert entry.text == "/w 卖家 你好! 我想购买你的「赤毒·布拉玛」（25% 毒素）（带幻纹）"


# ---------------------------------------------------------------- 语言选择


@pytest.mark.parametrize(
    ("locale", "expected"),
    [
        ("zh-hans", "zh"),
        ("zh-hant", "zh"),
        ("en", "en"),
        ("de", "en"),
        (None, "zh"),
        ("", "zh"),
    ],
)
def test_pick_lang(locale, expected) -> None:
    assert pick_lang(locale, fallback="zh") == expected


# ---------------------------------------------------------------- 会话缓存


def test_cache_roundtrip(monkeypatch) -> None:
    whisper_service.clear()
    entries = [order_whisper(make_order(), "物品", "Item")]

    whisper_service.remember("s1", "u1", "WM", entries)
    assert whisper_service.count("s1", "u1") == 1
    assert whisper_service.pop("s1", "u1", 1) is entries[0]
    assert whisper_service.pop("s1", "u1", 2) is None
    # 别人的卡片互不影响
    assert whisper_service.count("s1", "u2") == 0


def test_cache_expiry(monkeypatch) -> None:
    whisper_service.clear()
    now = [1000.0]
    monkeypatch.setattr(
        whisper_service, "time", SimpleNamespace(time=lambda: now[0])
    )
    entries = [order_whisper(make_order(), "物品", "Item")]
    whisper_service.remember("s1", "u1", "WM", entries)
    assert whisper_service.count("s1", "u1") == 1

    now[0] += whisper_service.PICK_TTL + 1
    assert whisper_service.count("s1", "u1") == 0
    assert whisper_service.pop("s1", "u1", 1) is None


# ---------------------------------------------------------------- /w 回复文本


def test_reply_returns_whisper() -> None:
    whisper_service.clear()
    entries = [order_whisper(make_order(), "物品", "Item")]
    whisper_service.remember("s1", "u1", "WM", entries)
    assert whisper_service.reply_for("s1", "u1", "1") == entries[0].text


def test_reply_out_of_range() -> None:
    whisper_service.clear()
    whisper_service.remember(
        "s1", "u1", "WM", [order_whisper(make_order(), "物品", "Item")]
    )
    assert "超出范围" in whisper_service.reply_for("s1", "u1", "9")


def test_reply_without_cache() -> None:
    whisper_service.clear()
    assert "还没有可用的私聊信息" in whisper_service.reply_for("s1", "u1", "1")


def test_reply_usage() -> None:
    whisper_service.clear()
    assert "用法" in whisper_service.reply_for("s1", "u1", "")
    assert "不是序号" in whisper_service.reply_for("s1", "u1", "abc")


def test_reply_offline_hint() -> None:
    whisper_service.clear()
    offline = make_order(
        user={"id": "u", "ingameName": "Someone", "locale": "zh-hans", "status": "offline"}
    )
    whisper_service.remember("s1", "u1", "WM", [order_whisper(offline, "物品", "Item")])
    assert "当前离线" in whisper_service.reply_for("s1", "u1", "1")


# ---------------------------------------------------------------- 服务层接线


def test_orders_model_carries_whispers() -> None:
    """_build_orders_model_from_item 要把私聊语句挂到 Orders 上。"""
    from src.model.orders_items import OrdersItems
    from src.service.market_orders import MarketOrdersService

    item = OrdersItems(id="item-1", name="主要·死首", enName="Primary Deadhead")
    orders = [
        make_order(platinum=20, rank=5),
        make_order(
            platinum=6,
            quantity=6,
            rank=0,
            user={"id": "u", "ingameName": "W0lfieAGR", "locale": "en"},
        ),
    ]
    model = MarketOrdersService._build_orders_model_from_item(
        item, "pc", False, False, orders
    )
    assert len(model.whispers) == 2
    assert model.whispers[0].lang == "zh"
    assert model.whispers[1].lang == "en"
    assert model.whispers[0].text.startswith("/w zyx6687 你好!")
    assert model.whispers[1].text.startswith("/w W0lfieAGR Hi!")


def test_orders_model_skips_orders_without_name() -> None:
    """没有 ingame_name 的订单不生成语句，但仍保留在 orders 里。"""
    from src.model.orders_items import OrdersItems
    from src.service.market_orders import MarketOrdersService

    item = OrdersItems(id="item-1", name="物品", enName="Item")
    orders = [make_order(), make_order(user={"id": "u", "locale": "zh-hans"})]
    model = MarketOrdersService._build_orders_model_from_item(
        item, "pc", False, False, orders
    )
    assert len(model.orders) == 2
    assert len(model.whispers) == 1
