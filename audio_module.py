from ssh_client import SSHClient
import os
import re
import wave
import subprocess as sp

class AudioModule:
    def __init__(self, ssh_client: SSHClient):
        self.ssh_client = ssh_client
        self.audio_dir_play = "/root/plays/"
        self.audio_dir_record = "/root/records/"
        self.rate = 48000
        self.channels = 2
        self.audio_format = "int16"
        self.rec_dur_sec = 10 
        self.play_dur_sec = 0
        self.file_type = "wav"
        self.engine = "alsa"
        self.device = "speaker"
        self.is_recording = False
        self.is_playing = False

    def paras_settings(self, rate: int = 44100, channels: int = 2, audio_format: str = "S16_LE", rec_sec: int = 10, file_type: str = "wav", engine: str = "alsa", device: str = "speaker"):
        """
        Update audio settings for recording and playback.
        """
        self.rate = rate
        self.channels = channels
        self.audio_format = audio_format
        self.rec_dur_sec = rec_sec
        self.file_type = file_type
        self.engine = engine
        self.device = device
        print(
            f"Audio settings updated: rate={self.rate}, channels={self.channels}, format={self.audio_format}, dur_sec={self.rec_dur_sec}, type={self.file_type}, engine={self.engine}, device={self.device}")

    def get_remote_file_path(self, audio_file: str) -> bool:
        """
        Check if the audio file exists on the remote server and upload it if necessary.
        """
        # check if ssh client is connected
        if self.ssh_client is None:
            print("[ERR]: SSH client is not connected.")
            return None
        local_exists = os.path.exists(audio_file)
        audio_file_name = os.path.basename(audio_file)
        remote_audio_file = os.path.join(self.audio_dir_play, audio_file_name)
        remote_exists = self.ssh_client.file_exists(remote_audio_file)

        if not local_exists and not remote_exists:
            print(f"[ERR]: Audio file {audio_file} does not exist either locally or on the remote server.")
            return None

        # upload audio file to remote server if it does not exist        
        if not remote_exists and local_exists:
            self.ssh_client.upload_file(audio_file, self.audio_dir_play)

        return remote_audio_file 
       
    def get_wav_info(self, audio_file: str) -> dict:
        """
        Get the information of a WAV audio file.
        """
        # Try local file first
        if os.path.exists(audio_file):
            try:
                with wave.open(audio_file, 'rb') as wav_file:
                    sample_rate = wav_file.getframerate()
                    num_frames = wav_file.getnframes()
                    duration = num_frames / sample_rate
                    info = {
                        'channels': wav_file.getnchannels(),
                        'sample_rate': sample_rate,
                        'num_frames': num_frames,
                        'duration': duration,
                    }
                return info
            except Exception as e:
                print(f"[ERR]: Failed to read local WAV file {audio_file}: {e}")
                return None
        # check if ssh client is connected
        if self.ssh_client is None:
            print("[ERR]: SSH client is not connected.")
            return None
        
        remote_audio_file = self.get_remote_file_path(audio_file)
        if remote_audio_file is None:
            print(f"[ERR]: Audio file {audio_file} does not exist on the remote server.")
            return None
        
        # get audio file information
        command = f"ffprobe -v error -show_format -show_streams {remote_audio_file}"
        output = self.ssh_client.execute_command(command)
        if output:
            info = {}
            for line in output.splitlines():
                if '=' not in line:
                    continue
                if ':' in line:
                    continue
                key, value = line.split('=')
                info[key] = value
            return info
        else:
            print("[ERR]: Failed to retrieve audio file information.")
            return None
    
    def check_avaliable_paras(self, dev_type) -> bool:
        """
        Check if the current audio parameters are valid for device
        """
        if 'speaker' in dev_type.lower():
           command = f"aplay -D {self.device} --dump-hw-params /dev/zero"
        elif 'mic' in dev_type.lower():
           command = f"arecord -D {self.device} --dump-hw-params /dev/zero"
        else:
            print(f"[ERR]: Unsupported device type: {dev_type}")
            return False  
        hw_output = self.ssh_client.execute_command(command)
        if hw_output is None:
            print(f"[ERR]: Failed to check audio parameters for device {self.device}.")
            return False
        
        result = {}
        # extract audio format
        format_match = re.search(r'FORMAT:\s+([A-Z0-9_ ]+)', hw_output)
        if format_match:
            formats = format_match.group(1).split()
            result['FORMAT'] = formats

        # extract audio channel count
        channels_match = re.search(r'CHANNELS:\s+(\[?\d+(?:\s+\d+)?\]?)', hw_output)
        if channels_match:
            nums = list(map(int, re.findall(r'\d+', channels_match.group(1))))
            if len(nums) == 2:
                result['CHANNELS'] = {'min': nums[0], 'max': nums[1]}
            elif len(nums) == 1:
                result['CHANNELS'] = {'min': nums[0], 'max': nums[0]}

        # extract sample rate
        rate_match = re.search(r'RATE:\s+(\[?\d+(?:\s+\d+)?\]?)', hw_output)
        if rate_match:
            nums = list(map(int, re.findall(r'\d+', rate_match.group(1))))
            if len(nums) == 2:
                result['RATE'] = {'min': nums[0], 'max': nums[1]}
            elif len(nums) == 1:
                result['RATE'] = {'min': nums[0], 'max': nums[0]}
        
        if self.audio_format.upper() not in result.get('FORMAT', []):
            print(f"[ERR]: Unsupported audio format: {self.audio_format}. Supported formats: {result.get('FORMAT', [])}")
            return False
        if self.channels < result.get('CHANNELS', {}).get('min', 1) or self.channels > result.get('CHANNELS', {}).get('max', 2):
            print(f"[ERR]: Unsupported number of channels: {self.channels}. Supported range: {result.get('CHANNELS', {}).get('min', 1)} - {result.get('CHANNELS', {}).get('max', 2)}")
            return False
        if self.rate < result.get('RATE', {}).get('min', 8000) or self.rate > result.get('RATE', {}).get('max', 192000):
            print(f"[ERR]: Unsupported sample rate: {self.rate}. Supported range: {result.get('RATE', {}).get('min', 8000)} - {result.get('RATE', {}).get('max', 192000)}")
            return False
        return True  # all parameters are valid
        
    def play_audio(self, audio_file) -> bool:
        """
        Play an audio file on the remote server.
        """
        # check if ssh client is connected
        if self.ssh_client is None:
            print("[ERR]: SSH client is not connected.")
            return False
        # check if the audio file exists on the remote server
        remote_audio_file = self.get_remote_file_path(audio_file)
        if remote_audio_file is None:
            print(f"[ERR]: Audio file {audio_file} does not exist on the remote server.")
            return False
        # check if the audio file is a valid audio file
        command = f"ffmpeg -i {remote_audio_file}"
        output = self.ssh_client.execute_command(command)
        if "Audio:" not in output:
            print(f"[ERR]: File {remote_audio_file} is not a valid audio file.")
            return False
        # print(f"[INFO]: {output}")
    
        if self.engine == "alsa":
            if not self.check_avaliable_paras('speaker'):
                return False
            command = f"aplay -D {self.device} {remote_audio_file} -d {self.play_dur_sec}"
        elif self.engine == "cras":
            cras_node = self.get_cras_node(self.device)
            if cras_node is None:
                print(f"[ERR]: CRAS node for device {self.device} not found.")
                return False
            command = f"cras_test_client --select_output {cras_node} --playback_file {remote_audio_file} --rate {self.rate} --num_channels {self.channels} --duration_seconds {self.play_dur_sec}"
        else:
            print(f"[ERR]: Unsupported engine: {self.engine}")
            return False
        
        output = self.ssh_client.execute_command(command)

        if output is not None:
            print(f"[INFO]: Playing audio: {audio_file}")
            return True
        else:
            print("[ERR]: Failed to play audio.")
            return False
        
    def get_cras_node(self, device: str, direction: str = "Output") -> str:
        """
        Get the CRAS node for the specified device.
        """
        device_name = device.split(":")[1].split(",")[0]
        command = "cras_test_client"
        cras_info = self.ssh_client.execute_command(command)
        device_pattern =  re.compile(r"\s+(\d+)[^\n]*" + re.escape(device_name) + r"[^\n]*")
        cras_card_node = ""

        if(direction == "Output"):
            output_section = cras_info.split("Output Devices:")[1].split("Output Nodes:")[0]
            node_id = re.findall(device_pattern, output_section)
            if not node_id:
                print(f"[ERR]: No Speaker found with name {device_name}")
                return None
            else:
                cras_card_node = node_id[0] + ":0"   
        else:
            input_section = cras_info.split("Input Devices:")[1].split("Input Nodes:")[0]
            node_id = re.findall(device_pattern, input_section)
            if not node_id:
                print(f"[ERR]: No Micphones found with name {device_name}")
                return None
            else:
                cras_card_node = node_id[0] + ":0"
        return cras_card_node
    
    def stop_playing(self):
        """
        Stop the current audio playback.
        """
        if not self.is_playing:
            print("[ERR]: No playback is in progress.")
            return False
        print(f"[INFO]: Stopping playback for device {self.device}...")
        if self.is_loopback_device(self.device):
            # stop loopback mode if it is enabled
            ret = self.loopback_file_mode_stop()
            if not ret:
                print("[ERR]: Failed to stop loopback mode.")
                return False
            else:
                self.is_playing = False
                print("[INFO]: Playback stopped.")
                return True
        else:
            command = "pkill -f 'aplay|cras_test_client'"
            output = self.ssh_client.execute_command(command)
            if output is not None:
                self.is_playing = False
                print("[INFO]: Playback stopped.")
                return True
            else:
                print("[ERR]: Failed to stop playback.")
                return False
    
    def stop_recording(self):
        """
        Stop the current audio recording.
        """
        if not self.is_recording:
            print("[ERR]: No recording is in progress.")
            return False
        print(f"[INFO]: Stopping recording for device {self.device}...")
        command = "pkill -f 'arecord|cras_test_client'"
        output = self.ssh_client.execute_command(command)
        if output is not None:
            self.is_recording = False
            print("[INFO]: Recording stopped.")
            return True
        else:
            print("[ERR]: Failed to stop recording.")
            return False
    
    def record_audio(self, output_file: str):
        """
        Record audio from the specified device and save it to the output file.
        """
        if not self.ssh_client:
            print("[ERR]: SSH client is not connected.")
            return False, output_file            
        # check if the output file exists on the remote server
        remote_output_file = os.path.join(self.audio_dir_record, os.path.basename(output_file))
        suffix = 0
        while self.ssh_client.file_exists(remote_output_file):
            suffix += 1
            remote_output_file = os.path.join(self.audio_dir_record, f"{os.path.basename(output_file).split('.')[0]}_{suffix}.{os.path.basename(output_file).split('.')[1]}")
      
        output_file = remote_output_file
        # check if the output file already exists
        if self.ssh_client.file_exists(remote_output_file):
            print(f"[WARN]: Output file {remote_output_file} already exists.")
            return False, output_file
        
        if self.engine == "alsa":
            if not self.check_avaliable_paras('mic'):
                return False, output_file
            command = f"arecord -D {self.device} -f {self.audio_format} -r {self.rate} -t {self.file_type} -c {self.channels} -d {self.rec_dur_sec} {remote_output_file}"
        elif self.engine == "cras":
            cras_node = self.get_cras_node(self.device, direction="Input")
            if cras_node is None:
                print(f"[ERR]: CRAS node for device {self.device} not found.")
                return False, output_file
            command = f"cras_test_client --select_input {cras_node} --duration_seconds {self.rec_dur_sec} --record_file {remote_output_file}"
        else:
            print(f"[ERR]: Unsupported engine: {self.engine}")
            return False, output_file
        
        # device vibemicarray has conflict with device Loopback,0 because of vibe-dsp-server
        if self.device == "hw:vibemicarray,0":
            self.ssh_client.execute_command("stop vibe-dsp-server") 
            output = self.ssh_client.execute_command(command)
            self.ssh_client.execute_command("start vibe-dsp-server")
        else:
            output = self.ssh_client.execute_command(command)

        if output is not None:
            print(f"[INFO]: Recording audio to: {output_file}")
            return True, output_file
        else:
            print("[ERR]: Failed to record audio.")
            return False, output_file
    
    def is_loopback_device(self, device) -> bool:
        """
        Check if the current device is a loopback speaker.
        """
        if device.lower() == "hw:loopback,0":
            return True
        elif device.lower() == "hw:loopback,1":
            return True
        else:
            return False
        
    def loopback_file_mode_start(self, audio_file) -> bool:
        """
        Enable or disable loopback mode for the current device.
        """
        # check if ssh client is connected
        if self.ssh_client is None:
            print("[ERR]: SSH client is not connected.")
            return False
        # check if the audio file exists on the remote server
        audio_file_name = os.path.basename(audio_file)
        remote_audio_file = os.path.join(self.audio_dir_play, audio_file_name)
        if not self.ssh_client.file_exists(remote_audio_file):
            self.ssh_client.upload_file(audio_file, self.audio_dir_play)
        # check if the audio file is a valid audio file
        command = f"ffmpeg -i {remote_audio_file}"
        output = self.ssh_client.execute_command(command)
        if "Audio:" not in output:
            print(f"[ERR]: File {remote_audio_file} is not a valid audio file.")
            return False

        # prepare loopback mode command
        command = f"vibe_dsp_client -c 'mode file {remote_audio_file}'"
        output = self.ssh_client.execute_command(command)
        if output is not None:
            print(f"[INFO]: Loopback file mode satrt executed successfully.")
            return True
        else:
            print(f"[ERR]: Failed to execute loopback file mode start.")
            return False

    def loopback_file_mode_stop(self) -> bool:
        """
        Disable loopback mode for the current device.
        """
        # check if ssh client is connected
        if self.ssh_client is None:
            print("[ERR]: SSH client is not connected.")
            return False
        # stop loopback mode
        command = "vibe_dsp_client -c close"
        output = self.ssh_client.execute_command(command)
        if output is not None:
            print("[INFO]: Loopback mode stopped successfully.")
            return True
        else:
            print("[ERR]: Failed to stop loopback mode.")
            return False 
        
if __name__ == "__main__":
    # Example usage
    ssh_client = SSHClient(hostname="192.168.50.140", username="root", password="test0000")
    if not ssh_client.connect():
        print("[ERR]: Failed to connect to the remote host.")
        exit(1)
    audio_module = AudioModule(ssh_client)
    
    # Update audio settings
    audio_module.paras_settings(rate=48000, channels=1, audio_format="float32", file_type="wav", engine="cras", device="hw:0,0")
    
    # Play an audio file
    # audio_module.play_audio("path/to/audio/file.wav")
    cras_node = audio_module.get_cras_node("hw:Loopback,0", direction="Input")
    print(f"[INFO]: CRAS Node: {cras_node}")
            
        