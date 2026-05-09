"""
择股条件定义：所有筛选条件在此集中管理。
方便调参、添加新条件、禁用旧条件。
"""
import math
import os
import pandas as pd
from datetime import datetime
from .config import A_WINDOW, B_WINDOW, C_WINDOW, D_WINDOW, E_WINDOW, MA_DIR, SELECT_DIR


# ================== 条件参数工厂 ==================
def make_params():
    """创建条件参数字典（包含均线差值计算和斜率计算）"""
    return {
        # 均线差值：DIF0 = 当日, DIF1 = 前1日, DIF2 = 前2日 ...
        'DIF0_AB': lambda df: df['MA_A'].iloc[-1] - df['MA_B'].iloc[-1],
        'DIF0_BC': lambda df: df['MA_B'].iloc[-1] - df['MA_C'].iloc[-1],
        'DIF0_CD': lambda df: df['MA_C'].iloc[-1] - df['MA_D'].iloc[-1],
        'DIF0_DE': lambda df: df['MA_D'].iloc[-1] - df['MA_E'].iloc[-1],

        'DIF1_AB': lambda df: df['MA_A'].iloc[-2] - df['MA_B'].iloc[-2],
        'DIF1_BC': lambda df: df['MA_B'].iloc[-2] - df['MA_C'].iloc[-2],
        'DIF1_CD': lambda df: df['MA_C'].iloc[-2] - df['MA_D'].iloc[-2],
        'DIF1_DE': lambda df: df['MA_D'].iloc[-2] - df['MA_E'].iloc[-2],

        'DIF2_AB': lambda df: df['MA_A'].iloc[-3] - df['MA_B'].iloc[-3],
        'DIF2_BC': lambda df: df['MA_B'].iloc[-3] - df['MA_C'].iloc[-3],
        'DIF2_CD': lambda df: df['MA_C'].iloc[-3] - df['MA_D'].iloc[-3],
        'DIF2_DE': lambda df: df['MA_D'].iloc[-3] - df['MA_E'].iloc[-3],

        'DIF3_AB': lambda df: df['MA_A'].iloc[-4] - df['MA_B'].iloc[-4],
        'DIF3_BC': lambda df: df['MA_B'].iloc[-4] - df['MA_C'].iloc[-4],
        'DIF3_CD': lambda df: df['MA_C'].iloc[-4] - df['MA_D'].iloc[-4],
        'DIF3_DE': lambda df: df['MA_D'].iloc[-4] - df['MA_E'].iloc[-4],

        'DIF4_AB': lambda df: df['MA_A'].iloc[-5] - df['MA_B'].iloc[-5],
        'DIF4_BC': lambda df: df['MA_B'].iloc[-5] - df['MA_C'].iloc[-5],
        'DIF4_CD': lambda df: df['MA_C'].iloc[-5] - df['MA_D'].iloc[-5],
        'DIF4_DE': lambda df: df['MA_D'].iloc[-5] - df['MA_E'].iloc[-5],

        # MA_A斜率
        'slopeA_1': lambda df: df['MA_A'].iloc[-1] - df['MA_A'].iloc[-2],
        'slopeA_2': lambda df: df['MA_A'].iloc[-2] - df['MA_A'].iloc[-3],
        'slopeA_3': lambda df: df['MA_A'].iloc[-3] - df['MA_A'].iloc[-4],
    }


