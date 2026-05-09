"""
股票列表管理：下载、更新、读取。
"""
import pandas as pd
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from .config import STOCK_LIST_FILE, MAX_WORKERS_FETCH, REQUEST_INTERVAL
from .utils import get_recent_trade_dates


def get_stock_list(pro):
    """下载A股所有股票列表"""
    df = pro.stock_basic(
        exchange='',
        list_status='L',
        fields='ts_code,symbol,market,name,industry,list_status'
    )
    df.to_csv(STOCK_LIST_FILE, index=False, encoding='utf-8-sig')
    return df


def read_stock_list(filename=None):
    """读取股票列表，只返回主板股票"""
    if filename is None:
        filename = STOCK_LIST_FILE
    df = pd.read_csv(filename)
    main_board = df[df['market'] == '主板'].reset_index(drop=True)
    return main_board


def check_single_stock_status(ts_code, recent_days, pro):
    """检查单支股票是否有最近n日交易数据"""
    try:
        time.sleep(REQUEST_INTERVAL)
        data = pro.daily(ts_code=ts_code, start_date=recent_days[-1], end_date=recent_days[0])
        return ts_code, (data.shape[0] >= len(recent_days))
    except Exception as e:
        print(f"检查股票 {ts_code} 状态时出错：{e}")
        return ts_code, False


def update_stock_list(pro):
    """多线程检查股票状态，剔除停牌股票"""
    stock_list = read_stock_list()
    recent_days = get_recent_trade_dates(pro, n=4)

    active_stocks = []
    start_time = datetime.now()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS_FETCH) as executor:
        futures = {
            executor.submit(check_single_stock_status, row['ts_code'], recent_days, pro)
            for _, row in stock_list.iterrows()
        }
        for future in as_completed(futures):
            ts_code, is_active = future.result()
            if is_active:
                active_stocks.append(ts_code)

    # 更新文件
    if active_stocks:
        updated_df = stock_list[stock_list['ts_code'].isin(active_stocks)]
        updated_df.to_csv(STOCK_LIST_FILE, index=False, encoding='utf-8-sig')

    print(f"更新完成！有效股票: {len(active_stocks)}，耗时: {datetime.now() - start_time}")
    return len(active_stocks)


def get_active_stock_count():
    """获取当前有效股票数量"""
    try:
        df = read_stock_list()
        return len(df)
    except:
        return 0
