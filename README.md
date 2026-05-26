<div align="center">

<img src="logo.png" alt="NyxBot Logo" width="120"/>

# NyxBot

AstrBot 的 Warframe 助手插件，提供世界状态查询、市场交易、紫卡分析、订阅通知等功能。

[![AstrBot](https://img.shields.io/badge/AstrBot-%3E%3D4.23.5-blue)](https://github.com/AstrBotDevs/AstrBot)
[![Python](https://img.shields.io/badge/Python-%3E%3D3.12-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

</div>

---

## 功能概览

| 模块 | 说明 |
|------|------|
| 🌍 **世界状态** | 查询警报、突击、裂隙、入侵、平原周期、虚空商人、仲裁、钢铁之路等实时数据 |
| 💰 **市场交易** | 对接 Warframe.Market API，查询物品订单、紫卡拍卖、赤毒/信条武器行情、金/银垃圾回收价 |
| 🔮 **紫卡分析** | OCR 识别紫卡截图 → 武器/词条解析 → 倾向趋势计算 → 多卡片可视化渲染 |
| 📢 **订阅通知** | 群组任务订阅，定时推送世界状态变更通知（警报/突击/裂隙/入侵/奸商/仲裁等） |
| 🔍 **OCR 识别** | 基于 PaddleOCR PP-OCRv5 的文字识别，支持游戏截图解析 |
| 🌐 **中英翻译** | Warframe 物品/状态中英文名称互查，支持别名模糊匹配 |
| ⚙️ **数据管理** | Plugin Pages 管理后台，支持别名、翻译、紫卡词条等数据的可视化 CRUD |

---

## 指令列表

插件支持通过 `wf_command_prefix` 配置项自定义指令前缀：

- **前缀非空时**（如设为 `wf`）：指令以 `/wf help` 形式触发
- **前缀为空时**（默认）：指令以 `/help` 形式触发，无需前缀

### 世界状态

| 指令 | 别名 | 说明 |
|------|------|------|
| `警报` | — | 查看当前警报任务 |
| `突击` | — | 查看今日突击任务 |
| `仲裁` | — | 查看当前仲裁任务 |
| `裂隙` | `裂缝` | 查看当前虚空裂隙 |
| `钢铁裂隙` | `钢铁裂缝` | 查看钢铁之路虚空裂隙 |
| `九重天裂隙` | `九重天` / `九重天裂缝` | 查看九重天虚空裂隙 |
| `入侵` | — | 查看当前入侵任务 |
| `奸商` | `虚空商人` | 查看虚空商人（Baro Ki'Teer） |
| `平原` | — | 查看平原周期（希图斯、金星、扎里曼） |
| `轮换` | `双衍王境` | 查看双衍王境轮换 |
| `钢铁` | — | 查看钢铁之路轮换与精华 |
| `电波` | — | 查看午夜电波任务与奖励 |
| `每日特惠` | — | 查看达尔沃每日特惠商品 |
| `1999` | `日历` | 查看 1999 日历赛季 |
| `执刑官猎杀` | `猎杀` / `执行官` / `执政官` / `执刑官` | 查看执刑官猎杀任务 |
| `遗物` | `核桃` | 查看虚空遗物掉落 |
| `希图斯` | `地球赏金` | 查看希图斯赏金任务 |
| `英择谛` | `火卫二赏金` | 查看英择谛赏金任务 |
| `索拉里斯` | `金星赏金` | 查看索拉里斯赏金任务 |

### 市场交易

| 指令 | 别名 | 说明 |
|------|------|------|
| `WM` | `市场` / `wm` / `market` | 查询 Warframe.Market 物品订单（买卖行情、玩家列表） |
| `WR` | `wr` | 查询 Warframe.Market 紫卡拍卖 |
| `RM` | `rm` | 紫卡市场估价（倾向+词条组合价格估算） |
| `CD` | `cd` / `赤毒` | 查询赤毒武器拍卖行情 |
| `XT` | `xt` / `信条` | 查询信条武器拍卖行情 |
| `金垃圾` | — | 查询可交易金装部件回收价格（Ducats 换算） |
| `银垃圾` | — | 查询可交易银装部件回收价格（Ducats 换算） |

### 紫卡分析

| 指令 | 别名 | 说明 |
|------|------|------|
| `紫卡分析` | `分析紫卡` / `Wfen` | 发送紫卡截图 → OCR 识别 → 多武器候选分析 → 趋势卡片渲染 |

### 帮助

| 指令 | 说明 |
|------|------|
| `wfhelp` | 显示 Warframe 助手完整指令帮助 |

---

## 架构

```
入口层
  main.py (NyxBotPlugin)  →  插件生命周期管理（初始化 / 终止）
  registry.py              →  指令注册 + __module__ 路径修补 + 配置驱动前缀

指令层 (src/commands/ — 23 个模块, 28+ 条指令)
  wf_alerts / wf_arbitration / wf_calendar_seasons / wf_cycle / wf_daily_deals
  wf_duviri / wf_fissures / wf_help / wf_invasions / wf_lite_sortie
  wf_market_dump / wf_market_liches / wf_market_orders / wf_market_riven
  wf_market_sisters / wf_relics / wf_riven_analyse / wf_riven_market
  wf_season_info / wf_sorties / wf_steel_path / wf_syndicate / wf_void_trader

服务层 (src/service/ — 22 个服务模块)
  WorldStateService          ↔  世界状态缓存 + 自动刷新 + 翻译管道
  MarketService / Orders / Riven / Ducats / Sync  ↔  Warframe.Market 全链路
  RivenAnalyseService        ↔  紫卡 OCR 解析 + 武器匹配 + 倾向趋势计算
  StateTranslationService    ↔  中英文名称翻译
  AliasService               ↔  别名模糊匹配
  SubscriptionService        ↔  群组任务订阅管理
  NotificationService        ↔  定时推送通知
  DataSyncService / DataAdminService  ↔  静态数据同步与管理
  NightWaveService / RelicsService / WeaponsService / WarframesService
  SentinelsService / UpgradesService / NodesService / RewardService / RivenService

数据层 (src/model/ — 60+ TortoiseORM 模型)
  model/                              →  核心模型（别名、翻译、订阅、通知、紫卡）
  model/world_state/                  →  世界状态模型（警报、突击、裂隙、入侵、周期…）
  model/market/                       →  市场模型（订单、紫卡拍卖、赤毒/信条、杜卡德）
  model/export/                       →  导出数据（战甲、武器、遗物、MOD、奖励…）
  SQLite 本地存储

渲染层 (src/render/ — 21 个卡片渲染器 + 引擎)
  CardRenderer (主引擎)  →  字体管理 / 派系图标 / 任务着色
  ImageCombiner (建造者) →  圆角矩形 / 双层边框 / 看板娘 / 文字排版
  card_*.py (各卡片)     →  警报 / 突击 / 裂隙 / 入侵 / 仲裁 / 平原 / 双衍
                          钢铁 / 奸商 / 电波 / 1999 / 执刑官 / 遗物 / 赏金 / 每日特惠
                          市场订单 / 紫卡拍卖 / 赤毒信条 / 杜卡德 / 紫卡分析

基础设施
  src/api/         →  Warframe.Market API / 世界状态 API / CDN 客户端
  src/ocr/         →  PaddleOCR PP-OCRv5 文字识别服务
  src/wenum/       →  枚举定义（派系 / 任务类型 / 裂隙类型 / 元素 / 极性 / 伤害）
  src/util/        →  工具函数（HTTP 重试 / 缓存 / 时间格式化 / 字符串 / 压缩）
  src/init/        →  初始化引擎（TortoiseORM 连接 / 导出文件下载）
  src/web_api/     →  Plugin Pages 管理后台 API
  pages/           →  Plugin Pages 管理后台前端
```

### 数据流

```
用户发送指令
  → registry.py 路由到对应 Handler
    → Service 层从缓存/API 获取数据
      → CardRenderer 渲染为 Pillow 图片
        → 返回图片消息给用户

世界状态同步
  → 后台 asyncio.Task 定时从 WF_API 拉取 JSON
    → 解析 → 翻译 → 写入 SQLite 缓存
      → 对比变更 → 触发订阅通知推送
```

---

## 安装

### 方式一：管理面板安装

在 AstrBot 管理面板的插件市场中搜索 `nyxbot` 安装。

### 方式二：手动安装

将此仓库克隆到 AstrBot 的 `data/plugins/` 目录下：

```bash
cd AstrBot/data/plugins
git clone https://github.com/KingPrimes/astrbot_plugin_nyxbot.git
```

安装依赖：

```bash
cd astrbot_plugin_nyxbot
uv sync
```

> **注意**：PaddleOCR 首次运行时会自动下载 PP-OCRv5 移动端模型（约 10MB）至 `~/.paddlex/official_models/`。

---

## 配置

插件安装后，在 AstrBot 管理面板的插件配置中可设置以下选项：

| 配置项 | 说明 | 类型 | 默认值 |
|--------|------|------|--------|
| `wf_update_interval` | 世界状态更新间隔（秒），建议不低于 60 | `int` | `600` |
| `wf_notification_retention_hours` | 通知历史保留时长（小时），超时自动清理 | `int` | `12` |
| `wf_data_source_cdn` | 数据源 CDN 地址（翻译/别名等静态数据） | `string` | `https://testingcf.jsdelivr.net/gh/KingPrimes/DataSource` |
| `wf_arbitration_data` | 仲裁数据源 URL，需返回 JSON 格式 | `string` |  |
| `wf_command_prefix` | 指令前缀，为空则无需前缀 | `string` | `""`（空） |
| `db_debug` | 数据库调试日志，开启后输出 SQL 查询日志 | `bool` | `false` |

### 数据源 CDN 可选项

- `https://testingcf.jsdelivr.net/gh/KingPrimes/DataSource`
- `https://jsd.onmicrosoft.cn/gh/KingPrimes/DataSource`
- `https://cdn.jsdelivr.net/gh/KingPrimes/DataSource`
- `https://kingprimes.top`

---

## 项目结构

```
astrbot_plugin_nyxbot/
├── main.py                    # 插件入口（NyxBotPlugin 类）
├── registry.py                # 指令注册与模块路径修补
├── _conf_schema.json          # 插件配置 Schema
├── metadata.yaml              # 插件元数据
├── pyproject.toml             # 项目配置与依赖管理
├── requirements.txt           # Python 依赖
├── logo.png                   # 插件图标
├── LICENSE                    # 开源协议
├── pages/
│   └── nyxbot-admin/          # Plugin Pages 管理后台前端
│       └── assets/            # 前端静态资源
├── src/
│   ├── api/                   # 外部 API 封装
│   │   ├── api.py             #   WF 世界状态 / Market / Public Export 端点常量
│   │   ├── market.py          #   MarketClient + Platform 枚举（PC/Xbox/PS/Switch）
│   │   └── cdn_client.py      #   CDN 静态数据客户端（自动获取最新版本号）
│   ├── commands/              # 指令模块（23 个模块，28+ 条指令）
│   ├── config/                # 配置管理
│   ├── init/                  # 初始化引擎（TortoiseORM 连接、导出文件下载）
│   ├── model/                 # 数据模型（TortoiseORM，60+ 模型）
│   │   ├── export/            #   导出数据（战甲、武器、遗物、MOD、奖励、节点）
│   │   │   └── reward/        #     奖励池
│   │   ├── market/            #   市场模型（订单、紫卡拍卖、赤毒信条、杜卡德）
│   │   └── world_state/       #   世界状态模型（警报、突击、裂隙、入侵、周期…）
│   ├── ocr/                   # PaddleOCR PP-OCRv5 文字识别服务
│   ├── render/                # Pillow 卡片渲染引擎
│   │   ├── fonts/             #   字体文件
│   │   ├── standing/          #   看板娘素材
│   │   ├── card_renderer.py   #   主渲染引擎
│   │   ├── image_combiner.py  #   图像合成建造者
│   │   └── card_*.py          #   各卡片渲染器（21 个）
│   ├── service/               # 业务服务层（22 个服务模块）
│   ├── util/                  # 工具函数（缓存、HTTP 重试、时间、字符串、压缩）
│   ├── web_api/               # 数据管理后台 API（Plugin Pages 后端）
│   └── wenum/                 # 枚举定义（派系、裂隙类型、任务类型、元素、极性、伤害）
```

---

## 技术栈

| 类别 | 技术 | 说明 |
|------|------|------|
| 框架 | [AstrBot](https://github.com/AstrBotDevs/AstrBot) | 插件框架（`>=4.23.5`） |
| 数据库 | TortoiseORM + SQLite | 异步 ORM，本地 SQLite 存储 |
| 渲染 | Pillow | 信息卡片直接绘制，无需浏览器 |
| OCR | PaddleOCR PP-OCRv5 | 移动端模型，CPU 推理 |
| 调度 | asyncio | 原生异步定时任务 |
| 网络 | httpx | 异步 HTTP 客户端 |
| 序列化 | orjson / pydantic | 高性能 JSON 解析与数据校验 |
| 缓存 | cachetools | 内存缓存（TTL 策略） |

---

## 开发

### 代码风格

| 规则 | 说明 |
|------|------|
| **Python 版本** | `>=3.12` |
| **Linter** | `ruff>=0.9.0` |
| **测试** | `pytest>=8.0.0` + `pytest-asyncio>=0.25.0` |
| **类型注解** | 所有函数使用完整类型标注，文件头必须包含 `from __future__ import annotations` |
| **文档字符串** | 中英双语 docstring，描述模块/类/方法的功能 |
| **异步** | 所有 Handler 和服务方法均为 `async` |
| **导入** | 使用相对导入（如 `from ...registry import wf`） |
| **结果返回** | 使用 `yield event.plain_result()` 返回文本，`yield event.chain_result()` 返回图片 |

### 添加新指令

1. 在 [`src/commands/`](src/commands/) 目录下创建新的指令文件（如 `wf_plain.py`）
2. 使用 [`registry.py`](registry.py) 提供的 `wf` 装饰器注册指令：

```python
"""wf_plain - /平原 - 查看平原周期"""
from __future__ import annotations

from astrbot.api.event import AstrMessageEvent
import astrbot.api.message_components as Comp

from ...registry import wf
from ..service.world_state import WorldStateService
from ..render.card_renderer import CardRenderer


@wf.command("平原")
async def wf_plain(self, event: AstrMessageEvent):
    """查看平原周期"""
    data = await WorldStateService.get_cetus_cycle()

    if not data:
        yield event.plain_result("暂无数据")
        return

    renderer = CardRenderer()
    img = renderer.create_cycle_card(data)
    img_bytes = CardRenderer.render_to_bytes(img)

    yield event.chain_result([Comp.Image.fromBytes(img_bytes)])
```

3. 在 [`src/commands/__init__.py`](src/commands/__init__.py) 的 `register_all()` 中导入新模块：

```python
from . import wf_plain  # noqa: F401
```

> **注意**：[`registry.py`](registry.py) 会自动修补 Handler 的 `__module__`，确保 AstrBot 插件管理器能正确发现独立文件中定义的 Handler。

### 常用命令

```bash
uv run ruff check .     # 代码规格检查
uv run pytest            # 运行测试
uv run pytest tests/ -k "test_name"  # 运行单个测试
uv sync                  # 安装/更新依赖
```

---

## 许可证

详见 [LICENSE](LICENSE) 文件。
