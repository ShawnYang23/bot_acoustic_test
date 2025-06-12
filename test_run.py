#!/usr/bin/env python
import paramiko
import argparse
import subprocess
import os
import time
import configparser
import sys
import signal
import threading
import re
from multiprocessing import Process
import copy 

from speech_quality_ana import *
from pesq_score import PesqScore

cras_output_devices = []
cras_input_devices = []
tmp_rate = 0
tmp_chns = 0
tmp_fmt = ""

# system init and setup
def ssh_connect(args):
    """建立SSH连接"""
    try:
        hostname = args.hostname
        port = args.port
        username = args.username
        password = args.password
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, port, username, password)
        print(f"成功连接到 {hostname}")
        return ssh
    except Exception as e:
        print(f"连接失败: {e}")
        return None
def check_remote_system_init_status(args):
    args.command = "ls /tmp/ | grep 'test_init_done'"
    stdout = execute_remote_command(args)
    if stdout == "":
        return False
    return True
def system_prepare(args):
    # Check if the remote system is initialized
    if check_remote_system_init_status(args):
        print("[init]: Remote system is already initialized")
        if args.init:
            print("[init]: Reinitializing remote system")
        else:
            return
    else:
        print("[init]: Initializing remote system")
    # Check if the root directory is writable and remount if necessary
    args.command = "mount | grep ' / ' | grep rw || mount -o remount,rw /"
    execute_remote_command(args)
    print("[init]: Remote root directory is writable")
    # Ensure the necessary directories and files exist in the remote system
    args.command = "mkdir -p /root/plays /root/records"
    execute_remote_command(args)
    print("[init]: Remote directories are created")
    # Ensure the necessary directories or files exist in the local system
    if not os.path.exists("./config.ini"):
        command = "cp ./config_default.ini ./config.ini"
        execute_local_command(command, args)
    print("[init]: Local config file is prepared")
    # Copy the test audio files to the remote system
    command = f"sshpass -p {args.password} rsync -avz ./plays/ {args.username}@{args.hostname}:/root/plays"
    execute_local_command(command, args)
    # Create a tmp directory in the local system
    command = f"mkdir -p ./tmp/"
    execute_local_command(command, args)
    print("[init]: Remote test audio files are prepared")
    # Restart alsa service
    reset_alsa_client(args)
    print("[init]: Reset alsa client")
    # Create a file to indicate that the initialization is complete
    args.command = "touch /tmp/test_init_done"
    execute_remote_command(args)
    print("[init]: Remote system is initialized")
    return True
def dump_info(args):
    if not args.info:
        return
    # args info
    print("[Args info]")
    print(" hostname: ", args.hostname)
    print(" port: ", args.port)
    print(" username: ", args.username)
    print(" password: ", args.password)
    print(" record duration: ", args.duration, "s")
    print(" local_path: ", args.local_path)
    print(" remote_path: ", args.remote_path)
    print("\n")
    # local file info
    print("[Local file info]")
    command = f"tree --noreport {args.local_path}"
    stdout = execute_local_command(command, args)
    print(stdout)
    # remote file info
    print("[Remote file info]")
    args.command = f"tree --noreport {args.remote_path}"
    stdout = execute_remote_command(args)
    print("[Remote device info]")
    args.command = f"aplay -l | grep card"
    alsa_out = execute_remote_command(args)
    args.command = f"arecord -l | grep card"
    alsa_in = execute_remote_command(args)
    print("[Remote cras device info]")
    args.command = f"cras_test_client"
    cras_stdout = execute_remote_command(args)
    # print(cras_stdout)
    output_device_pattern = re.compile(
        r"Output Devices:\n([\s\S]+?)\n\n", re.MULTILINE)
    input_device_pattern = re.compile(
        r"Input Devices:\n([\s\S]+?)\n\n", re.MULTILINE)
    device_info_pattern = re.compile(r"(\d+)\s+(\d+)\s+\S+\s+(.*)")
    output_devices_block = output_device_pattern.search(cras_stdout)
    input_devices_block = input_device_pattern.search(cras_stdout)

    def parse_devices(device_block):
        devices = []
        if device_block:
            for match in device_info_pattern.finditer(device_block.group(1)):
                device_id = int(match.group(1))
                max_channels = int(match.group(2))
                name = match.group(3)
                devices.append({"ID": device_id, "Max Channels": max_channels, "Name": name})
        return devices

    cras_output_devices = parse_devices(output_devices_block)
    cras_input_devices = parse_devices(input_devices_block)
    print("Output Devices:")
    for device in cras_output_devices:
        print(f" ID: {device['ID']}, Max Channels: {device['Max Channels']}, Name: {device['Name']}")

    print("\nInput Devices:")
    for device in cras_input_devices:
        print(f" ID: {device['ID']}, Max Channels: {device['Max Channels']}, Name: {device['Name']}")
    print("info done!")
