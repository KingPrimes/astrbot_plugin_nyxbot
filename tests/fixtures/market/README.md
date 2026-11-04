# 市场 API 快照（2026-11-04）

真实响应的**冻结副本**，供测试与开发参考。测试期间**禁止联网**（`tests/conftest.py`
会直接掐掉 socket 连接）。

## 文件

| 文件 | 记录数 | 来源 |
|---|---|---|
| `items.json` | 63 条（从 3893 条抽样） | `GET /v2/items` |
| `orders_frost_prime_set.json` | 24 条（从 844 条抽样） | `GET /v2/orders/item/frost_prime_set` |
| `item_set_frost_prime_set.json` | 5 个 item | `GET /v2/item/frost_prime_set/set` |
| `auctions_riven_nagantaka.json` | 10 条（从 100 条抽样） | `GET /v1/auctions/search?type=riven&weapon_url_name=nagantaka` |
| `auctions_lich_kuva_bramma.json` | 10 条（从 100 条抽样） | `GET /v1/auctions/search?type=lich&weapon_url_name=kuva_bramma` |

抓取时间：2026-11-04 20:19 ~ 20:24（本机直连）。

## 隐私处理

- **玩家名与用户 slug 已匿名化**：`ingameName` / `ingame_name` / 用户 `slug` 统一替换为
  `Player01`、`Player02`…（共 77 个），不影响字段形态与测试；
- **物品名、物品 slug、价格、时间戳、ID 保持原样**，仍是真实响应。

## 抽样规则

- **items**：按「字段组合」分组（共 11 种），每种最多取 6 条，保证所有字段形态都覆盖
  （`maxRank` / `bulkTradable` / `subtypes` / `vaulted` / `ducats` / `endoMultiplier` /
  星数 / `subIcon`），并强制包含 `frost_prime_set`、`secura_dual_cestra`、
  `ayatan_orta_sculpture`、`kitgun_riven_mod_veiled` 等典型物品。
- **orders**：按 `(type, rank 有无, locale, crossplay)` 分桶，每桶最多 3 条。
- **auctions**：按 `owner.locale` 分桶，每种最多 2 条，保证语言多样性。
- **i18n**：`items.json` 与 `item_set` 均含 `en` 与 `zh-hans`，与插件实际请求头一致。

## 为什么不能联网跑测试

官方规则 <https://docs.warframe.market/docs/rules/overview> 明确要求：

- **User-Agent 必须可识别**，禁止伪装浏览器；
- **谨慎请求**：用缓存、复用响应、避免紧轮询；
- **限流**：公共 API `3 req/s`，合约搜索（auctions）约 `10~20 req/min`；
- 违规可能被临时或永久限制访问。

所以：

1. 测试只读本地快照；
2. 插件侧已加 `User-Agent: NyxBot-AstrBot/1.0 (+仓库地址)`，并对
   `warframe.market` 的请求做 0.35 s 最小间隔节流（见 `src/util/http_utils.py`）。

## 需要刷新快照时

**不要**在测试或 CI 里刷新。手动执行，且注意频率：

```bash
# 一次抓一个，间隔至少 1 秒；auctions 属于合约搜索，建议间隔 3 秒
curl -s -H "language: zh-hans" "https://api.warframe.market/v2/items" -o items_full.json
```

抓完按上面的抽样规则裁剪（items 全量约 2.5 MB，直接进仓库太重），再更新本文件的
「抓取时间」。订单与拍卖是易变数据，刷新后 `test_auctions_cover_multiple_locales`
这类断言可能需要同步调整。

## 相关测试

```bash
python -m pytest tests -q          # 12 条，约 5 秒，全程离线
```

覆盖：字段完整性（API 有、模型不能缺）、模型解析、i18n 双语、locale 多样性。
