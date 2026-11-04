"""测试全局配置：禁止联网 + 让 ``src`` 可导入。

warframe.market 的规则（https://docs.warframe.market/docs/rules/overview）明确要求
「谨慎请求、优先缓存、避免紧轮询」。测试一律使用 ``tests/fixtures`` 下的真实响应快照，
这里直接把 socket 连接掐掉，防止以后误加联网测试。
"""
from __future__ import annotations

import pathlib
import socket
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    """任何测试都不允许建立网络连接。"""

    def _guard(*args, **kwargs):
        raise RuntimeError(
            "测试禁止访问网络：请使用 tests/fixtures/market/ 下的真实快照"
        )

    monkeypatch.setattr(socket.socket, "connect", _guard)
    monkeypatch.setattr(socket.socket, "connect_ex", _guard)
    monkeypatch.setattr(socket, "create_connection", _guard)
