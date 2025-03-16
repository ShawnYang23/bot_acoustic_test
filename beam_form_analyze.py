import argparse
import numpy as np
import librosa
import librosa.display
from scipy.signal import correlate
import matplotlib.pyplot as plt
from tabulate import tabulate

DR = []
MZC = []
NCC = []
SNR = [0]
RMES = [0]
def amp_dynamic_range_analysis(ref, procs):
    # 良好收束：峰值降低但 RMS 变化不大，动态范围保持适中。
    # 过度收束：RMS 下降过多，动态范围显著缩小，导致音频失去层次感。
    rms_ref = librosa.feature.rms(y=ref)
    rms_procs = [librosa.feature.rms(y=proc) for proc in procs]

    #  calculate dynamic range
    dynamic_range_ref = np.max(rms_ref) - np.min(rms_ref)
    dynamic_range_procs = [np.max(rms) - np.min(rms) for rms in rms_procs]
    DR.append(dynamic_range_ref)
    DR.extend(dynamic_range_procs)
def spectrum_analysis(ref, procs):
    # 良好收束：频谱整体形态变化不大，仅在极端振幅处有所平滑。
    # 过度收束：高频或某些关键频率成分削弱过多，导致音质下降。
    # plot spectrum
    stft_ref = np.abs(librosa.stft(ref))
    stft_procs = [np.abs(librosa.stft(proc)) for proc in procs]
    nums = len(stft_procs) + 1
    fig, axs = plt.subplots(nums, 1, figsize=(10, 10))
    librosa.display.specshow(librosa.amplitude_to_db(stft_ref, ref=np.max),
                               ax=axs[0], y_axis='log', x_axis='time')
    axs[0].set_title('Reference')
    for i, stft in enumerate(stft_procs):
        librosa.display.specshow(librosa.amplitude_to_db(stft, ref=np.max),
                                   ax=axs[i+1], y_axis='log', x_axis='time')
        axs[i+1].set_title(f'Processed {i}')
    plt.tight_layout()
    plt.show()

def zero_crossing_rate_analysis(ref, procs):
    # 良好收束：ZCR 降低但不过分，仍保持一定的高频信息。
    # 过度收束：ZCR 下降过多，导致音频变闷、细节缺失。
    zcr_ref = librosa.feature.zero_crossing_rate(y=ref)
    zcr_procs = [librosa.feature.zero_crossing_rate(y=proc) for proc in procs]

    #  calculate zero crossing rate
    mean_zcr_ref = np.mean(zcr_ref)
    mean_zcr_procs = [np.mean(zcr) for zcr in zcr_procs]

    MZC.append(mean_zcr_ref)
    MZC.extend(mean_zcr_procs)

def ncc_analysis(ref, procs):
    # NCC > 0.95：良好收束，基本无失真。
    # 0.8 < NCC < 0.95：轻微变化，可接受。
    # NCC < 0.8：可能失真较严重。
    def normalized_cross_correlation(x, y):
        x = (x - np.mean(x)) / (np.std(x) + 1e-10)
        y = (y - np.mean(y)) / (np.std(y) + 1e-10)
        return np.max(correlate(x, y, mode='full')) / len(x)
    ncc_ref = normalized_cross_correlation(ref, ref)
    ncc_procs = [normalized_cross_correlation(ref, proc) for proc in procs] 
    NCC.append(ncc_ref)
    NCC.extend(ncc_procs)
    
def snr_calculation(ref, procs):
    noise = [ref - proc for proc in procs]
    snr = [10 * np.log10(np.sum(ref**2) / np.sum(n**2)) for n in noise]
    SNR.extend(snr)

def rmes_calculation(ref, procs):
    rmes = [np.sqrt(np.mean((ref - proc)**2)) for proc in procs]
    RMES.extend(rmes)
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="analyze beamforming results of audio files")
    parser.add_argument("-r", "--ref", type=str,
                        required=True, help='Reference audio file')
    parser.add_argument("-p", "--processed", type=str,
                        nargs='+', required=True, help='Processed audio files')

    args = parser.parse_args()
    procs = []
    ref, sr = librosa.load(args.ref, sr=None)
    for proc in args.processed:
        proc, sr = librosa.load(proc, sr=None)
        procs.append(proc)
    #align the length of all audio files
    min_len = min(len(ref), *[len(proc) for proc in procs])
    ref = ref[:min_len]
    procs = [proc[:min_len] for proc in procs]
    
    snr_calculation(ref, procs)
    rmes_calculation(ref, procs)
    amp_dynamic_range_analysis(ref, procs)
    spectrum_analysis(ref, procs)
    zero_crossing_rate_analysis(ref, procs)
    ncc_analysis(ref, procs)

    # 打印表格
    headers = ["File", "SNR", "RMES", "Dynamic Range", "ZCR", "NCC"]
    table = []
    table.append(["Reference", SNR[0], RMES[0], DR[0], MZC[0], NCC[0]])
    for i, proc in enumerate(procs):
        table.append([args.processed[i], SNR[i+1], RMES[i+1], DR[i+1], MZC[i+1], NCC[i+1]])
    print(tabulate(table, headers=headers, tablefmt="grid"))
    