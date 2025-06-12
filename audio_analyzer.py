from ssh_client import SSHClient
import re
import os
import subprocess as sp
import numpy as np
import wave
import matplotlib.pyplot as plt
import soundfile as sf
from pesq_score import PesqScore


class AudioAnalyzer:
    def __init__(self, audio_module):
        self.audio_module = audio_module
        self.ssh_client = audio_module.ssh_client
        self.pesq_analyzer = PesqScore()
        if not self.ssh_client.is_connected():
            raise Exception("[ERR]: SSH client is not connected. Cannot initialize AudioAnalyzer.")
        
        self.default_analyze_sec = 10 # Default analyze duration in seconds
    
    def audio_analyzing(self, ref_audio:str , target_audio: str, method: str = "PESQ"):
        """
        Analyze the audio file and return its properties.
        """
        if not os.path.exists(target_audio):
            print(f"[ERR]: Target Audio file {target_audio} does not exist.")
            return False
        # analyze audio file
        if method == "PESQ":
            if not os.path.exists(ref_audio):
                print(f"[ERR]: Refe Audio file {ref_audio} does not exist.")
                return False
            print(f"[INFO]: Analyzing audio file {target_audio} with PESQ against reference {ref_audio}.")
            return self.pesq_analyzing(ref_audio, target_audio)   
        elif method == "Reverb":
            pass
        elif method == "SNR":
            pass
        elif method == "DOA":
            info = self.audio_module.get_wav_info(target_audio)
            if info is None:
                print(f"[ERR]: Failed to get audio info for {target_audio}.")
                return False
            chns = info.get('channels', 0)
            # Analyze for direction of arrival (DOA)
            print(f"[INFO]: Analyzing audio file channels {chns} for DOA.")
            if chns == 8:
                # check if ssh client is connected
                if not self.ssh_client.is_connected():
                    print("[ERR]: SSH client is not connected.")
                    return False
                ret = self.doa_analyzing(target_audio)
                if not ret:
                    print(f"[ERR]: Failed to analyze audio file {target_audio} for DOA.")
                    return False
            elif chns == 9:
                ret = self.doa_file_analyzing(target_audio)
                if not ret:
                    print(f"[ERR]: Failed to analyze audio file {target_audio} for DOA.")
                    return False
            else:
                print(f"[ERR]: Unsupported channel count {chns} for DOA analysis. Expected 8 or 9 channels.")
                return False
            return True
        elif method == "ANR":
            pass
        elif method == "AEC":
            pass
        elif method == "Spectrum":
            pass
        else:
            print(f"[ERR]: Unsupported analysis method: {method}")
            return None
        
    def doa_analyzing(self, src_audio):
        """
        Analyze the given audio file for direction of arrival (DOA).
        """
        if not self.ssh_client.is_connected():
            print("[ERR]: SSH client is not connected.")
            return False, None
        src_base_name = os.path.basename(src_audio)
        remote_audio_path = self.audio_module.get_remote_file_path(src_audio)
        if remote_audio_path is None:
            print(f"[ERR]: Audio file {src_base_name} does not exist on the remote server.")
            return False, None

        try:
            remote_config_file_path = "/etc/vibe/dsp/cras_audio_bot.cfg"
            remote_config_file_test_path = "/tmp/cras_audio_bot_test.cfg"
            if not self.ssh_client.file_exists(remote_config_file_path):
                print(f"[ERR]: Configuration file {remote_config_file_path} does not exist on the remote server.")
                return False, None
            if not self.ssh_client.file_exists(remote_config_file_test_path):
                # Download the configuration file from the remote server
                config_file_path = "/tmp/cras_audio_bot.cfg"
                self.ssh_client.download_file(remote_config_file_path, config_file_path)
                # Modify the configuration file to enable recorder and set position to "ssl"
                with open(config_file_path, 'r') as file:
                    config = file.read()
                config = re.sub(r'enable_recorder\s*=\s*0\s*;', 'enable_recorder = 1;', config)
                config = re.sub(
                    r'position:\s*\([^\)]*\);',
                    'position: ("ssl");',
                    config
                )
                with open(config_file_path, 'w') as file:
                    file.write(config)
                # Upload the modified configuration file back to the remote server
                self.ssh_client.upload_file(config_file_path, remote_config_file_test_path)
            
            #TODO check wav file format
            # Analyze the audio file using cras_api_file_test
            self.ssh_client.execute_command("rm -rf /tmp/*ssl_.wav && restart vibe-dsp-server")  # Clean up any previous test output
            print(f"[INFO]: Analyzing audio file {remote_audio_path} for DOA.")
            command = f"cras_api_file_test -c {remote_config_file_test_path} -i {remote_audio_path} -o /tmp/cras_api_file_test.wav"
            output = self.ssh_client.execute_command(command, force=True)
            if output is None or "Error" in output:
                print(f"[ERR]: cras_api_file_test command failed for {remote_audio_path}. Output: {output}")
                return False, None
            # Download the ssl test file to local
            remote_ssl_file_path = self.ssh_client.execute_command(f"ls /tmp/*ssl_.wav | head -n 1") 
            if not remote_ssl_file_path:
                print(f"[ERR]: No SSL file found in /tmp after cras_api_file_test.")
                return False, None
            local_ssl_file_name = f"./records/ssl_{src_base_name}"
            self.ssh_client.download_file(remote_ssl_file_path, local_ssl_file_name)
            print(f"[INFO]: DOA analysis Stage1 completed. SSL file saved at {local_ssl_file_name}.")
            return self.doa_file_analyzing(local_ssl_file_name)
            
        except Exception as e:
            print(f"[ERR]: Failed to analyze audio file {src_audio}: {e}")
            return False, None
        
    def doa_file_analyzing(self, ssl_file):
        if not os.path.exists(ssl_file):
            print(f"[ERR]: SSL file {ssl_file} does not exist.")
            return False

        try:
            # Step 1: extract the 7th channel from the SSL file
            ssl_base_name = os.path.basename(ssl_file)
            ssl_channel_file = f"./records/chn_{ssl_base_name}"
            command = f"ffmpeg -y -i {ssl_file} -map_channel 0.0.8 -c:a pcm_s16le -ar 16000 {ssl_channel_file}"
            result = sp.run(command, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
            if result.returncode != 0:
                print(f"[ERR]: Failed to extract channel: {result.stderr.decode()}")
                return False

            # Step 2: read the extracted channel audio file and recover the angle
            audio_np, sample_rate = sf.read(ssl_channel_file, dtype='float32')
            if len(audio_np) < sample_rate:
                print(f"[ERR]: Audio too short.")
                return False
            def normalize_angle(angle_f):
                """
                Normalize the angle to be within [0, 360) degrees.
                """
                angle_f = angle_f / 0.95
                norm_angle = (angle_f * 180) % 360
                return norm_angle
            
            for i in range(len(audio_np)):
                if np.abs(audio_np[i]) > 0.95:
                    audio_np[i] = -50  # <=-50 angle for invalid data
                else:
                    audio_np[i] = normalize_angle(audio_np[i])

            # Step 3: process the audio for DOA analysis
            doa_block = []
            doa_data = []
            doa_idx = []
            valid_cnt = 0
            invalid_cnt = 0

            
            block_divide_thresh = 8000  # 0.5 seconds at 16kHz
            block_min_size = 1600 # 0.1 seconds at 16kHz
            for i in range(len(audio_np)):
                if audio_np[i] >= 0.0:
                    doa_data.append(audio_np[i])
                    doa_idx.append(i)
                    valid_cnt += 1
                    invalid_cnt = 0
                else:
                    invalid_cnt += 1
                    if invalid_cnt > block_divide_thresh or i == len(audio_np) - 1:
                        if valid_cnt > block_min_size:
                            doa_block.append(doa_data)
                        doa_data = []
                        valid_cnt = 0   
                        invalid_cnt = 0
            print(f"[INFO]: DOA analysis Stage2 completed. Found {len(doa_block)} valid blocks.")
            for i in range(len(doa_block)):
                duartion = len(doa_block[i]) / sample_rate
                min_angle = np.min(doa_block[i])
                max_angle = np.max(doa_block[i])
                pole_diff = max_angle - min_angle
                if pole_diff > 180: #crossing circle point
                    # Adjust angles to avoid crossing the 0/360 degree point
                    mid = (min_angle + max_angle) / 2
                    for j in range(len(doa_block[i])):
                        if doa_block[i][j] > mid:
                            doa_block[i][j] -= 360
                    pole_diff = np.max(doa_block[i]) - np.min(doa_block[i])
                average = np.mean(doa_block[i])
                std = np.std(doa_block[i])
                print(f"[INFO]: DOA Position {i}: Dur: {duartion:.2f}s, AVE: {average:.2f}, STD: {std:.2f}, Pol-Diff: {pole_diff:.2f}")

            # plot the audio waveform with matplotlib
            offset = 0
            for i in range(len(doa_block)):
                for j in range(len(doa_block[i])):
                    audio_np[doa_idx[offset + j]] = doa_block[i][j]
                offset += len(doa_block[i])
            plt.figure(figsize=(10, 4))
            y_time = np.arange(len(audio_np)) / sample_rate
            plt.plot(y_time, audio_np, color='blue')
            plt.title(f"Audio Waveform - {ssl_channel_file}")
            plt.xlabel("Time (seconds)")
            plt.ylabel("Angle (degrees)")
            plt.text(0.5, 0.95, f"Note: <=-50 angle for invalid data", transform=plt.gca().transAxes, fontsize=10, color='red', ha='center')
            plt.grid()
            plt.savefig(f"./records/waveform_{ssl_base_name}.png")
            plt.close()
            
            return True

        except Exception as e:
            print(f"[ERR]: Exception occurred: {e}")
            return False
        
    def pesq_analyzing(self, ref_audio, target_audio):
        """
        Analyze the audio file using PESQ.
        """
        if not os.path.exists(ref_audio) or not os.path.exists(target_audio):
            print(f"[ERR]: Reference or target audio file does not exist.")
            return False
        
        try:
            self.pesq_analyzer.pesq_calc(ref_audio, target_audio)
            return True
        except Exception as e:
            print(f"[ERR]: Failed to analyze audio file with PESQ: {e}")
            return False