def update_config(args):
    if not args.update:
        return
    configfile = "config.ini"
    if not os.path.exists(configfile):
        print("config.ini not found, pls init system : ./test_run.py --init")
        return
    config = configparser.ConfigParser()
    if args.hostname:
        config["DEFAULT"]["hostname"] = args.hostname
    if args.port:
        config["DEFAULT"]["port"] = str(args.port)
    if args.username:
        config["DEFAULT"]["username"] = args.username
    if args.password:
        config["DEFAULT"]["password"] = args.password
    if args.duration:
        config["DEFAULT"]["record_duration"] = args.duration
    if args.local_path:
        config["DEFAULT"]["local_path"] = args.local_path
    if args.remote_path:
        config["DEFAULT"]["remote_path"] = args.remote_path
    with open(configfile, "w") as configfile:
        config.write(configfile)
    print("配置文件已更新")
def reset_alsa_client(args):
    args.command = f"pkill -f 'arecord|aplay|cras_test_client|scp'"
    execute_remote_command(args)

#basic functions
def execute_remote_command(args, fatal=True):
    """执行远程命令"""
    ssh = args.ssh
    try:
        stdin, stdout, stderr = ssh.exec_command(args.command)
        stdout_text = stdout.read().decode().strip()
        stderr_text = stderr.read().decode().strip()

        if not args.verbose:
            print(f"[REMOTE COMMAND]#: {args.command}")
            print(f"[STDOUT:] {stdout_text}")
            print(f"[STDERR:] {stderr_text}")
        # Clear the command to prevent it from being executed again
        args.command = ""
        # Merge stdout and stderr, cause sometimes warning info is in stderr
        out_text = stdout_text + stderr_text
        return out_text
    except Exception as e:
        print(f"{args.remote_path} #: {args.command}")
        print(f"命令执行失败:\n{str(e)}")
        if fatal:
            print("fatal error, exit")
            sys.exit(1)
        return str(e)
