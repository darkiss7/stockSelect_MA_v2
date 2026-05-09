"""
回测引擎：验证选股条件的历史表现。

核心逻辑：
1. 读取历史筛选结果（A股选股数据/日期/条件.csv）
2. 按日期获取买入价格（次日开盘价）
3. 持有N日后获取卖出价格（持有期最后一天的收盘价）
4. 计算收益率，考虑交易成本

输出：
- 单笔交易详情
- 总体统计（收益率、夏普、最大回撤、胜率）
"""
import os
import argparse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from tqdm import tqdm

try:
    from .config import (
        SELECT_DIR, DATA_DIR, HOLD_DAYS, INITIAL_CAPITAL,
        COMMISSION, STAMP_TAX, SLIPPAGE, SELECTOR_CONDITIONS
    )
except ImportError:
    from config import (
        SELECT_DIR, DATA_DIR, HOLD_DAYS, INITIAL_CAPITAL,
        COMMISSION, STAMP_TAX, SLIPPAGE, SELECTOR_CONDITIONS
    )


def get_next_trade_date(daily_df, current_date, n=1):
    """
    获取 current_date 之后的第 n 个交易日

    Args:
        daily_df: 日线数据 DataFrame
        current_date: 当前日期 (YYYYMMDD 格式)
        n: 第几个交易日

    Returns:
        第 n 个交易日的日期字符串 (YYYYMMDD)
    """
    trade_dates = daily_df['trade_date'].astype(str).values
    idx = np.where(trade_dates == str(current_date))[0]
    if len(idx) == 0:
        return None
    target_idx = idx[0] + n
    if target_idx >= len(trade_dates):
        return None
    return trade_dates[target_idx]


def calculate_return(entry_price, exit_price):
    """
    计算单笔收益率（含交易成本）

    买入成本 = entry_price * (1 + COMMISSION + SLIPPAGE)
    卖出收入 = exit_price * (1 - COMMISSION - STAMP_TAX - SLIPPAGE)
    收益率 = (卖出收入 - 买入成本) / 买入成本
    """
    buy_cost = entry_price * (1 + COMMISSION + SLIPPAGE)
    sell_revenue = exit_price * (1 - COMMISSION - STAMP_TAX - SLIPPAGE)
    return (sell_revenue - buy_cost) / buy_cost


def load_daily_data(ts_code):
    """加载单支股票的日线数据"""
    file_path = os.path.join(DATA_DIR, f"{ts_code}.csv")
    if not os.path.exists(file_path):
        return None
    df = pd.read_csv(file_path, dtype={'trade_date': str})
    df = df.sort_values(by='trade_date').reset_index(drop=True)
    return df


def backtest_single_signal(ts_code, entry_date, hold_days, daily_df):
    """
    回测单个信号

    Args:
        ts_code: 股票代码
        entry_date: 买入日期 (YYYYMMDD)
        hold_days: 持有天数
        daily_df: 该股票的日线数据

    Returns:
        dict: {'ts_code': str, 'entry_date': str, 'exit_date': str,
               'entry_price': float, 'exit_price': float, 'return': float}
    """
    # 统一日期格式为 YYYYMMDD（去掉 dashes）
    entry_date_str = str(entry_date).replace('-', '')

    # 找到下一个交易日作为买入日
    trade_dates = daily_df['trade_date'].astype(str).values
    date_indices = {d: i for i, d in enumerate(trade_dates)}

    if entry_date_str not in date_indices:
        return None

    entry_idx = date_indices[entry_date_str]
    if entry_idx + 1 >= len(trade_dates):
        return None

    # 实际买入日 = 次日
    actual_entry_idx = entry_idx + 1
    actual_entry_date = trade_dates[actual_entry_idx]
    actual_entry_row = daily_df[daily_df['trade_date'].astype(str) == actual_entry_date]

    if actual_entry_row.empty:
        return None

    entry_price = actual_entry_row['open'].values[0]
    if pd.isna(entry_price) or entry_price <= 0:
        return None

    # 计算卖出日 = 持有 N 天后的收盘价
    exit_idx = actual_entry_idx + hold_days
    if exit_idx >= len(trade_dates):
        # 数据不够，直接用最后一天
        exit_idx = len(trade_dates) - 1

    exit_date = trade_dates[exit_idx]
    exit_row = daily_df[daily_df['trade_date'].astype(str) == exit_date]

    if exit_row.empty:
        return None

    exit_price = exit_row['close'].values[0]
    if pd.isna(exit_price) or exit_price <= 0:
        return None

    ret = calculate_return(entry_price, exit_price)

    return {
        'ts_code': ts_code,
        'entry_date': actual_entry_date,
        'exit_date': exit_date,
        'entry_price': entry_price,
        'exit_price': exit_price,
        'return': ret
    }


def load_selection_result(condition, date):
    """
    读取某天的筛选结果

    Args:
        condition: 条件名称（如 'golden'）
        date: 日期 (YYYY-MM-DD 或 YYYYMMDD)

    Returns:
        list: 股票代码列表
    """
    date_str = str(date)  # 保持原始格式，如 '2024-12-20'
    file_path = os.path.join(SELECT_DIR, date_str, f"{condition}.csv")
    if not os.path.exists(file_path):
        return []
    df = pd.read_csv(file_path)
    return df['ts_code'].tolist()


