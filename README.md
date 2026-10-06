# 量化实操 · Quant in Practice

> 一个个人量化系统的工程实战记录：数据管线、模拟盘调度、风控、验证体系，以及真实踩过的坑。
>
> *A hands-on quant engineering log — data pipelines, paper-trading orchestration, risk controls, validation, and postmortems.*

这里不放"年化收益多少"的策略神话，只记录**让一个无人值守的量化系统真正可靠运行**的工程部分。所有代码均脱敏：不包含任何选股逻辑、因子定义、调仓阈值或具体标的池。

## 为什么有这个仓库

个人量化最大的敌人往往不是模型，而是数据和工程：一个你以为严谨的边界处理、一张该拆开却图省事复用的表、一次只取最新分区的查询，都可能让忠实的风控替你做出最糟的决策。

模型错了你还有止损，工程错了，止损本身会反过来砍你。

## 目录

### 🩺 事故复盘 Postmortems

| # | 主题 | 关键词 |
|---|---|---|
| 01 | [没亏钱却触发 -15.7% 熔断、还自动砍了半仓](postmortems/01-missing-price-drawdown-fuse/) | 缺失数据≠价格0 · 估值口径 · 全量快照取末值 |

每个复盘都包含：可独立运行的最小复现、错误写法 vs 修复写法、单元测试。

### 规划中（对应系列文章）

- 10 盘无人值守模拟盘的调度 / 数据管线整体设计
- 个人量化的数据验证体系：怎么让系统在你睡觉时自己抓 bug

## 运行方式

零第三方依赖，Python 3.9+ 标准库即可：

```bash
# 进入某个事故目录，例如 01
cd postmortems/01-missing-price-drawdown-fuse

# 端到端复现
python scripts/reproduce_incident.py

# 单元测试
python -m unittest discover -s tests -v
```

## 免责声明

- 本仓库仅为**软件工程与数据质量**层面的技术分享，不构成任何投资建议，也不提供任何交易策略。
- 示例数字为说明口径差异而构造/脱敏，不代表任何真实账户的精确数据。

## License

[MIT](LICENSE)
