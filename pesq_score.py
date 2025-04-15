import argparse
import os
from scipy.io import wavfile
from pesq import pesq
from tabulate import tabulate
from speech_quality_ana import align_audio_signal
import numpy as np

def get_file_list(*paths):
    file_list = []
    
    for path in paths:
        print(f"Processing path: {path}")  # debug statement to show the path being processed
        if os.path.isdir(path):  
            for item in os.listdir(path):
                full_path = os.path.join(path, item)
                # check if the item is a file and has a .wav extension, and name includes 'aligned_' to avoid duplicates
                if os.path.isfile(full_path) and full_path.lower().endswith('.wav') and ('aligned_' not in os.path.basename(full_path)):
                    file_list.append(full_path)
        elif os.path.isfile(path):  
            file_list.append(path)
    
    return file_list

def pesq_calc(ref_file, deg_files, bw="nb"):

    # read reference audio file
    ref_rate, ref_ = wavfile.read(ref_file)
    ref_ = ref_.astype(np.float32) 
    rms_ref = np.sqrt(np.mean(ref_**2))
    results = []
    degs = get_file_list(*deg_files)  # get all degraded files from the provided paths
    for deg_file in degs:
        try:
            ref = ref_.copy()  # make a copy of the reference audio
            rate_deg, deg = wavfile.read(deg_file)
            # check if the audio files are empty
            if(len(ref) == 0 or len(deg) == 0):
                print(f"warning: One of the files is empty: {ref_file} or {deg_file}")
                results.append([deg_file, "Lenth dismatch", "-"])
                continue
            # check if the sample rates match
            if ref_rate != rate_deg:
                print(f"warning: Sample rate mismatch: {ref_file} ({ref_rate}) vs {deg_file} ({rate_deg})")
                results.append([deg_file, "Sample rate mismatch", "-"])
                continue
           
            # if len(ref) != len(deg):
            #     # set the first 1.2s as zero padding for PESQ calculation, if needed
            #     padding_length = 1 * ref_rate
            #     if len(deg) > padding_length:
            #         # padding = np.zeros(int(padding_length), dtype=deg.dtype)  # create padding of 1.2s
            #         deg = deg[int(padding_length):]
            #         deg = deg[:len(deg)-int(padding_length)]
            #         # deg = np.concatenate((padding, deg))

            #     deg_align_file_path = os.path.join(os.path.dirname(deg_file), "aligned_" + os.path.basename(deg_file))
            #     deg = align_audio_signal(ref, deg, "cc", deg_align_file_path)

            if len(ref) != len(deg):
                min_length = min(len(ref), len(deg))
                ref = ref[len(ref) - min_length:]
                deg = deg[len(deg) - min_length:]
            # calculate PESQ scores
            deg = deg.astype(np.float32) 
            rms_deg = np.sqrt(np.mean(deg**2))
            gain = rms_ref / rms_deg
            # print(f" rms_ref: {rms_ref}, rms_deg: {rms_deg}, gain: {gain}")

            for i in range(len(deg)):
                deg[i] = deg[i] * gain
            pesq_val = 0
            if bw == 'nb':
                pesq_val = pesq(ref_rate, ref, deg, 'nb')
            else:
                pesq_val = pesq(ref_rate, ref, deg, 'wb')

            results.append([deg_file, "OK", f"{pesq_val:.2f}"])
        
        except Exception as e:
            results.append([deg_file, f"Error: {e}", "-"])

    # print the results in a table format
    headers = ["File", "Status", f"PESQ ({bw.upper()})"]
    print(tabulate(results, headers=headers, tablefmt="grid"))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='PESQ score')
    parser.add_argument("-r", "--ref", type=str, required=True, help='Reference audio file')
    parser.add_argument("-d", "--deg", type=str, nargs='+', required=True, help='Degraded audio files (space-separated list)')
    args = parser.parse_args()
    pesq_calc(args.ref, args.deg)