def execute_local_command(command, args, fatal=True):
    """执行本地命令"""
    try:
        # Use subprocess.run for easy command execution and output capture
        result = subprocess.run(
            command,
            shell=True,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if not args.verbose:
            print(f"[LOCAL COMMAND]# {command}")
            print(f"[STDOUT:] {result.stdout}")
            print(f"[STDERR:] {result.stderr}")
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Command failed with return code {e.returncode}")
        print(f"STDERR: {e.stderr}")
        # Handle errors (command failed)
        if fatal:
            print("fatal error, exit")
            sys.exit(2)
        return e.stderr
def execute_scp_command(args):
    # If path has a "*" in it, it needs to be quoted to prevent shell expansion
    if args.download:
        if "*" in args.remote_path:
            args.command = f"ls {args.remote_path}"
            stdout = execute_remote_command(args)
            for file in stdout.split("\n"):
                if file:
                    command = f"sshpass -p {args.password} scp -r " + \
                              f"{args.username}@{args.hostname}:{file}" + \
                              f" {args.local_path}"
                    execute_local_command(command, args)
            print(
                f"Download: \n[remote]: {args.remote_path}\n-->\n[local]: {args.local_path}")
        else:
            command = f"sshpass -p {args.password} scp -r {args.username}@" + \
                      f"{args.hostname}:{args.remote_path} {args.local_path}"
            execute_local_command(command, args)
            print(
                f"Download: \n[remote]: {args.remote_path}\n-->\n[local]: {args.local_path}")

    elif args.upload:
        if "*" in args.local_path:
            command = f"ls {args.local_path}"
            stdout = execute_local_command(command, args)
            for file in stdout.split("\n"):
                if file:
                    command = f"sshpass -p {args.password} rsync -avz " + \
                        f"{file} {args.username}@{args.hostname}:{args.remote_path}"
                    # command = f"sshpass -p {args.password} scp -r " + \
                    #           f"{file} {args.username}@{args.hostname}:{args.remote_path}"
                    execute_local_command(command, args)
                    print(command)

            print(
                f"Upload: \n[local]: {args.local_path}\n-->\n[remote]: {args.remote_path}")
        else:
            command = f"sshpass -p {args.password} rsync -avz {args.local_path} " + \
                f"{args.username}@{args.hostname}:{args.remote_path}"
            # command = f"sshpass -p {args.password} scp -r {args.local_path} " + \
            #           f"{args.username}@{args.hostname}:{args.remote_path}"
            execute_local_command(command, args)
            print(
                f"Upload: \n[local]: {args.local_path}\n-->\n[remote]: {args.remote_path}")
def parse_wav_file(args, file_path):
    args.command = f"sox --i -T {file_path}"
    stdout = execute_remote_command(args)
    channels = int(re.search(r"Channels\s+:\s+(\d+)", stdout).group(1))
    rate = int(re.search(r"Sample Rate\s+:\s+(\d+)", stdout).group(1))
    duration = re.search(r"Duration\s+:\s+([\d:.]+)", stdout).group(1)
    fmt = re.search(r"Precision\s+:\s+(\d+)", stdout).group(1)
    hh, mm, ss = map(float, duration.split(':'))
    duration_sec = hh * 3600 + mm * 60 + ss
    return [channels, rate, duration_sec, fmt]

#audio operation functions
def exec_play_audio(args):
    if hasattr(args, "ssh"):
        args.ssh.close()
    args.ssh = ssh_connect(args)
    play_file_path = args.play_file
    remote_file_path = ""
    remote_store_path = "/root/plays/"
    # check remote file exist
    args.command = f"ls {play_file_path}"
    stdout = execute_remote_command(args)
    if stdout == "":
        # if remote file not found, check local
        if not os.path.exists(play_file_path):
            print("File not found in both local and remote,"
                  "please check the file path")
            return
        else:
            # rsync plays file to remote
            print("Uploading " + play_file_path +
                  " to remote folder " + remote_store_path)
            local_play_file_path = args.play_file
            upload_command = f"sshpass -p {args.password} rsync -avz {local_play_file_path} " + \
                f"{args.username}@{args.hostname}:{remote_store_path}"
            execute_local_command(upload_command, args)
            time.sleep(1)
            play_file_path = remote_store_path + \
                os.path.basename(local_play_file_path)
    else:
        pass

    # get audio file duration
    [args.pcm_chns, args.pcm_rate, duration_sec, pcm_fmt] = parse_wav_file(args, play_file_path)
    args.pcm_fmt = f"S{pcm_fmt}_LE" 
    print("Playing " + play_file_path + " duration: " +
          str(duration_sec) + "s", "channels: ", args.pcm_chns , "rate: ", args.pcm_rate, "format: ", args.pcm_fmt)
    if args.engine == "cras":
        cras_card = get_remote_cras_card_parameter(args, "spk", "card_id")

        if args.volume == "0":
            args.volume = get_sys_speaker_volume(args)
        args.command = f"cras_test_client --select_output {cras_card} --playback_file {play_file_path} " \
                       f"--rate {args.pcm_rate} --num_channels {args.pcm_chns} --duration_seconds {duration_sec} --volume {args.volume}"
    else:
        ret = check_device_params(args, "spk")
        if( ret == -1):
            print("Error: check device params failed")
            return
        alsa_card = args.alsa_card

        args.command = f"aplay  -D {alsa_card} -r { args.pcm_rate} -c {args.pcm_chns} -f {args.pcm_fmt} {play_file_path}"
    execute_remote_command(args)
    print("Playing Done!")
    args.play_file = ""

def exec_record_audio(args):
    if hasattr(args, "ssh"):
     args.ssh.close()
    args.ssh = ssh_connect(args)
    # get base record file name
    local_file_path = args.record_file
    local_file_name = os.path.basename(local_file_path)
    file_type = local_file_name.split(".")[1]
    if file_type != "wav" and file_type != "pcm" and file_type != "raw":
        print("Only support wav/pcm(raw)file, pls check the file suffix")
        return
    if file_type == "pcm":
        file_type = "raw"
    # setup remote audio record parameters
    remote_dir = "/root/records/"
    remote_file_path = remote_dir + local_file_name
    duration = args.duration
    if args.engine == "alsa":
        ret = check_device_params(args, "mic")
        if( ret == -1):
            print("Error: check device params failed")
            return
    rate = args.pcm_rate
    chns = args.pcm_chns
    fmt = args.pcm_fmt
    if args.engine == "cras":
        cras_card = get_remote_cras_card_parameter(args, "mic", "card_id")
        if args.volume == "0":
            args.volume = get_sys_mic_gain(args)
        args.command = f"cras_test_client --select_input {cras_card} --capture_file {remote_file_path} " \
                       f"--duration_seconds {duration} --rate {rate} --num_channels {chns} --capture_gain {args.volume}"
    else:
        alsa_card = args.alsa_card
        args.command = f"arecord -D {alsa_card} -f {fmt} " \
                       f"-r {rate} -c {chns} -t wav -d {duration} > {remote_file_path}"
        rate = tmp_rate if tmp_rate != 0 else rate
        chns = tmp_chns if tmp_chns != 0 else chns
        fmt = tmp_fmt if tmp_fmt != "" else fmt
    # record audio
    print(duration + "s Recording...")
    execute_remote_command(args)
    print("Recording Done!")
    # convert pcm to wav
    #TODO(shawn): auto format convert
    if args.engine == "cras" and file_type == "wav":
        args.command = f"sox -t raw -r {rate} -e signed -b 16 -c {chns} {remote_file_path} /tmp/{local_file_name}"
        execute_remote_command(args)
        args.command = f"mv /tmp/{local_file_name} {remote_file_path}"
        execute_remote_command(args)
    if args.engine == "alsa" and file_type == "wav":
        args.command = f"sox -t raw -r {rate} -e signed -b 16 -c {chns} {remote_file_path} /tmp/{local_file_name}"
        execute_remote_command(args)
        args.command = f"mv /tmp/{local_file_name} {remote_file_path}"
        execute_remote_command(args)
    # download record file to local
    command = f"sshpass -p {args.password} rsync -avz {args.username}@{args.hostname}:{remote_file_path} {args.local_path}"
    print({"command": command})
    execute_local_command(command, args)
    # if cras engine, download src file too
    # if args.engine == "cras":
    #     src_file_path = "/dev/shm/record_16k_src.wav"
    #     prefix = local_file_path.split(".")[0]
    #     local_src_file_path = prefix + "_src.wav"
    #     command = f"sshpass -p {args.password} scp {args.username}@{args.hostname}:{src_file_path} {local_src_file_path}"
    #     execute_local_command(command, args)
    args.record_file = ""

def get_remote_alsa_card_info(args, type, print_flag=True):
    dev_type = "micphone" if type.find(f"mic") >= 0 else "speaker"
    dev_cmd = "aplay" if dev_type == "speaker" else "arecord"
    if args.card_name == "all":
        args.command = f"{dev_cmd} -l | grep card"
        stdout = execute_remote_command(args)
        if stdout == "":
            print(f"No {dev_type} devices found")
            return None
        if print_flag:
            if stdout == "":
                print(f"No {dev_type} devices found")
            else:
                print(f"[Remote {dev_type} info]")
                print(stdout)
        else:
            return stdout
    else:
        #TODO(shawn): change vibe bot mic and speaker name to bot in driver
        card_name = args.card_name
        if ("bot" in card_name.lower()) or ("vibe" in card_name.lower()):
            card_name = "vibemicarray" if dev_type == "micphone" else "rockchipad82178"
        args.command = f"{dev_cmd} -l | grep -i {card_name}"
        stdout = execute_remote_command(args)
        if(stdout == ""):
            print(f"No {dev_type} found with name {args.card_name}")
            return None       
        # get card and device number
        card_num = re.search(r"card\s+(\d+):", stdout)
        dev_num = re.search(r"device\s+(\d+):", stdout)
        args.alsa_card = f"hw:{card_num.group(1)},{dev_num.group(1)}"
    
        args.command = f"{dev_cmd} -D {args.alsa_card} --dump-hw-params /dev/zero"
        stdout = execute_remote_command(args)
        if print_flag:
            if stdout == "":
                print(f"No {dev_type} devices found")
            else:
                print(f"[Remote {dev_type} info]")
                print(stdout)
        else:
            if stdout == "":
                print(f"No {dev_type} found with name {args.card_name}")
            else:
                return stdout 
def get_remote_alsa_card_parameter(args, type, param):
    info = get_remote_alsa_card_info(args, type, False)
    if not info:
        print(f"No info found for the card {args.card_name}, please check the card name")
        return None
    if param == "card_id":
        return args.alsa_card
    elif param == "rate":
        rate = re.search(r"RATE:\s+\[(\d+)\s+(\d+)\]", info)
        rate = [int(rate.group(1)), int(rate.group(2))] if rate else None
        if rate == None:
            rate = re.search(r"RATE:\s+(\d+)", info)
            rate = [int(rate.group(1)), int(rate.group(1))]
        return rate
    elif param == "chns":
        chn = re.search(r"CHANNELS:\s+\[(\d+)\s+(\d+)\]", info)
        chn = [int(chn.group(1)), int(chn.group(2))] if chn else None
        if chn == None:
            chn = re.search(r"CHANNELS:\s+(\d+)", info)
            chn = [int(chn.group(1)), int(chn.group(1))]
        return chn
    elif param == "fmt":
        fmt = re.search(r"SAMPLE_BITS:\s+\[(\d+)\s+(\d+)\]", info)
        fmt = [int(fmt.group(1)), int(fmt.group(2))] if fmt else None
        if fmt == None:
            fmt = re.search(r"SAMPLE_BITS:\s+(\d+)", info)
            fmt = [int(fmt.group(1)), int(fmt.group(1))]
        return fmt
    else:
        print("param not supported")
        return None
def get_remote_cras_card_info(args, print_flag=True):
    args.command = f"cras_test_client"
    if(args.cras_info != ""):
        return args.cras_info
    stdout = execute_remote_command(args)
    if stdout == "":
        print(f"No cras devices found")
        return None
    if print_flag:
        print(f"[Remote cras device info]")
        print(stdout)
        return None
    else:
        args.cras_info = stdout
        return stdout
def get_remote_cras_card_parameter(args, type, param):
    info = get_remote_cras_card_info(args, False)
    dev_type = "micphone" if type.find(f"mic") >= 0 else "speaker"
    direction = "Input" if type == "mic" else "Output"
    card_name = args.card_name
    if (card_name.find("bot") >= 0) or (card_name.find("vibe") >= 0):
        card_name = "vibemicarray" if dev_type=="micphone" else "rockchipad82178"
    if not info:
        print(f"No info found for the card {card_name}, please check the card name")
        return None
    if param == "card_id":
        device_pattern =  re.compile(r"\s+(\d+)[^\n]*" + re.escape(card_name) + r"[^\n]*")
        cras_card_node = ""
        if(direction == "Output"):
            output_section = info.split("Output Devices:")[1].split("Output Nodes:")[0]
            node_id = re.findall(device_pattern, output_section)
            if not node_id:
                print(f"No {dev_type} found with name {args.card_name}")
                return None
            else:
                cras_card_node = node_id[0] + ":0"   
        else:
            input_section = info.split("Input Devices:")[1].split("Input Nodes:")[0]
            node_id = re.findall(device_pattern, input_section)
            if not node_id:
                print(f"No {dev_type} found with name {args.card_name}")
                return None
            else:
                cras_card_node = node_id[0] + ":0"
        args.cras_card = cras_card_node 
        return cras_card_node
    else:
        print("param not supported")
        return None
def check_device_params(args, type):
    alsa_card = get_remote_alsa_card_parameter(args, type, "card_id")
    if not alsa_card:
        print(f"No {type} found with name {args.card_name}")
        return -1
    c_min, c_max = get_remote_alsa_card_parameter(args, type, "chns")
    chns = args.pcm_chns
    if chns <= c_max and chns >= c_min:
        chns = int(chns)
    else:
        tmp_chns = chns
        if chns > c_max:
            print(f"Warn: Force set channel number to max: {c_max}")
            chns = c_max
        else:
            chns = c_min
            # print(f"Error: Audio channels number should be greater than device min channel number {c_min}")
            # return -1
    args.pcm_chns = int(chns)
       
    r_min, r_max = get_remote_alsa_card_parameter(args, type, "rate")
    rate = args.pcm_rate
    if rate <= r_max and rate >= r_min:
        rate = int(rate)
    else:
        tmp_rate = rate
        if rate > r_max:
            print(f"Warn: Force set sample rate to max: {r_max}")
            rate = r_max
        else:
            rate = r_min
    args.pcm_rate = int(rate)

    f_min, f_max = get_remote_alsa_card_parameter(args, type, "fmt")
    fmt = re.search(r"S(\d+)_LE", args.pcm_fmt).group(1)
    fmt = int(fmt)
    if fmt <= f_max and fmt >= f_min:
        fmt = int(fmt)
    else:
        tmp_fmt = f"S{fmt}_LE"
        if fmt > f_max:
            print(f"Warn: Force set sample format to max: {f_max}")
            fmt = f_max
        else:
            fmt = f_min
    args.pcm_fmt =f"S{fmt}_LE"
    
    return 0
def get_sys_speaker_volume(args):
    args.command = f"amixer get 'Master' | grep Mono | awk '{{print $4}}' | sed 's/[^0-9]*//g'"
    speaker_vol = execute_remote_command(args)
    print(f"speaker volume is: {speaker_vol}")
    return speaker_vol
def get_sys_mic_gain(args):
    args.command = f"cras_test_client --dump_server_info | grep Internal | awk '{{print $3}}'"
    mic_gain = execute_remote_command(args)
    print(f"mic gain is: {mic_gain} dB")
    return mic_gain
def set_volume(args):
    if not args.set:
        return
    if args.set == "speaker":
        args.command = f"amixer set 'Master' {args.volume} | grep Mono | awk '{{print $4}}' | sed 's/[^0-9]*//g'"
        stdout = execute_remote_command(args)
        print(f"Set {args.set} volume to {stdout} done!")
    elif args.set == "mic":
        args.command = f"cras_test_client --capture_gain {args.volume}"
        execute_remote_command(args)
        print(f"Set {args.set} gain to {args.volume} dB done!")
def get_volume(args, dev_type):
    if not args.get:
        return
    if dev_type == "spk":
        return get_sys_speaker_volume(args)
    elif dev_type == "mic":
        return get_sys_mic_gain(args)
    else:
        get_sys_speaker_volume(args)
        get_sys_mic_gain(args)

# doa analysis functions
def spilt_wav_file(args):
    file_path = args.spilt
    print("spilt file: ", file_path)
    command = f"ls {args.spilt}"
    stdout = execute_local_command(command, args)

    if args.layout == "6x1":
        # split into mic and loopback: 1-6 channel and 8 channel
        print(
            "split 8 channel wav file to a 1-6 channel wav file and an 8 channel wav file")
        for file in stdout.split("\n"):
            if file.endswith(".wav"):
                # make sure the file is a 8 channel wav file
                command = f"soxi {file} | grep 'Channels' | awk '{{print $3}}'"
                stdout = execute_local_command(command, args)
                chn = stdout.strip()
                if chn != "8":
                    print(
                        f"{file} is {chn} channel wav file, not 8 channel wav file")
                    continue

                pre_fix = file.split(".")[0]
                suffix = file.split(".")[1]
                file_path_mic = pre_fix + "_mic." + suffix
                file_path_lp = pre_fix + "_lp." + suffix
                command1 = f"sox {file} {file_path_mic} remix 1 2 3 4 5 6"
                command2 = f"sox {file} {file_path_lp} remix 8"
                for command in [command1, command2]:
                    execute_local_command(command, args)

                print("[spilt]:\n " + file + "\n[to]:\n " + file_path_mic +
                      "\n " + file_path_lp)
    elif args.layout == "3x2":
        # split 6 channel wav file to 3x2 channel wav files
        print("split 6 channel wav file to 3x2 channel wav files")
        for file in stdout.split("\n"):
            if file.endswith(".wav"):
                # make sure the file is a 6 channel wav file
                command = f"soxi {file} | grep 'Channels' | awk '{{print $3}}'"
                stdout = execute_local_command(command, args)
                chn = stdout.strip()
                if chn != "6":
                    print(
                        f"{file} is {chn} channel wav file, not 6 channel wav file")
                    continue

                pre_fix = file.split(".")[0]
                suffix = file.split(".")[1]
                file_path_1 = pre_fix + "_12." + suffix
                file_path_2 = pre_fix + "_34." + suffix
                file_path_3 = pre_fix + "_56." + suffix
                command1 = f"sox {file} {file_path_1} remix 1 2"
                command2 = f"sox {file} {file_path_2} remix 3 4"
                command3 = f"sox {file} {file_path_3} remix 5 6"
                for command in [command1, command2, command3]:
                    execute_local_command(command, args)

                print("[spilt]:\n " + file + "\n[to]:\n " + file_path_1 +
                      "\n " + file_path_2 + "\n " + file_path_3)
    else:
        print("layout not supported")
    args.spilt = ""
def doa_analysis(args):
    # clear remote log file
    args.command = f"echo "" > /var/log/messages"
    execute_remote_command(args)
    # play local audio and record remote audio concurrently
    audio_path = "./doa/shawn_voice_10s.wav"
    # speaker_device = "hw:3,0" # owl
    # speaker_device = "hw:2,0" # bot
    speaker_device = "hw:5,0"  # standard speaker
    command = f"aplay -D {speaker_device} {audio_path}"
    thread_play = threading.Thread(
        target=execute_local_command, args=(command, args))
    # Record remote audio
    args.command = f"cras_test_client --capture_file /tmp/tmp.pcm --duration_seconds {args.duration} --num_channels 2 --capture_gain 20"
    thread_record = threading.Thread(
        target=execute_remote_command, args=(args))
    thread_record.start()
    thread_play.start()
    thread_record.join()
    thread_play.join()
    # download log file
    command = f"sshpass -p {args.password} scp {args.username}@{args.hostname}:/var/log/messages /tmp/messages"
    execute_local_command(command, args)
    # parse doa info and save to file
    doa_angle_file = f"./doa/{args.doa_analysis}.txt"
    command = f"cat /tmp/messages | grep '\[SSL\]' | awk '{{print $6}}' > {doa_angle_file}"
    execute_local_command(command, args)
    command = f"cat {doa_angle_file} | sort | uniq -c | sort -nr"
    print(execute_local_command(command, args))
    # download doa audio file
    doa_auido_file = f"./doa/{args.doa_analysis}_src.wav"
    command = f"sshpass -p {args.password} scp {args.username}@{args.hostname}:/dev/shm/record_48k_src.wav {doa_auido_file}"
    execute_local_command(command, args)
    args.doa_analysis = ""

def audio_quality_record_analysis(args):
    # both record and play audio with engine cras, and the paras are based on the reference audio file
    ref_audio_path = args.ref_audio 
    ref_base_name = os.path.basename(ref_audio_path).split(".")[0] 
    args.engine = "cras"
    [args.pcm_chns, args.pcm_rate, args.duration, fmt] = parse_wav_file(args, ref_audio_path)

    # copy args to avoid modifying the original
    record_args = copy.copy(args)
    play_args = copy.copy(args)
    wait_time_s = 2
    record_args.duration = f"{(int)(args.duration) + wait_time_s + 1}"  
    record_args.record_file = f"{args.local_path}/{ref_base_name}_{args.card_name}.wav"
    play_args.play_file = ref_audio_path
    play_args.card_name = args.ref_speaker
    play_args.volume = 100

    # remove ssh from args, which can't be pickled. Since Process uses pickle to serialize the arguments
    if hasattr(record_args, "ssh"):
        del record_args.ssh
    if hasattr(play_args, "ssh"):
        del play_args.ssh
    
    # Create separate processes for recording and playback
    record_proc = Process(target=exec_record_audio, args=(record_args,))
    play_proc = Process(target=exec_play_audio, args=(play_args,))

    record_proc.start()
    # wait for cras_test_client to available again
    time.sleep(wait_time_s)  
    play_proc.start()

    # Wait for the processes to finish or timeout
    record_proc.join(timeout=15)
    play_proc.join(timeout=15)

    if record_proc.is_alive():
        record_proc.terminate()
        print("Recording process terminated due to timeout.")

    if play_proc.is_alive():
        play_proc.terminate()
        print("Playback process terminated due to timeout.")

    print("Audio recording and playback completed.")
    
    pesq = PesqScore()
    pesq.pesq_calc(ref_audio_path, [record_args.record_file])


def create_signal_handler(args):
    def signal_handler(sig, frame):
        print("You pressed Ctrl+C!")
        if args.ssh:
            args.reset = True
            reset_alsa_client(args.ssh, args)
            print("[reset] audio related process")
            args.ssh.close()
        else:
            print("exit")
        sys.exit(0)
    return signal_handler


def main():
    # read config file: config.ini
    config_file = "config.ini"
    if not os.path.exists(config_file):
        print("config.ini not found, pls init system first: ./test_run.py --init")
    config = configparser.ConfigParser()
    config.read(config_file)
    parser = argparse.ArgumentParser(
        description="This script is used to interact with remote chromium OS device. Especially for audio test."
    )
    # connection parameters
    parser.add_argument("--hostname", default=config["DEFAULT"]["hostname"], help="Remote host IP address")
    parser.add_argument( "--port", type=int, default=config["DEFAULT"]["port"], help="SSH port, default 22",)
    parser.add_argument("--username", default=config["DEFAULT"]["username"], help="SSH username")
    parser.add_argument("--password", default=config["DEFAULT"]["password"], help="SSH password")
    parser.add_argument("--ssh", action="store_true", help="SSH connection handler")
    
    # audio parameters
    parser.add_argument("-c", "--pcm_chns", type=int, default=config["DEFAULT"]["pcm_chns"], help="audio channels")
    parser.add_argument("-f", "--pcm_fmt", choices="S8_LE, S16_LE, S24_LE, S32_LE", default=config["DEFAULT"]["pcm_fmt"], help="audio pcm format")
    parser.add_argument("-r", "--pcm_rate", type=int, default=config["DEFAULT"]["pcm_rate"], help="audio sample rate")
    parser.add_argument("-d","--duration",default=config["DEFAULT"]["record_duration"],help="Recording duration(s), works with --record_file")
    parser.add_argument("-n", "--card_name", default=config["DEFAULT"]["card_name"], help="get audio card info by name, default all")
    parser.add_argument("-e", "--engine", choices=["alsa", "cras"], default="cras", help="audio engine: alsa or cras")
    parser.add_argument("-v", "--volume", default="", help="Volume value, working with --play_file, --record_file options")
    parser.add_argument("--dev_type", choices=["spk", "mic", "all"], default="spk", help="audio device type: spk or mic")
    parser.add_argument("--alsa_card", default="", help="get audio alsa card info by id, default all")
    parser.add_argument("--cras_card", default="", help="get audio cras card info by id, default all")
    parser.add_argument("--cras_info", default="", help="get cras device info, default empty")

    # operation parameters
    parser.add_argument("-l", "--local_path", default=config["DEFAULT"]["local_path"], help="Local file path")
    parser.add_argument("-m", "--remote_path", default=config["DEFAULT"]["remote_path"], help="Remote file path")
    parser.add_argument("-C", "--command", required=False, default="", help="Execute remote command")
    parser.add_argument("-D", "--download", action="store_true", help="Downlaod files")
    parser.add_argument("-U", "--upload", action="store_true", help="Upload files")
    parser.add_argument("-P", "--play_file", default="", help="Upload file to remote /root/plays(if neccessary) and remote plays audio file")
    parser.add_argument("-R", "--record_file", default="", help="Record audio file into /root/records/ and download to local file path")
    parser.add_argument("-s", "--set", choices=["speaker", "mic"], help="Set audio input output volume")
    parser.add_argument("-g", "--get", choices=["speaker", "mic"], help="Get audio input output volume")
   
    #system setup
    parser.add_argument("--init", action="store_true", help="Init system for this script")
    parser.add_argument("-u", "--update", action="store_true", help="Configs will be saved to config.ini file as default")
    parser.add_argument("-V", "--verbose", action="store_false", help="Verbose mode")
    parser.add_argument("--info", action="store_true", help="Show system info")
    parser.add_argument("--reset", action="store_true", help="reset system to stop all audio process")
    parser.add_argument("--dump_card_info", action="store_true", help="dump remote audio card info, default all")

    # doa analysis
    parser.add_argument("--layout", choices=["6x1", "3x2"], default="6x1", help="spilt 6 channel wav file to 6x1 or 3x2 channel files")
    parser.add_argument("--spilt", default="", help="split 6 channel wav file to 3x2 channel files")
    parser.add_argument("--doa_analysis", default="", help="doa analysis")
    parser.add_argument("--audio_qa_record_analysis", action="store_true", help="Perform audio quality analysis")
    parser.add_argument("--ref_audio", default=config["QUALITY"]["ref_audio"], help="Reference audio file for audio quality analysis")
    parser.add_argument("--ref_mic", default=config["QUALITY"]["ref_mic"], help="Reference mic file for audio quality analysis")
    parser.add_argument("--ref_speaker", default=config["QUALITY"]["ref_speaker"], help="Reference speaker file for audio quality analysis")
    args = parser.parse_args()

    # signal handler
    signal_handler = create_signal_handler(args)
    signal.signal(signal.SIGINT, signal_handler)

    # update config file
    update_config(args)
    args.local_path = os.path.abspath(args.local_path)

    # print key infos
    print("[KEY INFOS]")
    print("(local  path): ", args.local_path)
    print("(remote user): ", args.username)
    print("(remote host): ", args.hostname)
    print("(remote path): ", args.remote_path)

    print("[COMMANDS]")

    args.ssh = ssh_connect(args)
    if args.ssh:
        # prepare system
        system_prepare(args)
        # display key info
        dump_info(args)
        # execute setting command
        get_volume(args, dev_type="all")
        # execute special command
        if args.reset:
            reset_alsa_client(args)
        elif args.command:
            execute_remote_command(args)
        elif args.dump_card_info:
            if args.engine == "alsa":
                get_remote_alsa_card_info(args, "mic")
                get_remote_alsa_card_info(args, "spk")
            else:
                get_remote_cras_card_info(args)
        elif args.volume:
            set_volume(args)
        elif args.doa_analysis:
            doa_analysis(args)
            print("doa analysis done!")
        elif args.spilt:
            spilt_wav_file(args)
        elif args.play_file:
            exec_play_audio(args)
        elif args.record_file:
            exec_record_audio(args)
        elif args.download or args.upload:
            execute_scp_command(args)
        elif args.audio_qa_record_analysis:
            audio_quality_record_analysis(args)
        else:
            pass

        # close ssh connection
        args.ssh.close()
    else:
        print("SSH connection failed")


if __name__ == "__main__":
    main()
