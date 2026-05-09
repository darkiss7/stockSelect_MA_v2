"""
数据获取：实时行情、日线数据下载。
"""
import pandas as pd
import time
import tushare as ts
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from .config import MAX_WORKERS_FETCH, REQUEST_INTERVAL, MA_DIR, DATA_DIR, TUSHARE_API_TOKEN
from .utils import wait_for_request_slot, get_latest_trade_date


def fetch_realtime_batch(stock_codes):
    """批量获取实时行情（新浪接口）"""
    try:
        codes_str = ",".join(stock_codes)
        time.sleep(REQUEST_INTERVAL)
        # 注意：必须用 ts.realtime_quote()，不能用 pro.realtime_quote()
        # pro 不支持批量查询
        df = ts.realtime_quote(ts_code=codes_str)
        return df
    except Exception as e:
        print(f"批量获取实时数据出错: {e}")
        return pd.DataFrame()


def fetch_all_realtime(stock_list, batch_size=870):
    """获取所有股票实时行情"""
    stock_codes = stock_list['ts_code'].tolist()
    all_data = pd.DataFrame()

    start_time = datetime.now()
    for i in range(0, len(stock_codes), batch_size):
        batch = stock_codes[i:i + batch_size]
        df = fetch_realtime_batch(batch)
        if not df.empty:
            all_data = pd.concat([all_data, df], ignore_index=True)

    print(f"下载实时行情用时：{(datetime.now() - start_time).total_seconds():.2f} 秒")

    output_file = 'all_realtime_stock_data.csv'
    all_data.to_csv(output_file, index=False, encoding='utf-8-sig')
    return all_data


def download_daily_for_stock(ts_code, start_date, pro):
    """下载单支股票日线数据"""
    try:
        wait_for_request_slot()
        df = pro.daily(ts_code=ts_code, start_date=start_date)
        return df
    except Exception as e:
        print(f"下载 {ts_code} 数据出错: {e}")
        return pd.DataFrame()


def update_stock_daily_file(ts_code, latest_date, pro):
    """更新单支股票日线数据文件"""
    file_path = f"{DATA_DIR}/{ts_code}.csv"

    # 读取现有数据
    if not pd.io.common.file_exists(file_path):
        return False

    df = pd.read_csv(file_path)

    # 删除最后一行空行
    if not df.empty and df.iloc[-1].isna().any():
        df = df.iloc[:-1]

    if df.empty:
        existing_max = '20230901'
    else:
        existing_dates = df['trade_date'].unique()
        existing_max = str(max(existing_dates))

    # 计算缺失日期
    date_range = pd.date_range(start=existing_max, end=latest_date, freq='B')
    existing_dates_set = set(pd.to_datetime(df['trade_date'].astype(str), format='%Y%m%d').date)
    missing_dates = [
        d.strftime('%Y%m%d') for d in date_range
        if d.date() not in existing_dates_set
    ]

    if not missing_dates:
        return False

    # 下载并合并
    new_data = download_daily_for_stock(ts_code, missing_dates[0], pro)
    if not new_data.empty:
        df = pd.concat([df, new_data], ignore_index=True)
        df = df.drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')
        df = df.sort_values(by=['ts_code', 'trade_date']).reset_index(drop=True)
        df.to_csv(file_path, index=False)
        return True

    return False


def update_all_daily(stock_list, pro):
    """多线程更新所有股票日线数据"""
    latest_date = get_latest_trade_date(pro)
    print(f"最新交易日期：{latest_date}")

    from concurrent.futures import ThreadPoolExecutor

    tasks = [(row['ts_code'], latest_date, pro) for _, row in stock_list.iterrows()]

    start = time.time()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS_FETCH) as executor:
        results = list(executor.map(lambda t: update_stock_daily_file(*t), tasks))
    end = time.time()

    updated_count = sum(1 for r in results if r)
    print(f"日线数据更新完成！更新: {updated_count} 支，耗时: {end - start:.2f} 秒")
