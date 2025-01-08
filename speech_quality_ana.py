import numpy as np
import scipy.io.wavfile as wav
import matplotlib.pyplot as plt
import argparse


def read_wav_file(file_path):
    """读取wav文件并返回采样率和音频数据"""
    rate, data = wav.read(file_path)
    print(f"Data type: {data.dtype}")
    if data.ndim > 1:
        # read only the first channel
        data = data[:, 0]
    return rate, data


def calculate_rms(signal):
    """计算信号的均方根 (RMS) 值"""
    return np.sqrt(np.mean(np.square(signal)))

def apply_gain(signal, gain):
    return np.clip(signal * gain, -32768, 32767).astype(np.int16)

def time_align_via_cross_correlation(ref_signal, target_signal):
    """
    使用互相关法对齐两个信号，返回对齐后的目标信号。
    ref_signal: 参考信号（纯净音频）
    target_signal: 需要对齐的目标信号（带噪音录制音频）
    """
    # # 计算互相关
    # correlation = np.correlate(target_signal, ref_signal, mode='full')
    # lag = np.argmax(correlation)

    # print(f"Estimated time lag: {lag} samples")

    # # 对目标信号进行裁剪或填充以对齐时间
    # if lag > 0:
    #     aligned_signal = target_signal[lag:]  # 去掉前面多余的部分
    # elif lag < 0:
    #     aligned_signal = np.pad(target_signal, (abs(lag), 0), mode='constant')  # 前面填充0
    # else:
    #     aligned_signal = target_signal  # 无需对齐

    # 确保两信号长度一致
    aligned_signal = target_signal
    min_length = min(len(ref_signal), len(aligned_signal))
    return ref_signal[:min_length], aligned_signal[:min_length]

def calculate_snr(signal, speech_with_noise):
    """计算信噪比 (SNR)"""
    signal_rms = calculate_rms(signal)
    total_rms = calculate_rms(speech_with_noise)
    noise_rms = np.sqrt(total_rms**2 - signal_rms**2)
    return 20 * np.log10(signal_rms / noise_rms)

def calc_match_gain(src, dst, threshold):
    sum_src = 0
    ave_src = 0
    sum_dst = 0
    ave_dst = 0
    for i in range(len(src)):
        if(np.abs(src[i]) > threshold):
            sum_src += dst[i] / src[i]
            ave_src += 1
    ave_src = sum_src / ave_src
    for i in range(len(dst)):
        if(np.abs(dst[i]) > threshold):
            sum_dst += dst[i]
            ave_dst += 1
    ave_dst = sum_dst / ave_dst
    return ave_dst/ave_src

def plot_waveforms(pure_signal, noise_signal, rate, name):
    # 计算语音信号的RMS
    speech_rms = calculate_rms(pure_signal)
    print(f"Speech RMS: {speech_rms:.4f}")
    # 计算底噪（噪音RMS）
    gain = calc_match_gain(noise_signal, pure_signal, 0.003)
    noise_signal = apply_gain(noise_signal, gain)
    speech_with_noise_rms = calculate_rms(noise_signal) 
    print(f"SWN RMS: {speech_with_noise_rms:.4f}")
    noise_rms = np.sqrt(speech_with_noise_rms**2 - speech_rms**2)
    print(f"Noise RMS: {noise_rms:.4f}")
    # 计算信噪比 (SNR)
    snr = calculate_snr(pure_signal, noise_signal)
    print(f"Signal-to-Noise Ratio (SNR): {snr:.2f} dB")
    #plot the waveforms and spectrogram of the speech signal and the noise signal
    time_axis = np.arange(0, len(pure_signal)) / rate
    plt.figure()
    plt.subplot(4, 1, 1)
    plt.plot(time_axis, pure_signal, label=f"Speech Signal RMS: {speech_rms:.4f} dB")
    plt.legend()
    plt.subplot(4, 1, 2)
    plt.plot(time_axis, noise_signal, label=f"{name} RMS: {noise_rms:.4f} dB")
    plt.legend()
    plt.subplot(4, 1, 3)
    plt.specgram(pure_signal, Fs=rate)
    plt.title(f"Speech Signal Spectrogram")
    
    #add speech rms value to the plot

    plt.subplot(4, 1, 4)
    plt.specgram(noise_signal, Fs=rate)
    plt.title(f"{name} Spectrogram (SNR: {snr:.2f} dB)")
    plt.show()
    figure_name = f"{name}.png"
    plt.savefig(figure_name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--speech_file", type=str,
                        required=True, help="The speech audio file")
    parser.add_argument("-n", "--noise_file", type=str,
                        required=True, help="The noise audio file")
    args = parser.parse_args()
    # 读取文件
    rate_signal, speech_signal = read_wav_file(args.speech_file)
    rate_noise, speech_with_noise = read_wav_file(args.noise_file)

    if rate_signal != rate_noise:
        raise ValueError(
            "The two audio files must have the same sampling rate!")

    # 裁剪长度一致
    align_ssig, align_snsig = time_align_via_cross_correlation(speech_signal, speech_with_noise)

    # 绘制波形
    name = args.noise_file.split('/')[-1].split('.')[0]
    plot_waveforms(align_ssig, align_snsig, rate_signal, name)
    


if __name__ == "__main__":
    main()
