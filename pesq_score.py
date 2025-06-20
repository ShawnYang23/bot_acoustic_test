import os
import numpy as np
from scipy.io import wavfile
from scipy import signal
from pesq import pesq
from tabulate import tabulate

class PesqScore:
    def __init__(self, bw="auto"):
        """
        bw: "nb" is narrowband (8kHz), "wb" is wideband (16kHz), "auto" decides based on sample rate.
        """
        self.bw = bw
        self.tor_sec = 1  # tolerance in seconds for alignment
        self.mics = 6
        self.cache_dir = "./cache/"
        self.pesq_def_path = self.cache_dir + "pesq_results.csv"
        self.snr_def_path = self.cache_dir + "snr_results.csv"

    def _find_best_offset(self, ref_signal, deg_signal):
        """
        Calculate the best offset between reference and degraded audio signals.
        Uses cross-correlation to find the optimal alignment.
        ref_signal: Reference audio signal (numpy array).
        deg_signal: Degraded audio signal (numpy array).
        Returns the offset in samples.
        """
        corr = signal.correlate(deg_signal, ref_signal, mode='full')
        max_idx = np.argmax(corr)
        offset = max_idx - (len(ref_signal) - 1)
        return offset

    def _resample_signal(self, signal_data, orig_rate, target_rate):
        """
        Resample the input signal data from orig_rate to target_rate.
        signal_data: Input audio signal data (numpy array).
        orig_rate: Original sample rate of the signal.
        target_rate: Desired sample rate to resample to.
        """
        if orig_rate == target_rate:
            return signal_data
        from math import gcd
        g = gcd(orig_rate, target_rate)
        up = target_rate // g
        down = orig_rate // g
        try:
            resampled = signal.resample_poly(signal_data, up, down)
        except Exception as e:
            print(f"Resample error (using FFT method as fallback): {e}")
            num_samples = int(len(signal_data) * target_rate / orig_rate)
            resampled = signal.resample(signal_data, num_samples)
        return resampled.astype(np.float32)

    @staticmethod
    def get_file_list(*paths):
        """ get all .wav files from given paths, excluding 'aligned_' prefixed files. """
        file_list = []
        for path in paths:
            print(f"Processing path: {path}")
            if os.path.isdir(path):
                for item in os.listdir(path):
                    full_path = os.path.join(path, item)
                    if os.path.isfile(full_path) and full_path.lower().endswith('.wav') \
                       and 'aligned_' not in os.path.basename(full_path):
                        file_list.append(full_path)
            elif os.path.isfile(path) and path.lower().endswith('.wav'):
                if 'aligned_' not in os.path.basename(path):
                    file_list.append(path)
        return file_list
    
    def normalize_audio(self, deg_file, ref_data, ref_rate):
        if len(ref_data) == 0:
            raise ValueError("Reference audio data is empty.")
        
        try:
            deg_rate, deg_data = wavfile.read(deg_file)
        except Exception as e:
            status = f"Read error: {e}"
            return deg_file, status, []
        deg_data = deg_data.astype(np.float32)
        # 0. check channel number
        if deg_data.ndim > 2:
            status = "Invalid audio file"
            return deg_file, status, []
        if deg_data.ndim == 2:
            if deg_data.shape[1] >= self.mics:
                # average fist mics channels
                deg_data = np.mean(deg_data[:, :self.mics], axis=1)
                print(f"[Warn]: Using first {self.mics} channels for averaging.")
            else:
                # take the first channel
                print(f"[Warn]: Using the first channel for {deg_file}.")
                deg_data = deg_data[:, 0]

        # 1. Algin sample rates based on reference audio
        if deg_rate != ref_rate:
            deg_data = self._resample_signal(deg_data, deg_rate, ref_rate)
            deg_rate = ref_rate

        # deg_data must be greater than ref_data in length
        if len(deg_data) < len(ref_data) - self.tor_sec * ref_rate:
            status = "Record file short"
            return deg_file, status, []

        # 2. Align lengths(time) of reference and degraded audio
        offset = self._find_best_offset(ref_data, deg_data)
        if offset > 0:
            # Record too early, need to trim the beginning of deg_data
            deg_data = deg_data[int(offset):]
        elif offset < 0:
            # Record too late to include the full reference audio
            if offset > -self.tor_sec * ref_rate:
                ref_data = ref_data[-int(offset):]
            else:
                status = "Record too late"
                return deg_file, status, []

        if len(ref_data) > len(deg_data):
            status = "Record short tail"
            return deg_file, status, []
        
        # Trim to match reference length
        deg_data = deg_data[:len(ref_data)] 
        if len(ref_data) > 0:
            cur_ref_rms = np.sqrt(np.mean(ref_data**2))
            deg_rms = np.sqrt(np.mean(deg_data**2))
        else:
            status = "Empty tailored audio"
            return deg_file, status, []

        # 3. Align RMS levels of reference and degraded audio
        if cur_ref_rms <= 0 or deg_rms <= 0:
            status = "RMS zero"
            return deg_file, status, []
        
        gain = cur_ref_rms / deg_rms
        deg_data *= gain  

        #save aligned degraded audio for debugging
        aligned_deg_file = f"aligned_{os.path.basename(deg_file)}"
        aligned_deg_path = os.path.join(self.cache_dir, aligned_deg_file)
        try:
            wavfile.write(aligned_deg_path, deg_rate, deg_data.astype(np.int16))
            print(f"Aligned degraded audio saved to: {aligned_deg_path}")
        except Exception as e:
            print(f"Warning: Could not save aligned degraded audio due to error: {e}")

        return aligned_deg_file, "OK", deg_data

    def pesq_calc(self, ref_file, deg_files, output_csv=None):
        # Read audio file
        ref_rate, ref_data = wavfile.read(ref_file)
        ref_data = ref_data.astype(np.float32)
        if isinstance(deg_files, str):
            deg_files = [deg_files]
        deg_list = self.get_file_list(*deg_files)

        # Determine PESQ mode and reference rate
        if self.bw == "auto":
            if ref_rate > 8000:
                ref_rate = 16000
                mode = 'wb'
            else:
                ref_rate = 8000
                mode = 'nb'
        else:
            mode = self.bw.lower()
            ref_rate = 16000 if mode == 'wb' else 8000
        
        if ref_rate not in [8000, 16000]:
            raise ValueError("Reference audio rate must be either 8000Hz or 16000Hz.")
        
        results = []  
        for deg_file in deg_list:
            # Normalize audio rate, channel, length, and RMS levels
            aligned_deg_file, status, deg_data = self.normalize_audio(deg_file, ref_data, ref_rate)
            if len(deg_data) <= 1:
                results.append([deg_file, status, "N/A"])
                continue
            
            # PESQ calculation
            try:
                pesq_val = pesq(ref_rate, ref_data, deg_data, mode)
                pesq_score = f"{pesq_val:.2f}"
            except Exception as e:
                status = f"PESQ error: {e}"

            results.append([aligned_deg_file, status, pesq_score])

        # print results in a table format
        headers = ["File", "Status", f"PESQ ({mode.upper()})"]
        print(tabulate(results, headers=headers, tablefmt="grid"))

        # save results to CSV
        csv_text = tabulate(results, headers=headers, tablefmt="csv")
        output_path = output_csv if output_csv else self.pesq_def_path
        try:
            rw_mode = 'w' if output_path != self.pesq_def_path else 'a'
            with open(output_path, rw_mode, encoding="utf-8", newline="") as f:
                f.write(f"# Timestamp: {np.datetime64('now')}\n")
                f.write(csv_text)
                f.write("\n\n")
            print(f"\nResults have been saved to {output_path}")
        except Exception as e:
            print(f"\nWarning: Could not save CSV file due to error: {e}")

    def snr_calc(self, ref_file, deg_files, seg_frame_ms=10, output_csv=None):
        """
        Calculate SNR (Signal-to-Noise Ratio) for degraded audio files against a reference file.
        ref_file: Reference audio WAV file.
        deg_files: List of degraded audio files or directory containing them.
        output_csv: Path to save the results in CSV format.
        """
        ref_rate, ref_data = wavfile.read(ref_file)
        ref_data = ref_data.astype(np.float32)
        
        if isinstance(deg_files, str):
            deg_files = [deg_files]
        deg_list = self.get_file_list(*deg_files)

        results = []
        for deg_file in deg_list:
            aligned_deg_file, status, deg_data = self.normalize_audio(deg_file, ref_data, ref_rate)
            if status != "OK":
                results.append([deg_file, status, "N/A", f"{seg_frame_ms}"])
                continue
            # calculate SNR
            if seg_frame_ms > 0:
                frame_size = int(ref_rate * seg_frame_ms / 1000)
                if len(deg_data) < frame_size or len(ref_data) < frame_size:
                    results.append([deg_file, "Frame size too large", "N/A", f"{seg_frame_ms}"])
                    continue
                # Calculate SNR for each frame
                snr_values = []
                for start in range(0, len(deg_data) - frame_size + 1, frame_size):
                    ref_frame = ref_data[start:start + frame_size]
                    deg_frame = deg_data[start:start + frame_size]
                    if len(ref_frame) == 0 or len(deg_frame) == 0:
                        continue
                    noise = deg_frame - ref_frame
                    if np.sum(noise**2) == 0:
                        snr_value = float('inf')
                    else:
                        snr_value = 10 * np.log10(np.sum(ref_frame**2) / np.sum(noise**2))
                    snr_values.append(snr_value)
                snr_value = np.mean(snr_values) if snr_values else 0.0
            else:
                # Calculate SNR for the entire signal
                noise = deg_data - ref_data[:len(deg_data)]
                if np.sum(noise**2) == 0:
                    snr_value = float('inf')
                else:
                     snr_value = 10 * np.log10(np.sum(ref_data**2) / np.sum(noise**2))

            results.append([aligned_deg_file, "OK", f"{snr_value:.2f}", f"{seg_frame_ms}"])
            
        # Print results in a table format
        headers = ["File", "Status", "SNR (dB)", "Seg(ms)"]
        print(tabulate(results, headers=headers, tablefmt="grid"))

        # Save results to CSV
        csv_text = tabulate(results, headers=headers, tablefmt="csv")
        output_path = output_csv if output_csv else self.snr_def_path
        try:
            rw_mode = 'w' if output_path != self.snr_def_path else 'a'
            with open(output_path, rw_mode, encoding="utf-8", newline="") as f:
                f.write(f"# Timestamp: {np.datetime64('now')}\n")
                f.write(csv_text)
                f.write("\n\n")
            print(f"\nResults have been saved to {output_path}")
        except Exception as e:
            print(f"\nWarning: Could not save CSV file due to error: {e}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='PESQ score calculator')
    parser.add_argument("-r", "--ref", type=str, required=True, help="Reference audio WAV file")
    parser.add_argument("-d", "--deg", type=str, nargs='+', required=True, help="Degraded audio file(s) or directory")
    parser.add_argument("-b", "--band", choices=['nb', 'wb', 'auto'], default="auto",
                        help="PESQ mode: 'nb' for narrowband, 'wb' for wideband, 'auto' to decide by sample rate")
    parser.add_argument("-o", "--output", type=str, help="Output CSV file path")
    args = parser.parse_args()
    pesq_tool = PesqScore(bw=args.band)
    pesq_tool.pesq_calc(args.ref, args.deg, output_csv=args.output)
