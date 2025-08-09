from ssh_client import SSHClient
import re
import os
import numpy as np
import wave
import matplotlib
matplotlib.use('Agg')  # cancel plot warnings in non-GUI environments
import matplotlib.pyplot as plt
import soundfile as sf
from pesq_score import PesqScore
from pydub import AudioSegment


class AudioAnalyzer:
    def __init__(self, audio_module):
        self.audio_module = audio_module
        self.ssh_client = None
        self.pesq_analyzer = PesqScore()  
        self.default_analyze_sec = 10 # Default analyze duration in seconds
        self.cache_on = False
        self.local_cras_config_path = "./cras/cras_audio_bot_test.cfg"
        self.remote_cras_config_path = "/etc/vibe/dsp/cras_audio_bot.cfg"
        self.test_remote_cras_config_path = "/tmp/cras_audio_bot_test.cfg"

    def set_ssh_connect(self, ssh_client: SSHClient):
        """
        Set the SSH client for remote operations.
        """
        if not ssh_client.is_connected():
            print("[ERR]: SSH client is not connected.")
        self.ssh_client = ssh_client
    
    def audio_analyzing(self, ref_audio:str , target_audio: str, method: str = "PESQ", cache: bool = False):
        """
        Analyze the audio file and return its properties.
        """
        self.cache_on = cache
        if not os.path.exists(target_audio):
            print(f"[ERR]: Target Audio file {target_audio} does not exist.")
            return False
        # analyze audio file
        if method == "PESQ":
            print(f"[INFO]: Analyzing audio file {target_audio} with PESQ against reference {ref_audio}.")
            return self.pesq_analyzing(ref_audio, target_audio)   
        elif method == "Reverb":
            pass
        elif method == "SNR":
            print(f"[INFO]: Analyzing audio file {target_audio} with SNR against reference {ref_audio}.")
            return self.snr_analyzing(ref_audio, target_audio)
        elif method == "DOA":
            info = self.audio_module.get_wav_info(target_audio)
            if info is None:
                print(f"[ERR]: Failed to get audio info for {target_audio}.")
                return False
            chns = self.audio_module.channels = info.get('channels', 0)
            # Analyze for direction of arrival (DOA)
            print(f"[INFO]: Analyzing audio file channels {chns} for DOA.")
            if chns == 8 or chns == 9: # 9 for old version, 8 for new version
                if "ssl" not in target_audio:
                    # check if ssh client is connected
                    if not self.ssh_client.is_connected():
                        print("[ERR]: SSH client is not connected.")
                        return False
                    ret = self.doa_analyzing(target_audio)
                    if not ret:
                        print(f"[ERR]: Failed to analyze audio file {target_audio} for DOA.")
                        return False
                else:
                    ret = self.doa_file_analyzing(target_audio)
                    if not ret:
                        print(f"[ERR]: Failed to analyze audio file {target_audio} for DOA.")
                        return False
            else:
                print(f"[ERR]: Unsupported channel count {chns} for DOA analysis. Expected 8 channels.")
                return False
            return True
        elif method == "ANR":
            print(f"[INFO]: ANR analysis is not implemented yet.")
            return False
        elif method == "AEC":
            print(f"[INFO]: AEC analysis is not implemented yet.")
            return False
        elif method == "Spectrum":
            print(f"[INFO]: Analyzing audio file {target_audio} with Spectrum Analysis.")
            return self.spectrum_analyzing(target_audio)
        elif method == "ODAS":
            print(f"[INFO]: Analyzing audio file {target_audio} with ODAS.")
            return self.odas_analyzing(target_audio)
        else:
            print(f"[ERR]: Unsupported analysis method: {method}")
            return None
        
    def odas_analyzing(self, src_audio):
        """
        Analyze the given audio file for omnidirectional audio source (ODAS).
        """
        if not self.ssh_client.is_connected():
            print("[ERR]: SSH client is not connected.")
            return False

        if not os.path.exists(self.local_cras_config_path):
            print(f"[ERR]: Local configuration file {self.local_cras_config_path} does not exist.")
            return False
        
        src_base_name = os.path.basename(src_audio)
        remote_audio_path, local_audio_path = self.audio_module.check_and_sync_file(src_audio)
        if remote_audio_path is None:
            print(f"[ERR]: Audio file {src_base_name} does not exist on the remote server.")
            return False
        
        try:
            if not self.ssh_client.file_exists(self.remote_cras_config_path):
                print(f"[ERR]: Configuration file {self.remote_cras_config_path} does not exist on the remote server.")
                return False
            if not self.ssh_client.file_exists(self.test_remote_cras_config_path) or not self.cache_on:
                # Modify the configuration file to enable recorder and set position to "ssl"
                with open(self.local_cras_config_path, 'r') as file:
                    config = file.read()
                config = re.sub(r'enable_recorder\s*=\s*0\s*;', 'enable_recorder = 1;', config)
                config = re.sub(r'file_path:\s*\"[^\"]*\";', 'file_path: "/tmp/test";', config)
                with open(self.local_cras_config_path, 'w') as file:
                    file.write(config)
                # Upload the modified configuration file back to the remote server
                self.ssh_client.upload_file(self.local_cras_config_path, self.test_remote_cras_config_path)
            
            #TODO check wav file format
            # Analyze the audio file using cras_api_file_test
            self.ssh_client.execute_command("stop vibe-dsp-server && rm -rf /tmp/*.wav")
            print(f"[INFO]: Analyzing audio file {remote_audio_path} for ODAS.")
            command = f"cras_api_file_test -c {self.test_remote_cras_config_path} -i {remote_audio_path} -o /tmp/cras_api_file_test_sink.wav"
            output = self.ssh_client.execute_command(command, force=True, verbose=True)
            self.ssh_client.execute_command("start vibe-dsp-server")
            if output is None or "Error" in output:
                print(f"[ERR]: cras_api_file_test command failed for {remote_audio_path}. Output: {output}")
                return False
            # Download the test file to local
            remote_file_paths = self.ssh_client.execute_command(f"ls /tmp/*test*.wav -t") 
            if not remote_file_paths:
                print(f"[ERR]: No recorded file found in /tmp after cras_api_file_test.")
                return False
            # sort remote_file_paths as list
            file_list = remote_file_paths.splitlines()
            for path in file_list:
                local_file_name = f"./cache/{os.path.basename(path)}"
                self.ssh_client.download_file(path, local_file_name)
                print(f"[INFO]: ODAS analysis completed. Save file {local_file_name}.")
            return True

        except Exception as e:
            print(f"[ERR]: Failed to analyze audio file {src_audio}: {e}")
            return False
           
    def doa_analyzing(self, src_audio):
        """
        Analyze the given audio file for direction of arrival (DOA).
        """
        if not self.ssh_client.is_connected():
            print("[ERR]: SSH client is not connected.")
            return False
        
        if not os.path.exists(self.local_cras_config_path):
            print(f"[ERR]: Local configuration file {self.local_cras_config_path} does not exist.")
            return False
        src_base_name = os.path.basename(src_audio)
        # Check if the SSL file already exists locally
        local_ssl_file_name = f"./cache/ssl_{src_base_name}"
        local_odas_file_name = f"./cache/odas_{src_base_name}"
        if os.path.exists(local_ssl_file_name) and self.cache_on:
            print(f"[INFO]: SSL file {local_ssl_file_name} already exists. Skipping analysis.")
            return self.doa_file_analyzing(local_ssl_file_name)
        
        # Not exists, proceed on remote server
        remote_audio_path, local_audio_path = self.audio_module.check_and_sync_file(src_audio)
        if remote_audio_path is None:
            print(f"[ERR]: Audio file {src_base_name} does not exist on the remote server.")
            return False
        
        try:
            if not self.ssh_client.file_exists(self.remote_cras_config_path):
                print(f"[ERR]: Configuration file {self.remote_cras_config_path} does not exist on the remote server.")
                return False
            if not self.ssh_client.file_exists(self.test_remote_cras_config_path) or not self.cache_on:
                # Modify the configuration file to enable recorder and set position to "ssl"
                with open(self.local_cras_config_path, 'r') as file:
                    config = file.read()
                config = re.sub(r'enable_recorder\s*=\s*0\s*;', 'enable_recorder = 1;', config)
                config = re.sub(r'position:\s*\([^\)]*\);', 'position: ("ssl");', config)
                config = re.sub(r'file_path:\s*\"[^\"]*\";', 'file_path: "/tmp/test";', config)
                with open(self.local_cras_config_path, 'w') as file:
                    file.write(config)
                # Upload the modified configuration file back to the remote server
                self.ssh_client.upload_file(self.local_cras_config_path, self.test_remote_cras_config_path)
            
            #TODO check wav file format
            # Analyze the audio file using cras_api_file_test
            remote_odas_file_path = "/tmp/cras_api_file_test_sink.wav"
            self.ssh_client.execute_command("stop vibe-dsp-server && rm -rf /tmp/*ssl_.wav")  # Clean up any previous test output
            print(f"[INFO]: Analyzing audio file {remote_audio_path} for DOA.")
            command = f"cras_api_file_test -c {self.test_remote_cras_config_path} -i {remote_audio_path} -o {remote_odas_file_path}"
            output = self.ssh_client.execute_command(command, force=True, verbose=True)
            self.ssh_client.execute_command("start vibe-dsp-server")  # Restart the server after test
            if output is None or "Error" in output:
                print(f"[ERR]: cras_api_file_test command failed for {remote_audio_path}. Output: {output}")
                return False
            # Download the ssl test file to local
            remote_ssl_file_path = self.ssh_client.execute_command(f"ls /tmp/*test*ssl_.wav -t | head -n 1") 
            if not remote_ssl_file_path:
                print(f"[ERR]: No SSL file found in /tmp after cras_api_file_test.")
                return False
            
            self.ssh_client.download_file(remote_ssl_file_path, local_ssl_file_name)
            self.ssh_client.download_file(remote_odas_file_path, local_odas_file_name)
            print(f"[INFO]: DOA analysis Stage1 completed. SSL file saved at {local_ssl_file_name}.")
            return self.doa_file_analyzing(local_ssl_file_name)
            
        except Exception as e:
            print(f"[ERR]: Failed to analyze audio file {src_audio}: {e}")
            return False
        
    def doa_file_analyzing(self, ssl_file):
        if not os.path.exists(ssl_file):
            print(f"[ERR]: SSL file {ssl_file} does not exist.")
            return False
        # Step 1: extract the 7th channel from the SSL file
        ssl_base_name = os.path.basename(ssl_file)
        ssl_channel_file = f"./cache/chn_{ssl_base_name}"
        chns = self.audio_module.channels
        ssl_chn = chns - 1  # Last channel as SSL channel

        if os.path.exists(ssl_channel_file) and self.cache_on:
            print(f"[INFO]: SSL channel file {ssl_channel_file} already exists. Skipping extraction.")
            return True
            
        try:
            # 加载多通道音频（必须是 .wav 且格式支持）
            audio = AudioSegment.from_file(ssl_file)
            if audio.channels < chns:
                print(f"[ERR]: File only has {audio.channels} channels, expected at least {chns}")
                return False

            # 分离出各个通道
            split_channels = audio.split_to_mono()

            if ssl_chn >= len(split_channels):
                print(f"[ERR]: Cannot extract channel {ssl_chn}, only {len(split_channels)} available.")
                return False

            # 获取目标通道并转换采样率
            target_channel = split_channels[ssl_chn].set_frame_rate(16000)

            # 确保目录存在
            os.makedirs(os.path.dirname(ssl_channel_file), exist_ok=True)

            # 导出目标通道为 WAV
            target_channel.export(ssl_channel_file, format="wav")


            # Step 2: read the extracted channel audio file and recover the angle
            audio_np, sample_rate = sf.read(ssl_channel_file, dtype='float32')
            if len(audio_np) < sample_rate:
                print(f"[ERR]: Audio too short, less than 1 second.")
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
        
    def snr_analyzing(self, ref_audio, target_audio):
        """
        Analyze the audio file using SNR.
        """
        if not os.path.exists(ref_audio) or not os.path.exists(target_audio):
            print(f"[ERR]: Reference or target audio file does not exist.")
            return False
        
        try:
            self.pesq_analyzer.snr_calc(ref_audio, target_audio)
            return True
        except Exception as e:
            print(f"[ERR]: Failed to analyze audio file with SNR: {e}")
            return False
        
    def spectrum_analyzing(self, audio_file):
        """
        Analyze the audio file using spectrum analysis.
        """
        if not os.path.isfile(audio_file):
            print(f"[ERR]: Audio file {audio_file} is not a valid file.")
            return False
                
        try:
            # Read the audio file
            with wave.open(audio_file, 'rb') as wf:
                n_channels = wf.getnchannels()
                sample_rate = wf.getframerate()
                n_frames = wf.getnframes()
                audio_data = wf.readframes(n_frames)
                audio_np = np.frombuffer(audio_data, dtype=np.int16)
            base_name = os.path.basename(audio_file)
            for i in range(n_channels):
                channel_data = audio_np[i::n_channels]
                # Perform FFT
                fft_result = np.fft.fft(channel_data)
                freqs = np.fft.fftfreq(len(fft_result), 1/sample_rate)
                # Plot the spectrum
                plt.figure(figsize=(10, 4))
                plt.plot(freqs[:len(freqs)//2], np.abs(fft_result)[:len(freqs)//2])
                plt.title(f"Spectrum Analysis - Channel {i+1}")
                plt.xlabel("Frequency (Hz)")
                plt.ylabel("Magnitude")
                plt.grid()
                plt.savefig(f"./records/spectrum_{base_name}_chn_{i+1}.png")
                plt.close()
            print(f"[INFO]: Spectrum analysis completed, results saved in ./records/")
            return True
        except Exception as e:
            print(f"[ERR]: Failed to analyze audio file with spectrum analysis: {e}")
            return False