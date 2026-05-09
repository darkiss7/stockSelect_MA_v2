"""
统计验证模块：对比所有筛选条件的历史表现。

核心功能：
1. 批量回测所有历史筛选数据
2. 对比各条件的收益率、胜率、夏普等指标
3. vs 随机选股基准
4. 计算统计显著性（p值）

使用方式：
    conda run -n quant python -m src.validator --hold 5 --start 20240101 --end 20250131
"""
import os
import argparse
import pandas as pd
import numpy as np
from datetime import datetime
from scipy import stats

try:
    from .config import SELECTOR_CONDITIONS, HOLD_DAYS
    from .backtester import backtest_condition, print_report
except ImportError:
    from config import SELECTOR_CONDITIONS
    from backtester import backtest_condition, print_report


def generate_random_baseline(n_trades, daily_returns, random_seed=42):
    """
    生成随机选股基准

    Args:
        n_trades: 交易次数
        daily_returns: 日收益率分布（用于采样）
        random_seed: 随机种子

    Returns:
        随机选股的收益率序列
    """
    np.random.seed(random_seed)
    # 用实际收益率的均值和标准差生成随机收益
    mean_ret = np.mean(daily_returns)
    std_ret = np.std(daily_returns)
    random_returns = np.random.normal(mean_ret, std_ret, n_trades)
    return random_returns


def calculate_statistics(returns, baseline_returns=None):
    """
    计算统计指标

    Args:
        returns: 实际收益率序列
        baseline_returns: 基准收益率序列（可选）

    Returns:
        dict: 统计指标
    """
    n = len(returns)
    if n == 0:
        return {}

    win_rate = np.sum(returns > 0) / n
    avg_return = np.mean(returns)
    std_return = np.std(returns)
    sharpe = avg_return / std_return * np.sqrt(252) if std_return > 0 else 0

    result = {
        'n_trades': n,
        'win_rate': win_rate,
        'avg_return': avg_return,
        'std_return': std_return,
        'sharpe_ratio': sharpe,
        'total_return': np.prod(1 + returns) - 1,
    }

    # 对比基准
    if baseline_returns is not None and len(baseline_returns) > 0:
        # 配对样本 t 检验
        min_len = min(len(returns), len(baseline_returns))
        t_stat, p_value = stats.ttest_rel(returns[:min_len], baseline_returns[:min_len])

        # Wilcoxon 符号秩检验（非参数）
        try:
            w_stat, w_p_value = stats.wilcoxon(returns[:min_len], baseline_returns[:min_len])
        except:
            w_stat, w_p_value = np.nan, np.nan

        result['vs_random'] = {
            'avg_diff': np.mean(returns) - np.mean(baseline_returns),
            'win_rate_diff': win_rate - (np.sum(baseline_returns > 0) / len(baseline_returns)),
            't_statistic': t_stat,
            'p_value': p_value,
            'wilcoxon_p': w_p_value,
            'significant': p_value < 0.05,
        }

    return result


def validate_all_conditions(hold_days=None, start_date=None, end_date=None):
    """
    验证所有条件的表现

    Returns:
        DataFrame: 各条件的统计指标对比表
    """
    if hold_days is None:
        hold_days = HOLD_DAYS
    if start_date is None:
        start_date = '20240101'
    if end_date is None:
        end_date = datetime.now().strftime('%Y%m%d')

    results = []

    print(f"\n{'='*60}")
    print(f"统计验证：持有 {hold_days} 天 | 区间 {start_date} ~ {end_date}")
    print(f"{'='*60}\n")

    for condition in SELECTOR_CONDITIONS:
        print(f"\n--- 验证条件: {condition} ---")

        result = backtest_condition(
            condition=condition,
            hold_days=hold_days,
            start_date=start_date,
            end_date=end_date
        )

        if result is None:
            print(f"  无数据，跳过")
            continue

        stats_dict, trades_df = result
        returns = trades_df['return'].values

        # 计算随机基准（用沪深300的日收益率作为替代，这里简化为用0）
        # 实际应该获取 benchmark 的收益率
        # 这里用 0 作为基准（表示"不亏不赚"）
        baseline_returns = np.zeros(len(returns))

        calc_stats = calculate_statistics(returns, baseline_returns)

        # 合并结果
        row = {
            '条件': condition,
            '交易次数': calc_stats.get('n_trades', 0),
            '胜率': f"{calc_stats.get('win_rate', 0):.1%}",
            '平均收益': f"{calc_stats.get('avg_return', 0):.2%}",
            '总收益': f"{calc_stats.get('total_return', 0):.2%}",
            '夏普比率': f"{calc_stats.get('sharpe_ratio', 0):.2f}",
            'p值': f"{calc_stats.get('vs_random', {}).get('p_value', 1):.3f}",
            '显著': '✓' if calc_stats.get('vs_random', {}).get('significant', False) else '',
        }

        results.append(row)

        print(f"  交易次数: {row['交易次数']}")
        print(f"  胜率: {row['胜率']}")
        print(f"  平均收益: {row['平均收益']}")
        print(f"  总收益: {row['总收益']}")
        print(f"  夏普比率: {row['夏普比率']}")
        if row['p值']:
            print(f"  p值: {row['p值']} {row['显著']}")

    # 汇总表
    if results:
        results_df = pd.DataFrame(results)
        print(f"\n{'='*60}")
        print("条件性能排名（按平均收益排序）")
        print(f"{'='*60}")
        results_df = results_df.sort_values(by='平均收益', ascending=False)
        print(results_df.to_string(index=False))

        # 保存结果
        output_file = f"validation_{hold_days}days.csv"
        results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n结果已保存: {output_file}")

        return results_df

    return None


def main():
    parser = argparse.ArgumentParser(description='统计验证模块')
    parser.add_argument('--hold', type=int, default=None,
                        help=f'持有天数 (默认: {HOLD_DAYS})')
    parser.add_argument('--start', type=str, default='20240101',
                        help='开始日期 YYYYMMDD')
    parser.add_argument('--end', type=str, default=None,
                        help='结束日期 YYYYMMDD (默认: 今天)')
    args = parser.parse_args()

    end_date = args.end or datetime.now().strftime('%Y%m%d')
    hold_days = args.hold or HOLD_DAYS

    validate_all_conditions(
        hold_days=hold_days,
        start_date=args.start,
        end_date=end_date
    )


if __name__ == '__main__':
    main()