# ================== 筛选条件定义 ==================
def make_conditions(params):
    """创建所有筛选条件"""
    return {
        # ------------- 条件1: 花开富贵 -------------
        'flowers': lambda df: (
            # 当日：MA_A > MA_B > MA_C > MA_D
            params['DIF0_AB'](df) > 0 and params['DIF0_BC'](df) > 0 and params['DIF0_CD'](df) > 0
            # 当日：MA_A > MA_B
            and params['DIF0_AB'](df) > params['DIF0_BC'](df)
            # 前1日：MA倒序排列，但差值缩小
            and params['DIF1_AB'](df) > 0 and params['DIF1_BC'](df) > 0 and params['DIF1_CD'](df) > 0
            and params['DIF1_AB'](df) < params['DIF0_AB'](df)
            and params['DIF1_BC'](df) < params['DIF0_BC'](df)
            and params['DIF1_CD'](df) < params['DIF0_CD'](df)
            # 前2日：差值继续缩小
            and params['DIF2_AB'](df) > 0 and params['DIF2_BC'](df) > 0 and params['DIF2_CD'](df) > 0
            and params['DIF2_AB'](df) < params['DIF1_AB'](df)
            and params['DIF2_BC'](df) < params['DIF1_BC'](df)
            and params['DIF2_CD'](df) < params['DIF1_CD'](df)
            # 斜率加速
            and params['slopeA_1'](df) > params['slopeA_2'](df) > params['slopeA_3'](df)
            # 收红：收盘 > 开盘
            and df['close'].iloc[-1] > df['open'].iloc[-1]
            and df['close'].iloc[-2] > df['open'].iloc[-2]
            and df['close'].iloc[-3] > df['open'].iloc[-3]
        ),

        # ------------- 条件2: 金叉 -------------
        'golden': lambda df: (
            params['DIF0_AB'](df) > 0 and params['DIF0_BC'](df) > 0 and params['DIF0_CD'](df) > 0
            and params['DIF1_AB'](df) > 0 and params['DIF1_BC'](df) > 0 and params['DIF1_CD'](df) > 0
            and params['DIF1_AB'](df) < params['DIF0_AB'](df)
            and params['DIF2_AB'](df) > 0
            and params['DIF3_AB'](df) < 0  # 金叉形成点
            and params['slopeA_1'](df) > params['slopeA_2'](df) > params['slopeA_3'](df)
            and df['close'].iloc[-1] > df['open'].iloc[-1]
            and df['close'].iloc[-1] > df['close'].iloc[-2]
        ),

        # ------------- 条件3: 金叉变体 -------------
        'golden2': lambda df: (
            params['DIF0_AB'](df) > 0 and params['DIF0_BC'](df) > 0 and params['DIF0_CD'](df) > 0
            and params['DIF1_AB'](df) > 0 and params['DIF1_BC'](df) > 0 and params['DIF1_CD'](df) > 0
            and params['DIF2_AB'](df) < 0
            and params['slopeA_1'](df) > params['slopeA_2'](df) > params['slopeA_3'](df)
            and df['close'].iloc[-1] > df['open'].iloc[-1]
            and df['close'].iloc[-1] > df['close'].iloc[-2]
        ),

        # ------------- 条件4: 涨停板检测 -------------
        'bitBoard': lambda df: (
            df['close'].iloc[-1] == df['high'].iloc[-1]
            and round(df['close'].iloc[-1], 2) == round(df['close'].iloc[-2] * 1.1, 2)
            and df['close'].iloc[-1] > df['close'].iloc[-2]
        ),

        # ------------- 条件5: 兔子（放量突破） -------------
        'rabbit': lambda df: (
            df['close'].iloc[-1] > df['MA_A'].iloc[-1] * 1.05
            and df['close'].iloc[-1] > df['open'].iloc[-1]
            and df['vol'].iloc[-1] > df['vol_MA_B'].iloc[-1] * 1.05
        ),

        # ------------- 条件6: 连续上涨 -------------
        'sun': lambda df: (
            df['close'].iloc[-1] > df['open'].iloc[-1]
            and df['close'].iloc[-2] > df['open'].iloc[-2]
            and df['close'].iloc[-3] > df['open'].iloc[-3]
            and df['close'].iloc[-4] > df['open'].iloc[-4]
            and df['close'].iloc[-1] > df['close'].iloc[-2]
            and df['close'].iloc[-2] > df['close'].iloc[-3]
            and df['close'].iloc[-3] > df['close'].iloc[-4]
            and df['close'].iloc[-4] > df['close'].iloc[-5]
        ),

        # ------------- 条件7: 庄家吸筹（均线重叠） -------------
        'MakingChips': lambda df: (
            math.fabs(params['DIF0_AB'](df)) < 0.06
            and math.fabs(params['DIF0_BC'](df)) < 0.1
            and math.fabs(params['DIF0_AB'](df)) < 0.2
        ),
    }


# ================== 筛选执行 ==================
def check_single_stock(ts_code, condition_name, min_period=300):
    """
    检查单支股票是否满足指定条件

    Args:
        ts_code: 股票代码
        condition_name: 条件名称
        min_period: 最小数据量要求

    Returns:
        ts_code if matches, None otherwise
    """
    ma_file = f"{MA_DIR}/{ts_code}.csv"

    if not os.path.exists(ma_file):
        return None

    try:
        df = pd.read_csv(ma_file)
        if df.shape[0] < min_period:
            return None

        df = df.sort_values(by='trade_date', ascending=True)

        params = make_params()
        conditions = make_conditions(params)

        if condition_name not in conditions:
            print(f"未知条件: {condition_name}")
            return None

        if conditions[condition_name](df):
            return ts_code

    except Exception as e:
        print(f"检查股票 {ts_code} 出错: {e}")

    return None


def screen_all_stocks(condition_name):
    """
    多线程筛选所有股票

    Args:
        condition_name: 条件名称

    Returns:
        满足条件的股票代码列表
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from .stock_list import read_stock_list

    stock_list = read_stock_list()
    tasks = [row['ts_code'] for _, row in stock_list.iterrows()]

    results = []
    start_time = datetime.now()

    with ThreadPoolExecutor(max_workers=48) as executor:
        futures = {
            executor.submit(check_single_stock, code, condition_name): code
            for code in tasks
        }
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"筛选 [{condition_name}] 完成！满足条件: {len(results)} 支，耗时: {elapsed:.2f}秒")

    # 保存结果
    if results:
        save_results(results, condition_name)

    return results


def save_results(stock_codes, condition_name):
    """保存筛选结果到CSV"""
    today = datetime.now().strftime('%Y-%m-%d')
    folder = os.path.join(SELECT_DIR, today)
    os.makedirs(folder, exist_ok=True)

    from .stock_list import read_stock_list
    stock_list = read_stock_list()

    matched = stock_list[stock_list['ts_code'].isin(stock_codes)][['ts_code', 'name']]
    file_path = os.path.join(folder, f'{condition_name}.csv')
    matched.to_csv(file_path, index=False, encoding='utf-8-sig')
    print(f"结果已保存: {file_path}")
