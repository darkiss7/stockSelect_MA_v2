"""
公共工具函数：请求控制、交易日期获取、日志等。
"""
import time
import queue
import threading
from datetime import datetime
from .config import REQUEST_INTERVAL


# ================== 全局请求队列 ==================
_request_queue = queue.Queue()
_controller_started = False


def start_request_controller():
    """启动全局请求频率控制线程"""
    global _controller_started
    if _controller_started:
        return

    def _control():
        while True:
            while not _request_queue.full():
                _request_queue.put(None)
            time.sleep(1)

    t = threading.Thread(target=_control, daemon=True)
    t.start()
    _controller_started = True


def wait_for_request_slot():
    """获取请求令牌，阻塞等待"""
    _request_queue.get()
    time.sleep(REQUEST_INTERVAL)


# ================== 交易日期相关 ==================
_trade_date_cache = {}


def get_latest_trade_date(pro):
    """获取最新的交易日（带缓存）"""
    today = datetime.now().strftime('%Y%m%d')
    if today in _trade_date_cache:
        return _trade_date_cache[today]

    df = pro.trade_cal(exchange='', start_date='20250101', end_date=today, is_open=1)
    result = df.iloc[0]['cal_date']
    _trade_date_cache[today] = result
    return result


def get_recent_trade_dates(pro, n=4):
    """获取最近n个交易日"""
    today = datetime.now().strftime('%Y%m%d')
    df = pro.trade_cal(exchange='', start_date='20240101', end_date=today, is_open=1)
    return list(df['cal_date'][0:n])
