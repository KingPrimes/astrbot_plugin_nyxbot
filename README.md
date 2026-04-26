# astrbot_plugin_nyxbot

AstrBot 的 Warframe 助手插件，目标实现与 nyxbot 功能相同。

## 功能

- `/nyx` - 获取 NyxBot 欢迎信息与帮助
- `/平原` - 查看平原时间（开发中）
- `/警报` - 查看警报（开发中）
- `/突击` - 查看突击（开发中）
- `/裂隙` - 查看裂隙（开发中）
- `/入侵` - 查看入侵（开发中）
- `/奸商` - 查看虚空商人（开发中）
- `/仲裁` - 查看仲裁（开发中）

## 安装

在 AstrBot 管理面板中搜索 `nyxbot` 安装，或手动将此仓库克隆到 `data/plugins/` 目录下。

## 配置

插件安装后，在 AstrBot 管理面板的插件配置中可设置：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `wf_platform` | Warframe 平台 | `pc` |
| `wf_update_interval` | 世界状态更新间隔（秒） | `600` |
| `wf_notification_retention_hours` | 通知历史保留时长（小时） | `12` |
| `wf_proxy_enabled` | 是否启用代理 | `false` |
| `wf_proxy_host` | 代理地址 | `` |
| `wf_proxy_port` | 代理端口 | `0` |
| `wf_data_source_cdn` | 数据源CDN前缀 | `https://testingcf.jsdelivr.net/gh/KingPrimes/DataSource` |

## 开发

基于 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 插件框架开发。

- [AstrBot 插件开发文档](https://docs.astrbot.app/dev/star/plugin-new.html)
- [迁移计划](plans/migration_plan.md)

## 项目结构

```
astrbot_plugin_nyxbot/
├── main.py                    # 插件入口
├── _conf_schema.json          # 插件配置 schema
├── requirements.txt           # Python 依赖
├── nyxbot/
│   ├── config.py              # 配置管理
│   ├── api_client.py          # HTTP 客户端 + API URL
│   ├── cache.py               # 缓存管理
│   ├── data_source.py         # 数据源加载
│   ├── models/                # 数据模型
│   ├── world_state/           # 世界状态查询
│   ├── market/                # Market 交易查询
│   ├── relics/                # 遗物查询
│   ├── riven/                 # 紫卡分析
│   ├── subscribe/             # 订阅与通知
│   ├── draw/                  # 绘图模块
│   └── utils/                 # 工具方法
└── plans/                     # 迁移计划文档
```
