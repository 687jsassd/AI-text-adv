"""
token分析
"""
# Copyright (c) 2025 [687jsassd]
# MIT License


def analyze_token_consume(token_consumes: list):
    """
    分析游戏过程中token消耗趋势
    """
    # 获取总轮数
    total_rounds = len(token_consumes)

    # 存储结果
    results = []

    # 从10轮开始，每10轮作为一个区间，直到总轮数
    for interval_end in range(10, total_rounds + 1, 10):
        # 计算当前区间(1到interval_end轮)的平均token消耗
        rounds_data = token_consumes[:interval_end]
        avg_consume = sum(rounds_data) / interval_end

        # 为简单线性回归准备数据
        x_vals = list(range(1, interval_end + 1))
        y_vals = token_consumes[:interval_end]

        # 简单线性回归（最小二乘法）
        n = interval_end
        sum_x = sum(x_vals)
        sum_y = sum(y_vals)
        sum_xy = sum(x * y for x, y in zip(x_vals, y_vals))
        sum_x2 = sum(x * x for x in x_vals)

        # 计算斜率和截距
        if n * sum_x2 - sum_x * sum_x != 0:
            slope = (n * sum_xy - sum_x * sum_y) / \
                (n * sum_x2 - sum_x * sum_x)
            intercept = (sum_y - slope * sum_x) / n
        else:
            slope = 0
            intercept = avg_consume

        # 保存结果
        results.append({
            'rounds': interval_end,
            'avg_consume': avg_consume,
            'slope': slope,
            'intercept': intercept
        })

    # 如果总轮数不是10的倍数，添加最后一个区间
    if total_rounds % 10 != 0:
        rounds_data = token_consumes[:total_rounds]
        avg_consume = sum(rounds_data) / total_rounds

        x_vals = list(range(1, total_rounds + 1))
        y_vals = token_consumes[:total_rounds]

        n = total_rounds
        sum_x = sum(x_vals)
        sum_y = sum(y_vals)
        sum_xy = sum(x * y for x, y in zip(x_vals, y_vals))
        sum_x2 = sum(x * x for x in x_vals)

        if n * sum_x2 - sum_x * sum_x != 0:
            slope = (n * sum_xy - sum_x * sum_y) / \
                (n * sum_x2 - sum_x * sum_x)
            intercept = (sum_y - slope * sum_x) / n
        else:
            slope = 0
            intercept = avg_consume

        results.append({
            'rounds': total_rounds,
            'avg_consume': avg_consume,
            'slope': slope,
            'intercept': intercept
        })

    # 输出结果
    for result in results:
        rounds = result['rounds']
        avg = result['avg_consume']
        slope = result['slope']
        intercept = result['intercept']

        print(f"1-{rounds}轮:")
        print(f"  平均token消耗: {avg:.2f}")
        print(f"  拟合直线: y = {slope:.4f}x + {intercept:.4f}")
        print(f"  预测下一轮消耗: {slope * (rounds + 1) + intercept:.2f}")
        print()
    input('按任意键继续')
