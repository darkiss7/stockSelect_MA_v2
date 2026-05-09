"""
均线计算：基于日线数据计算MA3/5/10/20/30及成交量均线。
"""
import pandas as pd
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
from .config import A_WINDOW, B_WINDOW, C_WINDOW, D_WINDOW, E_WINDOW, DATA_DIR, MA_DIR
from .stock_list import read_stock_list


def calculate_sma_for_stock(ts_code):
    """计算单支股票的均线数据"""
    daily_file = f"{DATA_DIR}/{ts_code}.csv"
    ma_file = f"{MA_DIR}/{ts_code}.csv"

    try:
        # 加载日线数据：包含open用于收红判断，high/low用于涨停判断
        df = pd.read_csv(
            daily_file,
            usecols=['trade_date', 'open', 'high', 'low', 'close', 'vol'],
            dtype={'trade_date': str, 'open': float, 'high': float, 'low': float, 'close': float, 'vol': float}
        )

        if df.empty or len(df) < E_WINDOW:
            return None

        df = df.sort_values(by='trade_date', ascending=True).reset_index(drop=True)

        # 计算价格均线
        df['MA_A'] = df['close'].rolling(window=A_WINDOW).mean()
        df['MA_B'] = df['close'].rolling(window=B_WINDOW).mean()
        df['MA_C'] = df['close'].rolling(window=C_WINDOW).mean()
        df['MA_D'] = df['close'].rolling(window=D_WINDOW).mean()
        df['MA_E'] = df['close'].rolling(window=E_WINDOW).mean()

        # 计算成交量均线
        df['vol_MA_B'] = df['vol'].rolling(window=B_WINDOW).mean()
        df['vol_MA_C'] = df['vol'].rolling(window=C_WINDOW).mean()

        return (ts_code, df)

    except FileNotFoundError:
        print(f"股票 {ts_code} 日线数据文件不存在")
        return None
    except Exception as e:
        print(f"计算 {ts_code} 均线出错: {e}")
        return None


def batch_write_results(results):
    """批量写入结果到文件"""
    import os
    os.makedirs(MA_DIR, exist_ok=True)

    for item in results:
        if item is None:
            continue
        ts_code, df = item
        ma_file = f"{MA_DIR}/{ts_code}.csv"
        df.to_csv(ma_file, index=False, float_format="%.2f")


def calculate_all_sma():
    """多进程计算所有股票均线"""
    stock_list = read_stock_list()
    stock_codes = stock_list['ts_code'].dropna().tolist()
    total = len(stock_codes)

    if total == 0:
        print("无有效股票可处理！")
        return

    print(f"待处理股票总数：{total}")

    start_time = time.time()

    # 自动检测CPU核心数
    cpu_count = multiprocessing.cpu_count()
    max_workers = max(1, cpu_count - 2)  # 留2个核心给系统

    results = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(calculate_sma_for_stock, code): code for code in stock_codes}

        for i, future in enumerate(as_completed(futures)):
            result = future.result()
            if result:
                results.append(result)

            if (i + 1) % 500 == 0:
                print(f"已处理: {i + 1}/{total}")

    # 批量写入
    batch_write_results(results)

    end_time = time.time()
    print(f"均线计算完成！共 {len(results)} 支，总耗时: {end_time - start_time:.2f} 秒")
    print(f"平均每支: {(end_time - start_time) / total:.4f} 秒")
