<div align="center">

<img src="logo.png" alt="NyxBot Logo" width="120"/>

# astrbot_plugin_nyxbot

AstrBot 的 Warframe 助手插件，目标实现与 nyxbot 功能相同。

</div>

## 功能

### 指令

插件支持通过 `wf_command_prefix` 配置项自定义指令前缀：

- **前缀非空时**（如设为 `wf`）：指令以 `/wf help` 形式触发
- **前缀为空时**（默认）：指令以 `/help` 形式触发，无需前缀

| 指令 | 说明 | 状态 |
|------|------|------|
| `help` | 显示 Warframe 助手指令帮助 | ✅ 已实现 |
| `平原` | 查看平原时间 | 🚧 开发中 |
| `警报` | 查看警报 | 🚧 开发中 |
| `突击` | 查看突击 | 🚧 开发中 |
| `裂隙` | 查看裂隙 | 🚧 开发中 |
| `入侵` | 查看入侵 | 🚧 开发中 |
| `奸商` | 查看虚空商人 | 🚧 开发中 |
| `仲裁` | 查看仲裁 | 🚧 开发中 |

## 安装

在 AstrBot 管理面板中搜索 `nyxbot` 安装，或手动将此仓库克隆到 `data/plugins/` 目录下。

## 配置

插件安装后，在 AstrBot 管理面板的插件配置中可设置：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `wf_update_interval` | 世界状态更新间隔（秒） | `600` |
| `wf_notification_retention_hours` | 通知历史保留时长（小时） | `12` |
| `wf_data_source_cdn` | 数据源CDN | `https://testingcf.jsdelivr.net/gh/KingPrimes/DataSource` |
| `wf_arbitration_data` | 仲裁数据源Url地址 | `https://wf.555590.xyz/api/arbys?days=30` |
| `wf_command_prefix` | 指令前缀（为空则无需前缀） | ` `（空） |

### 数据源CDN可选项

- `https://testingcf.jsdelivr.net/gh/KingPrimes/DataSource`
- `https://jsd.onmicrosoft.cn/gh/KingPrimes/DataSource`
- `https://cdn.jsdelivr.net/gh/KingPrimes/DataSource`
- `https://kingprimes.top`

## 依赖

- `aiohttp>=3.9.0`
- `cachetools>=5.3.0`
- `Pillow>=10.0.0`
- `pydantic>=2.0.0`
- `orjson>=3.9.0`

## 开发

基于 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 插件框架开发。

- [AstrBot 插件开发文档](https://docs.astrbot.app/dev/star/plugin-new.html)

### 添加新指令

1. 在 [`commands/`](commands/) 目录下创建新的指令文件（如 `wf_plain.py`）
2. 使用 [`registry.py`](registry.py) 提供的 `wf` 和 `command_prefix` 注册指令：

```python
from astrbot.api.event import AstrMessageEvent
from ..registry import command_prefix, wf

@wf.command("平原")
async def wf_plain(self, event: AstrMessageEvent):
    """查看平原时间"""
    yield event.plain_result("平原信息...")
```

3. 在 [`commands/__init__.py`](commands/__init__.py) 的 `register_all()` 中导入新模块：

```python
from . import wf_plain  # noqa: F401
```

> **注意**：[`registry.py`](registry.py) 会自动修补 Handler 的 `__module__`，确保 AstrBot 插件管理器能正确发现独立文件中定义的 Handler。

## 项目结构

```
astrbot_plugin_nyxbot/
├── main.py                    # 插件入口（NyxBotPlugin 类）
├── registry.py                # 指令注册与模块路径修补
├── _conf_schema.json          # 插件配置 schema
├── requirements.txt           # Python 依赖
├── metadata.yaml              # 插件元数据
├── commands/
│   ├── __init__.py            # 指令注册中心（自动导入所有指令模块）
│   └── wf_help.py             # /help 帮助指令
├── logo.png                   # 插件图标
└── LICENSE                    # 开源协议
```

## 许可证

详见 [LICENSE](LICENSE) 文件。
