from ssh_client import SSHClient
import os
import re

class AudioModule:
    def __init__(self, ssh_client: SSHClient):
        self.ssh_client = ssh_client
        self.audio_dir_play = "/root/plays/"
        self.audio_dir_record = "/root/records/"
        self.rate = 48000
        self.channels = 2
        self.audio_format = "int16"
        self.rec_dur_sec = 10 
        self.file_type = "wav"
        self.engine = "alsa"
        self.device = "speaker"
        self.is_recording = False
        self.is_playing = False

    def paras_settings(self, rate: int = 44100, channels: int = 2, audio_format: str = "S16_LE", file_type: str = "wav", engine: str = "alsa", device: str = "speaker"):
        """
        Update audio settings for recording and playback.
        """
        self.rate = rate
        self.channels = channels
        self.audio_format = audio_format
        self.file_type = file_type
        self.engine = engine
        self.device = device
        print(
            f"Audio settings updated: rate={self.rate}, channels={self.channels}, format={self.audio_format}, type={self.file_type}, engine={self.engine}, device={self.device}")

    def play_audio(self, audio_file: str, engine: str = "alsa", device: str = "speaker") -> bool:
        """
        Play an audio file on the remote server.
        """
        if not os.path.exists(audio_file):
            print(f"Audio file {audio_file} does not exist.")
            return False
        # check if ssh client is connected
        if not self.ssh_client.is_connected():
            print("SSH client is not connected.")
            return False
        # check if the audio file exists on the remote server
        audio_file_name = os.path.basename(audio_file)
        remote_audio_file = os.path.join(self.audio_dir_play, audio_file_name)
        if not self.ssh_client.file_exists(remote_audio_file):
            self.ssh_client.upload_file(audio_file, self.audio_dir_play)
        # get audio file information
        command = f"ffmpeg -i {remote_audio_file}"
        output = self.ssh_client.execute_command(command)
        if "Audio:" not in output:
            print(f"File {remote_audio_file} is not a valid audio file.")
            return False
        print(f"{output}")
        # update engine and device settings
        self.device = device
        self.engine = engine
        if engine == "alsa":
            command = f"aplay -D {device} {remote_audio_file}"
        elif engine == "cras":
            cras_node = self.get_cras_node(device)
            if cras_node is None:
                print(f"CRAS node for device {device} not found.")
                return False
            command = f"cras_test_client --select_output {cras_node} --playback_file {remote_audio_file}"
        else:
            print(f"Unsupported engine: {engine}")
            return False
        
        output = self.ssh_client.execute_command(command)

        if output is not None:
            print(f"Playing audio: {audio_file}")
            return True
        else:
            print("Failed to play audio.")
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
                print(f"No Speaker found with name {device_name}")
                return None
            else:
                cras_card_node = node_id[0] + ":0"   
        else:
            input_section = cras_info.split("Input Devices:")[1].split("Input Nodes:")[0]
            node_id = re.findall(device_pattern, input_section)
            if not node_id:
                print(f"No Micphones found with name {device_name}")
                return None
            else:
                cras_card_node = node_id[0] + ":0"
        return cras_card_node
    
    def record_audio(self, output_file: str, engine: str = "alsa", device: str = "mic") -> bool:
        """
        Record audio from the specified device and save it to the output file.
        """
        if not self.ssh_client.is_connected():
            print("SSH client is not connected.")
            return False
        # check if the output file exists on the remote server
        remote_output_file = os.path.join(self.audio_dir_record, os.path.basename(output_file))
        if self.ssh_client.file_exists(remote_output_file):
            print(f"Output file {remote_output_file} already exists.")
            return False
        # update engine and device settings
        self.device = device
        self.engine = engine
        if engine == "alsa":
            command = f"arecord -D {device} -f {self.audio_format} -r {self.rate} -t {self.file_type} -c {self.channels} {remote_output_file}"
        elif engine == "cras":
            cras_node = self.get_cras_node(device, direction="Input")
            if cras_node is None:
                print(f"CRAS node for device {device} not found.")
                return False
            command = f"cras_test_client --select_input {cras_node} --record_file {remote_output_file}"
        else:
            print(f"Unsupported engine: {engine}")
            return False
        
        output = self.ssh_client.execute_command(command)

        if output is not None:
            print(f"Recording audio to: {output_file}")
            return True
        else:
            print("Failed to record audio.")
            return False
    def analyze_audio(self, audio_file: str, method: str = "PESQ"):
        """
        Analyze the audio file and return its properties.
        """
        if not os.path.exists(audio_file):
            print(f"Audio file {audio_file} does not exist.")
            return None
        # check if ssh client is connected
        if not self.ssh_client.is_connected():
            print("SSH client is not connected.")
            return None
        # check if the audio file exists on the remote server
        audio_file_name = os.path.basename(audio_file)
        remote_audio_file = os.path.join(self.audio_dir_play, audio_file_name)
        if not self.ssh_client.file_exists(remote_audio_file):
            self.ssh_client.upload_file(audio_file, self.audio_dir_play)
        # analyze audio file
        if method == "PESQ":
            pass
        elif method == "Reverb":
            pass
        elif method == "SNR":
            pass
        elif method == "DOA":
            pass
        elif method == "ANR":
            pass
        elif method == "AEC":
            pass
        elif method == "Spectrum":
            pass
        else:
            print(f"Unsupported analysis method: {method}")
            return None
    
if __name__ == "__main__":
    # Example usage
    ssh_client = SSHClient(hostname="192.168.50.140", username="root", password="test0000")
    if not ssh_client.connect():
        print("Failed to connect to the remote host.")
        exit(1)
    audio_module = AudioModule(ssh_client)
    
    # Update audio settings
    audio_module.paras_settings(rate=48000, channels=1, audio_format="float32", file_type="wav", engine="cras", device="hw:0,0")
    
    # Play an audio file
    # audio_module.play_audio("path/to/audio/file.wav")
    cras_node = audio_module.get_cras_node("hw:Loopback,0", direction="Input")
    print(f"CRAS Node: {cras_node}")
            
        