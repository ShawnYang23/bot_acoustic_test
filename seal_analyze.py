import argparse
import numpy as np
import librosa
import librosa.display
import matplotlib.pyplot as plt
from scipy.signal import welch

# Load multi-channel audio
def load_multichannel_audio(file_path):
    y, sr = librosa.load(file_path, sr=None, mono=False)  # Load multi-channel audio
    return y, sr

# Compute RMS
def compute_rms(y):
    return np.sqrt(np.mean(y**2))

# Compute Power Spectral Density (PSD)
def compute_psd(y, sr):
    freqs, psd = welch(y, fs=sr, nperseg=1024)
    return freqs, psd

# Compute Frequency Spectrum (FFT)
def compute_fft(y, sr):
    fft_spectrum = np.abs(np.fft.rfft(y))
    freqs = np.fft.rfftfreq(len(y), 1/sr)
    return freqs, fft_spectrum

# Plot all channels in a single figure and save as image
def plot_all_channels(freqs_fft, fft_unsealed, fft_sealed, freqs_psd, psd_unsealed, psd_sealed, output_img="result.png"):
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))  # 2 rows, 3 columns

    for ch in range(6):
        ax = axes[ch // 3, ch % 3]  # Select subplot position

        # Plot FFT comparison
        ax.plot(freqs_fft[ch], fft_unsealed[ch], label="Unsealed FFT", alpha=0.7, linestyle="--")
        ax.plot(freqs_fft[ch], fft_sealed[ch], label="Sealed FFT", alpha=0.7)

        # Plot PSD comparison
        ax.plot(freqs_psd[ch], psd_unsealed[ch], label="Unsealed PSD", alpha=0.7, linestyle=":")
        ax.plot(freqs_psd[ch], psd_sealed[ch], label="Sealed PSD", alpha=0.7)

        ax.set_title(f"Channel {ch+1}")
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Amplitude / PSD")
        ax.legend()

    plt.tight_layout()
    plt.savefig(output_img)  # Save figure instead of displaying
    plt.close()
    print(f"📷 Result image saved: {output_img}")

# Main analysis function
def audio_analyzing(unsealed_file, sealed_file):
    y1, sr1 = load_multichannel_audio(unsealed_file)
    y2, sr2 = load_multichannel_audio(sealed_file)

    num_channels = min(y1.shape[0], y2.shape[0])  # Use the minimum channel count to avoid mismatches

    # Use only the first 6 microphone channels, reserve the 8th channel for loopback
    y1 = y1[:6]
    y2 = y2[:6]

    rms_changes = []
    freqs_fft, fft_unsealed, fft_sealed = [], [], []
    freqs_psd, psd_unsealed, psd_sealed = [], [], []

    # Open result file for writing
    with open("result.txt", "w") as f:
        f.write("Audio Sealing Analysis Results\n")
        f.write("=" * 40 + "\n")

        for ch in range(num_channels):
            # Compute RMS
            rms1, rms2 = compute_rms(y1[ch]), compute_rms(y2[ch])
            rms_change = (rms1 - rms2) / rms1 * 100  # Compute RMS reduction percentage
            rms_changes.append(rms_change)

            # Write channel RMS data to file
            f.write(f"Channel {ch+1}:\n")
            f.write(f"  - Unsealed RMS: {rms1:.4f}, Sealed RMS: {rms2:.4f}, Reduction: {rms_change:.2f}%\n")

            # Compute PSD and FFT
            f_psd, p_unsealed = compute_psd(y1[ch], sr1)
            _, p_sealed = compute_psd(y2[ch], sr2)

            f_fft, f_unsealed = compute_fft(y1[ch], sr1)
            _, f_sealed = compute_fft(y2[ch], sr2)

            # Store data for plotting
            freqs_psd.append(f_psd)
            psd_unsealed.append(p_unsealed)
            psd_sealed.append(p_sealed)

            freqs_fft.append(f_fft)
            fft_unsealed.append(f_unsealed)
            fft_sealed.append(f_sealed)

        # Overall analysis
        avg_rms_change = np.mean(rms_changes)
        f.write("\nOverall Analysis:\n")
        f.write(f"  - Average RMS reduction: {avg_rms_change:.2f}% (Higher value indicates better sealing performance)\n")

    print("📄 Analysis results saved to result.txt")

    # Plot and save comparison image
    plot_all_channels(freqs_fft, fft_unsealed, fft_sealed, freqs_psd, psd_unsealed, psd_sealed)

# Command-line argument parsing
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare audio parameters before and after sealing to evaluate airtightness.")
    parser.add_argument("-u", "--unsealed", type=str, required=True, help="Path to the unsealed recording file")
    parser.add_argument("-s", "--sealed", type=str, required=True, help="Path to the sealed recording file")

    args = parser.parse_args()
    
    audio_analyzing(args.unsealed, args.sealed)
