# stockSelect_MA_v2 模块化均线选股系统

## 快速使用

```bash
# 必须使用 quant 环境
conda run -n quant python src/run.py --skip-update --condition golden
```

## 功能说明

基于 A 股主板 3000+ 股票的均线择股系统，通过多进程计算 MA3/5/10/20/30 均线，按预设条件筛选符合条件的股票。

## 项目结构

```
stockSelect_MA_v2/
└── src/
    ├── config.py          # 配置：均线周期、线程数、路径
    ├── utils.py           # 工具：请求限速、交易日期
    ├── stock_list.py      # 股票列表下载与更新
    ├── data_fetcher.py    # 数据获取：实时行情、日线下载
    ├── sma_calculator.py  # 均线计算（多进程）
    ├── selector.py        # 筛选条件定义
    └── run.py             # 主入口
```

## 运行命令

```bash
conda run -n quant python src/run.py                    # 完整流程
conda run -n quant python src/run.py --skip-update      # 只计算+筛选
conda run -n quant python src/run.py --skip-calc         # 只更新数据
conda run -n quant python src/run.py --skip-update --condition golden   # 单条件
```

## 筛选条件

| 条件 | 说明 | 核心逻辑 |
|------|------|----------|
| `golden` | 金叉 | MA3 上穿 MA5，MA 多头排列收红 |
| `golden2` | 金叉变体 | MA3 上穿 MA5，前2日 MA3 在 MA5 下 |
| `flowers` | 花开富贵 | 均线差值逐日扩大，斜率加速 |
| `rabbit` | 放量突破 | 收盘 > MA3×1.05，成交量 > vol_MA5×1.05 |
| `sun` | 连续上涨 | 连续4日收红且逐日上涨 |
| `bitBoard` | 涨停检测 | 股价 = 高价 = 前收盘×1.1 |
| `MakingChips` | 庄家吸筹 | 均线差值 < 0.06，均线重叠 |

## 性能实测

| 指标 | 数值 |
|------|------|
| 股票总数 | 3181 |
| 计算耗时 | 17.6 秒（多进程） |
| 筛选耗时 | 8.2 秒 |
| 单股平均 | 5.5 毫秒 |

## 数据说明

- **股票列表**: `../stockSelect_MA/stock_live_list.csv`
- **日线数据**: `../A股日线数据/{code}.csv`
- **MA数据**: `../A股日均线数据/{code}.csv`（运行后生成）
- **结果输出**: `../A股选股数据/{日期}/{条件名}.csv`

## 添加新条件

在 `src/selector.py` 的 `make_conditions()` 中添加：

```python
'my_condition': lambda df: (
    df['close'].iloc[-1] > df['MA_A'].iloc[-1]
    and df['vol'].iloc[-1] > df['vol_MA_B'].iloc[-1]
    # ... 其他条件
),
```

然后在 `config.py` 的 `SELECTOR_CONDITIONS` 列表中添加条件名。

## 与原版对比

| | 原版 (Notebook) | v2 (模块化) |
|---|---|---|
| 代码形式 | 140KB 单文件 | 7 个独立模块 |
| 计算方式 | 多线程 | **多进程** |
| 调参方式 | 滚动查找 | `config.py` 集中管理 |
| 扩展方式 | 修改Notebook | 修改对应模块 |

## 故障排查

| 问题 | 解决 |
|------|------|
| `stock_live_list.csv` 不存在 | 运行 `update_stock_list()` 下载股票列表 |
| `A股日线数据/*.csv` 不存在 | 运行 `update_all_daily()` 下载日线数据 |
| 缺少 `open` 列报错 | 重新运行 `--skip-update` 重新计算 MA |

## 环境要求

- Python 3.x
- conda 环境: `quant`
- 依赖: `tushare`, `pandas`, `numpy`, `python-dotenv`