def get_available_dates(start_date, end_date, condition):
    """
    获取有筛选结果的日期列表

    Args:
        start_date: 开始日期 (YYYYMMDD)
        end_date: 结束日期 (YYYYMMDD)
        condition: 条件名称

    Returns:
        list: 可用的日期列表 (YYYY-MM-DD 格式)
    """
    dates = []
    # 转换为 YYYYMMDD 格式用于比较
    start_str = str(start_date).replace('-', '')
    end_str = str(end_date).replace('-', '')

    select_parent = os.path.join(SELECT_DIR)
    if not os.path.exists(select_parent):
        return dates

    for date_folder in os.listdir(select_parent):
        # 跳过非日期文件夹和 zip 文件
        if not len(date_folder) == 10 or not date_folder[4] == '-' or date_folder.endswith('.zip'):
            continue

        # 转换为 YYYYMMDD 用于比较
        date_compact = date_folder.replace('-', '')

        # 检查是否在日期范围内
        if not (start_str <= date_compact <= end_str):
            continue

        result_file = os.path.join(select_parent, date_folder, f"{condition}.csv")
        if os.path.exists(result_file):
            dates.append(date_folder)

    return sorted(dates)


def backtest_condition(condition, hold_days=None, start_date=None, end_date=None):
    """
    回测某个条件的历史表现

    Args:
        condition: 条件名称
        hold_days: 持有天数（默认从 config 读取）
        start_date: 开始日期（默认 20240101）
        end_date: 结束日期（默认今天）

    Returns:
        dict: 回测统计结果
    """
    if hold_days is None:
        hold_days = HOLD_DAYS
    if start_date is None:
        start_date = '20240101'
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')

    # 获取有数据的日期
    dates = get_available_dates(start_date, end_date, condition)
    if not dates:
        print(f"没有找到 {condition} 条件在 {start_date}-{end_date} 的筛选数据")
        return None

    all_trades = []
    progress_bar = tqdm(dates, desc=f"回测 {condition}")

    for date in progress_bar:
        # 读取当天选出的股票
        stock_codes = load_selection_result(condition, date)
        if not stock_codes:
            continue

        for ts_code in stock_codes:
            # 加载该股票的日线数据
            daily_df = load_daily_data(ts_code)
            if daily_df is None or len(daily_df) < hold_days + 5:
                continue

            # 回测这笔交易
            result = backtest_single_signal(ts_code, date, hold_days, daily_df)
            if result:
                all_trades.append(result)

        progress_bar.set_postfix({'trades': len(all_trades)})

    if not all_trades:
        print(f"没有有效的交易记录")
        return None

    # 转换为 DataFrame
    trades_df = pd.DataFrame(all_trades)

    # 计算统计指标
    returns = trades_df['return'].values

    stats = {
        'condition': condition,
        'hold_days': hold_days,
        'start_date': start_date,
        'end_date': end_date,
        'total_trades': len(returns),
        'winning_trades': int(np.sum(returns > 0)),
        'losing_trades': int(np.sum(returns <= 0)),
        'win_rate': np.sum(returns > 0) / len(returns),
        'avg_return': np.mean(returns),
        'median_return': np.median(returns),
        'std_return': np.std(returns),
        'max_return': np.max(returns),
        'min_return': np.min(returns),
        'sharpe_ratio': np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0,
    }

    # 计算最大回撤
    cumulative = np.cumprod(1 + returns)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - running_max) / running_max
    stats['max_drawdown'] = np.min(drawdown)

    # 总收益率（假设等权重）
    stats['total_return'] = np.prod(1 + returns) - 1

    # 年化收益率
    n_days = len(dates)
    if n_days > 0:
        stats['annual_return'] = (1 + stats['total_return']) ** (252 / n_days) - 1
    else:
        stats['annual_return'] = 0

    return stats, trades_df


def print_report(stats, trades_df=None):
    """打印回测报告"""
    print("\n" + "=" * 60)
    print(f"回测报告：{stats['condition']} | 持有 {stats['hold_days']} 天")
    print("=" * 60)
    print(f"回测区间：{stats['start_date']} ~ {stats['end_date']}")
    print(f"总交易次数：{stats['total_trades']}")
    print(f"盈利次数：{stats['winning_trades']} | 亏损次数：{stats['losing_trades']}")
    print(f"胜率：{stats['win_rate']:.2%}")
    print("-" * 60)
    print(f"平均收益率：{stats['avg_return']:.2%}")
    print(f"中位数收益率：{stats['median_return']:.2%}")
    print(f"标准差：{stats['std_return']:.2%}")
    print(f"最大收益：{stats['max_return']:.2%}")
    print(f"最大亏损：{stats['min_return']:.2%}")
    print("-" * 60)
    print(f"总收益率：{stats['total_return']:.2%}")
    print(f"年化收益率：{stats['annual_return']:.2%}")
    print(f"夏普比率：{stats['sharpe_ratio']:.2f}")
    print(f"最大回撤：{stats['max_drawdown']:.2%}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='回测引擎')
    parser.add_argument('--condition', type=str, default='golden',
                        help=f'筛选条件: {SELECTOR_CONDITIONS}')
    parser.add_argument('--hold', type=int, default=None,
                        help=f'持有天数 (默认: {HOLD_DAYS})')
    parser.add_argument('--start', type=str, default='20240101',
                        help='开始日期 YYYYMMDD')
    parser.add_argument('--end', type=str, default=None,
                        help='结束日期 YYYYMMDD (默认: 今天)')
    args = parser.parse_args()

    end_date = args.end or datetime.now().strftime('%Y%m%d')
    hold_days = args.hold or HOLD_DAYS

    result = backtest_condition(
        condition=args.condition,
        hold_days=hold_days,
        start_date=args.start,
        end_date=end_date
    )

    if result:
        stats, trades_df = result
        print_report(stats)

        # 保存交易记录
        output_file = f"backtest_{args.condition}_{hold_days}days.csv"
        trades_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n交易记录已保存: {output_file}")
    else:
        print("回测失败，请检查数据是否存在")


if __name__ == '__main__':
    main()
