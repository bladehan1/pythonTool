def adjusted_kelly(p, b, c, s):
    """
    计算含交易手续费的修正凯利公式仓位比例

    参数:
    p (float): 胜率（0~1）
    b (float): 原始盈利时的收益率（如0.2表示20%）
    c (float): 原始亏损时的损失率（如0.1表示10%）
    s (float): 总手续费率（双向合计，如0.01表示1%）

    返回:
    float: 最佳仓位比例（如0.5表示50%），若策略不可行返回None
    """
    # 参数合法性检查
    if not (0 <= p <= 1):
        print("错误：胜率p需在0~1之间")
        return None
    if b <= 0 or c <= 0 or s < 0:
        print("错误：收益率b、亏损率c需>0，手续费率s需≥0")
        return None

    # 计算实际盈利和亏损率（扣除/增加手续费）
    b_adj = b - s  # 实际盈利收益率
    c_adj = c + s  # 实际亏损损失率

    # 检查分母是否为零
    if (b_adj * c_adj) <= 0:
        print("错误：调整后的b或c无效，可能导致除零或负风险")
        return None

    # 计算修正凯利值
    numerator = p * b_adj - (1 - p) * c_adj
    f = numerator / (b_adj * c_adj)

    # 策略可行性判断
    if f <= 0:
        print("警告：凯利值≤0，策略期望收益为负，不建议交易")
        return None
    elif f > 1:
        print("警告：凯利值>100%，需检查参数或采用半凯利策略（建议仓位={:.1%}）".format(f/2))
    else:
        print("建议仓位：{:.1%}".format(f))

    return f