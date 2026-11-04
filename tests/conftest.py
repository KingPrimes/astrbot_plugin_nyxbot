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


_LOOPBACK = {"127.0.0.1", "::1", "localhost", "0.0.0.0", ""}


def _is_loopback(address: object) -> bool:
    """回环地址放行：asyncio 在 Windows 上建事件循环要用 socketpair。"""
    try:
        host = address[0]  # type: ignore[index]
    except Exception:
        return False
    return str(host) in _LOOPBACK


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    """禁止访问外部网络（回环放行）。"""

    def _guard(*args, **kwargs):
        address = args[1] if len(args) > 1 else kwargs.get("address")
        if _is_loopback(address):
            return _real_connect(*args, **kwargs)
        raise RuntimeError(
            "测试禁止访问网络：请使用 tests/fixtures/market/ 下的真实快照"
        )

    _real_connect = socket.socket.connect
    _real_connect_ex = socket.socket.connect_ex
    _real_create = socket.create_connection

    monkeypatch.setattr(socket.socket, "connect", _guard)
    monkeypatch.setattr(
        socket.socket,
        "connect_ex",
        lambda *a, **k: _real_connect_ex(*a, **k) if _is_loopback(a[1] if len(a) > 1 else k.get("address")) else 1,
    )
    monkeypatch.setattr(socket, "create_connection", _guard)
