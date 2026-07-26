import math
import config

def calc_percentile(sorted_list, percentile):
    n = len(sorted_list)
    if n == 0:
        return float('inf')
    idx = (n - 1) * percentile
    lower = int(math.floor(idx))
    upper = int(math.ceil(idx))
    if lower == upper:
        return sorted_list[lower]
    weight = idx - lower
    return sorted_list[lower] * (1 - weight) + sorted_list[upper] * weight

def smooth_value(old_val, new_val):
    return old_val + config.SMOOTH_FACTOR * (new_val - old_val)

def get_robust_peak(speed_buffer, window_peak, glitch_cut_ratio=0.1, min_continuous=3):
    if len(speed_buffer) < 5:
        return window_peak
    speeds = list(speed_buffer)
    sorted_speeds = sorted(speeds)

    high_speed_threshold = window_peak * 0.9
    continuous_high = 0
    max_continuous_high = 0
    for s in speeds:
        if s >= high_speed_threshold:
            continuous_high += 1
            max_continuous_high = max(max_continuous_high, continuous_high)
        else:
            continuous_high = 0
    if max_continuous_high >= min_continuous:
        return window_peak

    cut_count = max(1, int(len(speeds) * glitch_cut_ratio))
    filtered_speeds = sorted_speeds[:-cut_count]
    if len(filtered_speeds) == 0:
        robust_peak = sorted_speeds[0]
    else:
        robust_peak = filtered_speeds[-1]
        p90 = calc_percentile(filtered_speeds, 0.9)
        robust_peak = min(robust_peak, p90 * 1.05)

    robust_peak = max(robust_peak, window_peak * 0.5)
    robust_peak = min(robust_peak, window_peak)
    return robust_peak
