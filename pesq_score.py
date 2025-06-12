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
        self.tmp_dir = "./tmp/"
        self.pesq_def_path = self.tmp_dir + "pesq_results.csv"

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

    def pesq_calc(self, ref_file, deg_files, output_csv=None):
        ref_rate, ref_data = wavfile.read(ref_file)
        ref_data = ref_data.astype(np.float32)
        if isinstance(deg_files, str):
            deg_files = [deg_files]
        deg_list = self.get_file_list(*deg_files)
        target_rate = ref_rate

        # according to the target rate, decide the PESQ mode
        if self.bw == "auto":
            if target_rate > 8000:
                target_rate = 16000
                mode = 'wb'
            else:
                target_rate = 8000
                mode = 'nb'
        else:
            mode = self.bw.lower()
            target_rate = 16000 if mode == 'wb' else 8000

        results = []  
        for deg_file in deg_list:
            status = "OK"
            pesq_score = "-"
            try:
                deg_rate, deg_data = wavfile.read(deg_file)
            except Exception as e:
                results.append([deg_file, f"Read error: {e}", pesq_score])
                continue

            deg_data = deg_data.astype(np.float32)
            
            # 1. Algin sample rates based on reference audio
            if deg_rate != target_rate:
                deg_data = self._resample_signal(deg_data, deg_rate, target_rate)
                deg_rate = target_rate

            # deg_data must be greater than ref_data in length
            if len(deg_data) < len(ref_data) - self.tor_sec * target_rate:
                status = "Record file short"
                results.append([deg_file, status, pesq_score])
                continue

            # 2. Align lengths(time) of reference and degraded audio
            offset = self._find_best_offset(ref_data, deg_data)
            if offset > 0:
                # Record too early, need to trim the beginning of deg_data
                deg_data = deg_data[int(offset):]
            elif offset < 0:
                # Record too late to include the full reference audio
                if offset > -self.tor_sec * target_rate:
                    ref_data = ref_data[-int(offset):]
                else:
                    results.append([deg_file, "Record start late", pesq_score])
                continue

            if len(ref_data) > len(deg_data):
                results.append([deg_file, "Record short tail", pesq_score])
                continue
            # Trim to match reference length
            deg_data = deg_data[:len(ref_data)] 

            if len(ref_data) > 0:
                cur_ref_rms = np.sqrt(np.mean(ref_data**2))
            else:
                cur_ref_rms = 0.0

            # 3. Align RMS levels of reference and degraded audio
            if cur_ref_rms > 0:
                deg_rms = np.sqrt(np.mean(deg_data**2))
                if deg_rms > 0:
                    gain = cur_ref_rms / deg_rms
                    deg_data *= gain  

            #save aligned degraded audio for debugging
            aligned_deg_file = f"aligned_{os.path.basename(deg_file)}"
            aligned_deg_path = os.path.join(self.tmp_dir, aligned_deg_file)
            try:
                wavfile.write(aligned_deg_path, deg_rate, deg_data.astype(np.int16))
                print(f"Aligned degraded audio saved to: {aligned_deg_path}")
            except Exception as e:
                print(f"Warning: Could not save aligned degraded audio due to error: {e}")

            # PESQ calculation
            try:
                pesq_val = pesq(ref_rate, ref_data, deg_data, mode)
                pesq_score = f"{pesq_val:.2f}"
            except Exception as e:
                status = f"PESQ error: {e}"

            results.append([deg_file, status, pesq_score])

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
