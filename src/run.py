#!/usr/bin/env python3
"""
主入口：运行均线选股系统

使用方式：
    cd stockSelect_MA_v2
    python -m src.run

可选参数：
    --skip-update     跳过数据更新，直接计算均线和筛选
    --skip-calc       只更新数据，不计算均线和筛选
    --condition C     只运行指定条件（如 golden, flowers）
"""
import argparse
import sys
import os

# 添加父目录到路径，以便直接运行时能导入src模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tushare as ts

# 尝试相对导入，失败则使用绝对导入
try:
    from .config import (
        TUSHARE_API_TOKEN, RUN_REALTIME, DATA_UPDATED,
        SELECTOR_CONDITIONS
    )
    from .utils import start_request_controller, get_latest_trade_date
    from .stock_list import get_stock_list, read_stock_list, update_stock_list
    from .data_fetcher import fetch_all_realtime, update_all_daily
    from .sma_calculator import calculate_all_sma
    from .selector import screen_all_stocks
except ImportError:
    from src.config import (
        TUSHARE_API_TOKEN, RUN_REALTIME, DATA_UPDATED,
        SELECTOR_CONDITIONS
    )
    from src.utils import start_request_controller, get_latest_trade_date
    from src.stock_list import get_stock_list, read_stock_list, update_stock_list
    from src.data_fetcher import fetch_all_realtime, update_all_daily
    from src.sma_calculator import calculate_all_sma
    from src.selector import screen_all_stocks


def main():
    parser = argparse.ArgumentParser(description='均线选股系统')
    parser.add_argument('--skip-update', action='store_true', help='跳过数据更新')
    parser.add_argument('--skip-calc', action='store_true', help='只更新数据，不计算')
    parser.add_argument('--condition', type=str, default=None, help=f'指定条件: {SELECTOR_CONDITIONS}')
    args = parser.parse_args()

    # 初始化Tushare
    if not TUSHARE_API_TOKEN:
        print("错误: 未设置 Tushare API Token")
        print("请在 .env 文件中设置 Tushare_API_Token=你的token")
        return

    ts.set_token(TUSHARE_API_TOKEN)
    pro = ts.pro_api()

    # 读取股票列表
    stock_list = read_stock_list()
    print(f"股票池数量: {len(stock_list)}")

    # ================== 数据更新 ==================
    if not args.skip_update and not DATA_UPDATED:
        print("\n===== 开始数据更新 =====")

        if RUN_REALTIME:
            print("模式: 盘中实时更新")
            # 获取所有实时数据
            fetch_all_realtime(stock_list, pro)
        else:
            print("模式: 盘后更新")
            start_request_controller()
            update_all_daily(stock_list, pro)

    # ================== 均线计算 ==================
    if not args.skip_calc:
        print("\n===== 开始计算均线 =====")
        calculate_all_sma()

        # ================== 股票筛选 ==================
        print("\n===== 开始筛选股票 =====")
        conditions = [args.condition] if args.condition else SELECTOR_CONDITIONS

        for cond in conditions:
            print(f"\n--- 筛选条件: {cond} ---")
            results = screen_all_stocks(cond)
            print(f"满足条件: {len(results)} 支")

    print("\n===== 运行完成 =====")


if __name__ == '__main__':
    main()
