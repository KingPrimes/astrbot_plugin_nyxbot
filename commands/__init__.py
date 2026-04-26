"""Command registration hub / 指令注册中心

Importing this module triggers all command module imports, which in turn
registers their handlers via the patched decorators in registry.py.

导入此模块会触发所有指令模块的导入，进而通过 registry.py 中
修补过的装饰器注册各自的 Handler。
"""

from __future__ import annotations


def register_all() -> None:
    """Import all command modules to trigger handler registration.

    导入所有指令模块以触发 Handler 注册。
    """
    # 每个指令文件在此导入一次即可完成注册
    from . import wf_help  # noqa: F401


# 模块导入时自动注册所有指令
register_all()
