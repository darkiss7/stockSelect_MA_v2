"""
Configuration for MA-based stock selection system.
所有参数集中管理，方便调参。
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ================== API配置 ==================
TUSHARE_API_TOKEN = os.getenv('Tushare_API_Token')

# ================== 路径配置 ==================
# stockSelect_MA_v2/src/ 的父目录是 stockSelect_MA_v2/
# stockSelect_MA_v2/ 的父目录是 Astock/
# 所以从 src/config.py 出发，需要向上3层到达 Astock/
THIS_DIR = os.path.dirname(os.path.abspath(__file__))  # src/
V2_DIR = os.path.dirname(THIS_DIR)                     # stockSelect_MA_v2/
ASTOCK_DIR = os.path.dirname(V2_DIR)                    # Astock/

# 数据目录 (Astock/ 下)
DATA_DIR = os.path.join(ASTOCK_DIR, 'A股日线数据')
MA_DIR = os.path.join(ASTOCK_DIR, 'A股日均线数据')
SELECT_DIR = os.path.join(ASTOCK_DIR, 'A股选股数据')
# 股票列表 (在 stockSelect_MA/ 目录下，与v2平行)
STOCK_LIST_FILE = os.path.join(ASTOCK_DIR, 'stockSelect_MA', 'stock_live_list.csv')

# ================== 均线周期配置 ==================
A_WINDOW = 3    # 3日均线
B_WINDOW = 5    # 5日均线
C_WINDOW = 10   # 10日均线
D_WINDOW = 20   # 20日均线
E_WINDOW = 30   # 30日均线

# ================== 请求频率控制 ==================
MAX_REQUESTS_PER_SECOND = 700 // 60  # 每秒最大请求数
REQUEST_INTERVAL = 0.5  # 每次请求间隔(秒)

# ================== 多线程配置 ==================
MAX_WORKERS_FETCH = 48   # 数据获取线程数
MAX_WORKERS_CALC = 48    # 计算线程数

# ================== 择股条件列表 ==================
SELECTOR_CONDITIONS = ['MakingChips', 'bitBoard', 'golden', 'golden2', 'rabbit', 'sun', 'flowers']

# ================== 数据更新模式 ==================
# True: 盘中实时更新
# False: 盘后一次性更新
RUN_REALTIME = True
DATA_UPDATED = False  # True: 直接计算不更新数据
