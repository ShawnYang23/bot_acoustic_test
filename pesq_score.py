import argparse
from scipy.io import wavfile
from pesq import pesq
from tabulate import tabulate

# 设置参数解析器
parser = argparse.ArgumentParser(description='PESQ score')
parser.add_argument("-r", "--ref", type=str, required=True, help='Reference audio file')
parser.add_argument("-d", "--deg", type=str, nargs='+', required=True, help='Degraded audio files (space-separated list)')
args = parser.parse_args()

# 读取参考音频
rate, ref = wavfile.read(args.ref)

# 初始化结果列表
results = []

# 遍历每个降级文件
for deg_file in args.deg:
    try:
        rate_deg, deg = wavfile.read(deg_file)
        
        # 确保采样率一致
        if rate != rate_deg:
            results.append([deg_file, "Sample rate mismatch", "-", "-"])
            continue

        # 截取到相同长度
        max_len = min(len(ref), len(deg))
        ref_trimmed = ref[:max_len]
        deg_trimmed = deg[:max_len]

        # 计算 PESQ 分数
        pesq_wb = pesq(rate, ref_trimmed, deg_trimmed, 'wb')
        pesq_nb = pesq(rate, ref_trimmed, deg_trimmed, 'nb')

        # 保存结果
        results.append([deg_file, "OK", f"{pesq_wb:.2f}", f"{pesq_nb:.2f}"])
    
    except Exception as e:
        results.append([deg_file, f"Error: {e}", "-", "-"])

# 打印表格
headers = ["File", "Status", "PESQ (Wideband)", "PESQ (Narrowband)"]
print(tabulate(results, headers=headers, tablefmt="grid"))
