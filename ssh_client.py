import paramiko
import os
from scp import SCPClient
import shlex



class SSHClient:
    def __init__(self, hostname, username, password):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.client = None
        self.ssh_transport = None
        self.scp_client = None

    def connect(self):
        """
        Establish an SSH connection.
        """
        try:
            # Create SSH client instance
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Load system host keys if available with auto-add policy
            known_hosts_file = os.path.expanduser("~/.ssh/known_hosts")
            if os.path.exists(known_hosts_file):
                # Read known_hosts file
                with open(known_hosts_file, 'r') as f:
                    known_hosts = f.readlines()
                # if hostname not in known_hosts, add hostname to known_hosts
                if not any(self.hostname in line for line in known_hosts):
                    try:
                        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                        self.client.connect(self.hostname, username=self.username, password=self.password)
                        host_key = self.client.get_transport().get_remote_server_key()
                        # write the host key to known_hosts file
                        with open(known_hosts_file, 'a') as f:
                            f.write(f"{self.hostname} {host_key.get_name()} {host_key.get_base64()}\n")
                        
                        print(f"[INFO]: {self.hostname} added to known hosts.")
                    except Exception as e:
                        print(f"[ERROR]: Failed to fetch host key for {self.hostname} - {str(e)}")
                        return
            # Connect to the remote host
            self.client.connect(
                self.hostname, username=self.username, password=self.password)
   
            # Create SCP client for file transfer
            self.ssh_transport = self.client.get_transport()
            self.scp_client = SCPClient(self.ssh_transport)

            print(f"[INFO]: Connected to {self.hostname} as {self.username}")
            return True
        except Exception as e:
            print(f"[ERR]: Failed to connect: {e}")
            return False
        
    def is_connected(self):
        """
        Check if the SSH client is connected.
        """
        if self.client and self.client.get_transport() and self.client.get_transport().is_active():
            return True
        return False
    
    def disconnect(self):
        """
        Disconnect the SSH client if connected.
        """
        if self.is_connected():
            self.close()
            print(f"[INFO]: Disconnected from {self.hostname}")
        else:
            print("[ERR]: SSH client is not connected.")

        return not self.is_connected()

    def execute_command(self, command, force=False, verbose=False):
        """
        Execute a remote command and return the output as a string.
        """
        try:
            stdin, stdout, stderr = self.client.exec_command(command)
            # Get the output and error (if any)
            output = stdout.read().decode("utf-8").strip()
            error = stderr.read().decode("utf-8").strip()
            if verbose:
                print(f"[CMD]: {command}")
                if output:
                    print(f"[OUT]: {output}")
                if error:
                    print(f"[ERR]: {error}")
            if force:
                return output
            if error != "":
                if output == "":
                    output = error
                else:
                    # only keep first 10 lines of error output
                    error_lines = error.splitlines()
                    error = "\n".join(error_lines[:10])
                    print(f"[ERR]: Remote cmd {command} failed with error: {error}, output: {output}")
                    return None
            return output
        except Exception as e:
            print(f"[ERR]: Failed to execute command: {e}")
            return None

    def upload_file(self, local_path, remote_path):
        """
        Upload a file to the remote server using SCP.
        """
        try:
            if self.scp_client:
                if os.path.isdir(local_path):
                    # Folder update uses strategy: check file name list and download only new files
                    remote_basename_files = []
                    for file in self.get_file_name_list(remote_path):
                        remote_basename_files.append(os.path.basename(file.replace("\\", '/')))
                    # print(f"[INFO]: Uploading local files in {local_path} to remote folder {remote_path}")
                    for root, dirs, files in os.walk(local_path):
                        for file in files:
                            # TODO: check if files content is changed
                            if os.path.basename(file) not in remote_basename_files:
                                local_file_path = os.path.join(root, file).replace("\\", '/')
                                print(f"[INFO]: Uploading file {local_file_path} to remote {remote_path}")
                                self.scp_client.put(local_file_path, remote_path)
                else:
                    # Single file upload uses strategy: force replace
                    print(f"[INFO]: Uploading file {local_path} to remtoe {remote_path}")
                    self.scp_client.put(local_path, remote_path)
                print(f"[INFO]: File uploaded successfully: {local_path} to {remote_path}")
            else:
                print("SCP client not initialized. Ensure SSH connection is established.")
        except Exception as e:
            print(f"[ERR]: Failed to upload file: {e}")
    

    def download_file(self, remote_path, local_path):
        """
        Download a file from the remote server using SCP.
        """
        try:
            if self.scp_client:
                if remote_path.endswith('/'):
                    # Folder download uses strategy: check file name list and download only new files
                    # print(f"[INFO]: Downloading remote files in {remote_path} to local folder {local_path}")
                    remote_files = set(self.get_file_name_list(remote_path))
                    local_basename_files = []
                    for file in os.listdir(local_path):
                        local_basename_files.append(os.path.basename(file))
                    for file in remote_files:
                        # TODO: check if files content is changed
                        if os.path.basename(file) not in local_basename_files:
                            remote_file_path = os.path.join(remote_path, file)
                            remote_file_path = remote_file_path.replace("\\", '/')
                            print(f"[INFO]: Downloading file {remote_file_path} to local {local_path}")
                            self.scp_client.get(remote_file_path, local_path)   
                else:
                    # Signle file download uses strategy: force replace
                    parent_dir = os.path.dirname(local_path)
                    if parent_dir and not os.path.exists(parent_dir):
                        os.makedirs(parent_dir, exist_ok=True)
                    print(f"[INFO]: Downloading file {remote_path} to local {local_path}")
                    self.scp_client.get(remote_path, local_path)
                print(f"[INFO]: File downloaded successfully: {remote_path} to {local_path}")
            else:
                print("SCP client not initialized. Ensure SSH connection is established.")
        except Exception as e:
            print(f"[ERR]: Failed to download file: {e}")

    def close(self):
        """
        Close the SSH connection and SCP client.
        """
        try:
            if self.scp_client:
                self.scp_client.close()
            if self.client:
                self.client.close()
            print("[INFO]: Connection closed.")
        except Exception as e:
            print(f"[ERR]: Error while closing connection: {e}")

    def file_exists(self, remote_file):
        """
        Check if a file exists on the remote server.
        """
        try:
            command = f"test -f {remote_file} && echo 'File exists' || echo 'File does not exist'"
            output = self.execute_command(command)
            return "File exists" in output
        except Exception as e:
            print(f"[ERR]: Failed to check file existence: {e}")
            return False

    def is_dir(self, remote_path):
        """
        Check if a directory exists on the remote server.
        """
        try:
            command = f"test -d {remote_path} && echo 'Directory exists' || echo 'Directory does not exist'"
            output = self.execute_command(command)
            return "Directory exists" in output
        except Exception as e:
            print(f"[ERR]: Failed to check directory existence: {e}")
            return False
    
    def get_file_name_list(self, remote_path, file_type="all") -> list:
        """
        Get a list of files in a directory on the remote server.
        """
        try:
            remote_dir = os.path.dirname(remote_path)
            keyword = os.path.basename(remote_path)

            if file_type == ".wav":
                command = (
                    f"find {shlex.quote(remote_dir)} -maxdepth 1 "
                    f"\\( -type f -name '*.wav' -o -type d \\) "
                    f"-exec sh -c 'if [ -d \"$1\" ]; then echo \"$1/\"; else echo \"$1\"; fi' sh {{}} \\;"
                )

            elif file_type == "dir":
                command = f"find {shlex.quote(remote_dir)} -mindepth 1 -maxdepth 1 -type d -exec printf '%s/\\n' {{}} \\;"

            else:
                command = (
                    f"ls -1 {shlex.quote(remote_dir)} | "
                    f"while read f; do "
                    f"if [ -d \"{remote_dir}/$f\" ]; then echo \"$f/\"; else echo \"$f\"; fi; "
                    f"done"
                )


            output = self.execute_command(command)
            if output:
                file_list = output.split()
                for i in range(len(file_list)):
                    file_list[i] = os.path.join(remote_dir, file_list[i])
                if keyword:
                    file_list = [f for f in file_list if keyword in f]
                file_list = [f + os.path.sep if os.path.isdir(f) else f for f in file_list]
                return file_list
            else:
                print(f"[ERR]: No files found in directory {remote_dir}.")
                return []
        except Exception as e:
            print(f"[ERR]: Failed to get file list from {remote_dir}: {e}")
            return []

    def setup(self, args):
        """
        Setup the remote system by checking if the root directory is writable,
        creating necessary directories, copying test audio files, and preparing the local system.
        """
        # Check if the root directory is writable and remount if necessary
        command = "mount | grep ' / ' | grep rw || mount -o remount,rw /"
        self.execute_command(command)
        print("[init]: Remote root directory is writable")
        # Ensure the necessary directories and files exist in the remote system
        command = "mkdir -p /root/plays /root/records"
        self.execute_command(command)
        print("[init]: Remote work directories are created")
        return True
    
    def remote_reset(self):
        """
        Reset the remote system by stopping all audio-related processes and clearing directories.
        """
        # Stop all audio-related processes
        command = "pkill -f 'arecord|aplay|cras_test_client|scp|rsync|cras_api_file_test'"
        self.execute_command(command)
        print("[reset]: All audio-related processes stopped")        
        return True

    def get_speaker_list(self) -> list:
        """
        Get the list of available speakers on the remote system.
        """
        command = "aplay -l"
        output = self.execute_command(command)
        if output:
            # print("[INFO]: Available speakers:")
            # print(output)
            return self.parse_device_list(output, type="speaker")
        else:
            print("[ERR]: Failed to retrieve speaker list.")
            return None

    def parse_device_list(self, output: str, type: str) -> list:
        """
        Parse the output of `aplay -l` to extract speaker device names.
        """
        speaker_list = []
        for line in output.splitlines():
            if "card" in line and "device" in line:
                parts = line.split(": ")
                block = parts[1].split(", ")
                card_name = block[0].split()[0]
                device_index = block[1].split()[1]
                speaker_list.append(f"hw:{card_name},{device_index}")
        if type == "speaker":
            speaker_list.remove("hw:Loopback,0")
        elif type == "mic":
            speaker_list.remove("hw:Loopback,1")
        return speaker_list

    def get_mic_list(self) -> list:
        """
        Get the list of available microphones on the remote system.
        """
        command = "arecord -l"
        output = self.execute_command(command)
        if output:
            # print("[INFO]: Available microphones:")
            # print(output)
            return self.parse_device_list(output, type="mic")
        else:
            print("[ERR]: Failed to retrieve microphone list.")
            return None


# Example Usage
if __name__ == "__main__":
    # Initialize the SSH client
    ssh_client = SSHClient(hostname="192.168.50.140",
                           username="root", password="test0000")

    # Connect to the remote host
    if ssh_client.connect():
        # Execute a remote command
        output = ssh_client.execute_command("ls -l /tmp")
        if output:
            print("[INFO]: Command output:", output)

        # # Upload a file (example)
        # ssh_client.upload_file("local_file.txt", "/tmp/remote_file.txt")
        output = ssh_client.get_mic_list()
        if output:
            print("[INFO]: Available speakers:", output)

        # # Download a file (example)
        # ssh_client.download_file("/tmp/remote_file.txt", "downloaded_file.txt")

        # Close the SSH connection
        ssh_client.close()
