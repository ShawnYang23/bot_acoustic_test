#!/usr/bin/env python
import paramiko
import argparse
import subprocess
import os
import time
import configparser
import sys
import signal


def ssh_connect(hostname, port, username, password):
    """建立SSH连接"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, port, username, password)
        print(f"成功连接到 {hostname}")
        return ssh
    except Exception as e:
        print(f"连接失败: {e}")
        return None


def execute_remote_command(ssh, args, fatal=True):
    if not args.command:
        return None, None
    """执行远程命令"""
    try:
        stdin, stdout, stderr = ssh.exec_command(args.command)
        stdout_text = stdout.read().decode().strip()

        if not args.verbose:
            print(f"[REMOTE COMMAND]#: {args.command}")
            print(f"[STDOUT:] {stdout_text}")
            print(f"[STDERR:] {stderr.read().decode().strip()}")

        # Clear the command to prevent it from being executed again
        args.command = ""
        return stdout_text

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


def execute_scp_command(ssh, args):
    # If path has a "*" in it, it needs to be quoted to prevent shell expansion
    if args.download:
        if "*" in args.remote_path:
            args.command = f"ls {args.remote_path}"
            stdout = execute_remote_command(ssh, args)
            for file in stdout.split("\n"):
                if file:
                    command = f"sshpass -p {args.password} scp -r " + \
                              f"{args.username}@{args.hostname}:{file}" + \
                              f"{args.local_path}"
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


def check_remote_system_init_status(ssh, args):
    args.command = "ls /tmp/ | grep 'test_init_done'"
    stdout = execute_remote_command(ssh, args)
    if stdout == "":
        return False
    return True


def system_prepare(ssh, args):
    # Check if the remote system is initialized
    if check_remote_system_init_status(ssh, args):
        print("[init]: Remote system is already initialized")
        if args.init:
            print("[init]: Reinitializing remote system")
        else:
            return
    else:
        print("[init]: Initializing remote system")
    # Check if the root directory is writable and remount if necessary
    args.command = "mount | grep ' / ' | grep rw || mount -o remount,rw /"
    execute_remote_command(ssh, args)
    print("[init]: Remote root directory is writable")
    # Ensure the necessary directories and files exist in the remote system
    args.command = "mkdir -p /root/plays /root/records"
    execute_remote_command(ssh, args)
    print("[init]: Remote directories are created")
    # Ensure the necessary directories or files exist in the local system
    if not os.path.exists("./config.ini"):
        command = "cp ./config_default.ini ./config.ini"
        execute_local_command(command, args)
    print("[init]: Local config file is prepared")
    # Copy the test audio files to the remote system
    command = f"sshpass -p {args.password} rsync -avz ./plays/ {args.username}@{args.hostname}:/root/plays"
    execute_local_command(command, args)
    print("[init]: Remote test audio files are prepared")
    # Restart alsa service
    reset_alsa_client(ssh, args)
    print("[init]: Reset alsa client")
    # Create a file to indicate that the initialization is complete
    args.command = "touch /tmp/test_init_done"
    execute_remote_command(ssh, args)
    print("[init]: Remote system is initialized")
    return True


def dump_info(ssh, args):
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
    stdout = execute_remote_command(ssh, args)

    print(stdout)
    print("info done!")


# 更新配置文件内容
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


def exec_play_audio(ssh, args):
    if args.play_file:
        play_file_path = args.play_file
        remote_file_path = ""
        remote_store_path = "/root/plays/"
        # check remote file exist
        args.command = f"ls {play_file_path}"
        stdout = execute_remote_command(ssh, args)
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

        # play audio
        # get audio file duration
        args.command = f"sox --i -D {play_file_path}"
        stdout = execute_remote_command(ssh, args)
        duration = stdout.split(".")[0]
        # delay before playing audio
        time.sleep(1)
        print("Playing " + play_file_path + " for " + duration + "s")
        if args.engine == "cras":
            if args.value == "0":
                args.value = get_sys_speaker_volume(ssh, args)
            args.command = f"cras_test_client  --playback_file {play_file_path} --duration_seconds {duration} --volume {args.value}"
        else:
            args.command = f"aplay {play_file_path}"
        execute_remote_command(ssh, args)
        time.sleep(int(duration))


def exec_record_audio(ssh, args):
    if args.record_file:
        local_file_path = args.record_file
        local_file_name = os.path.basename(local_file_path)
        file_type = local_file_name.split(".")[1]
        if file_type != "wav" and file_type != "pcm" and file_type != "raw":
            print("Only support wav/pcm(raw)file, pls check the file suffix")
            return
        if file_type == "pcm":
            file_type = "raw"
        remote_dir = "/root/records/"
        remote_file_path = remote_dir + local_file_name
        duration = args.duration
        if args.engine == "cras":
            if args.value == "0":
                args.value = get_sys_mic_gain(ssh, args)
            args.command = f"cras_test_client --capture_file {remote_file_path} --duration_seconds {duration} --num_channels 2 --capture_gain {args.value}"
        else:
            args.command = f"arecord -D hw:2,0 -f S16_LE -r 48000 -c 8 -t {file_type} -d {duration} > {remote_file_path}"
        # record audio
        execute_remote_command(ssh, args)
        print(duration + "s Recording...")
        time.sleep(int(duration))
        print("Recording Done!")
        # convert pcm to wav
        if args.engine == "cras" and file_type == "wav":
            args.command = f"sox -t raw -r 48000 -e signed -b 16 -c 2 {remote_file_path} /tmp/{local_file_name}"
            execute_remote_command(ssh, args)
            args.command = f"mv /tmp/{local_file_name} {remote_file_path}"
            execute_remote_command(ssh, args)
        # download record file to local
        command = f"sshpass -p {args.password} rsync -avz {args.username}@{args.hostname}:{remote_file_path} {local_file_path}"
        print({"command": command})
        execute_local_command(command, args)
        #if cras engine, download src file too
        if args.engine == "cras":
            src_file_path = "/dev/shm/record_48k_src.wav"
            prefix = local_file_path.split(".")[0]
            local_src_file_path = prefix + "_src.wav"
            command = f"sshpass -p {args.password} scp {args.username}@{args.hostname}:{src_file_path} {local_src_file_path}"
            execute_local_command(command, args)
        # split into mic and loopback


def set_volume(ssh, args):
    if not args.set:
        return
    if args.set == "speaker":
        args.command = f"amixer set 'Master' {args.value} | grep Mono | awk '{{print $4}}' | sed 's/[^0-9]*//g'"
        stdout = execute_remote_command(ssh, args)
        print(f"Set {args.set} volume to {stdout} done!")
    elif args.set == "mic":
        args.command = f"cras_test_client --capture_gain {args.value}"
        execute_remote_command(ssh, args)
        print(f"Set {args.set} gain to {args.value} dB done!")


def get_sys_speaker_volume(ssh, args):
    args.command = f"amixer get 'Master' | grep Mono | awk '{{print $4}}' | sed 's/[^0-9]*//g'"
    speaker_vol = execute_remote_command(ssh, args)
    print(f"speaker volume is: {speaker_vol}")
    return speaker_vol


def get_sys_mic_gain(ssh, args):
    args.command = f"cras_test_client --dump_server_info | grep Internal | awk '{{print $3}}'"
    mic_gain = execute_remote_command(ssh, args)
    print(f"mic gain is: {mic_gain} dB")
    return mic_gain


def get_value(ssh, args):
    if not args.get:
        return
    if args.get == "speaker":
        get_sys_speaker_volume(ssh, args)
    elif args.get == "mic":
        get_sys_mic_gain(ssh, args)
    else:
        print("get value not supported")


def reset_alsa_client(ssh, args):
    if not args.reset:
        return
    args.command = f"pkill -f 'arecord|aplay|cras_test_client|scp'"
    execute_remote_command(ssh, args)


def spilt_wav_file(args):
    if not args.spilt:
        return
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
    parser.add_argument(
        "--hostname",
        default=config["DEFAULT"]["hostname"],
        help="Remote host IP address",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=config["DEFAULT"]["port"],
        help="SSH port, default 22",
    )
    parser.add_argument(
        "--username", default=config["DEFAULT"]["username"], help="SSH username"
    )
    parser.add_argument(
        "--password", default=config["DEFAULT"]["password"], help="SSH password"
    )
    parser.add_argument("--ssh", action="store_true",
                        help="SSH connection handler")
    parser.add_argument(
        "-u", "--update", action="store_true", help="Configs will be saved to config.ini file as default"
    )
    parser.add_argument("-v", "--verbose",
                        action="store_false", help="Verbose mode")
    parser.add_argument(
        "--engine", choices=["alsa", "cras"], default="cras", help="audio engine: alsa or cras")
    parser.add_argument(
        "-d",
        "--duration",
        default=config["DEFAULT"]["record_duration"],
        help="Recording duration(s), works with --record_file",
    )
    parser.add_argument(
        "-l",
        "--local_path",
        default=config["DEFAULT"]["local_path"],
        help="Local file path",
    )
    parser.add_argument(
        "-r",
        "--remote_path",
        default=config["DEFAULT"]["remote_path"],
        help="Remote file path",
    )

    parser.add_argument("--init", action="store_true",
                        help="Init system for this script")
    parser.add_argument("--info", action="store_true", help="Show system info")
    parser.add_argument("-C", "--command", required=False,
                        default="", help="Execute remote command")
    parser.add_argument("-D", "--download",
                        action="store_true", help="Downlaod files")
    parser.add_argument(
        "-U", "--upload", action="store_true", help="Upload files")
    parser.add_argument("-P", "--play_file", default="",
                        help="Upload file to remote /root/plays(if neccessary) and remote plays audio file")
    parser.add_argument(
        "-R",
        "--record_file",
        default="",
        help="Record audio file into /root/records/ and download to local file path",
    )
    parser.add_argument(
        "-s", "--set", choices=["speaker", "mic"], help="Set audio input output volume")
    parser.add_argument(
        "-g", "--get", choices=["speaker", "mic"], help="Get audio input output volume")
    parser.add_argument("--value", default="0",
                        help="Volume value, working with --set and --play_file, --record_file options")
    parser.add_argument("--reset", action="store_true",
                        help="reset system to stop all audio process")
    parser.add_argument("--layout", choices=["6x1", "3x2"], default="6x1",
                        help="spilt 6 channel wav file to 6x1 or 3x2 channel files")
    parser.add_argument("--spilt", default="",
                        help="split 6 channel wav file to 3x2 channel files")
    args = parser.parse_args()

    # signal handler
    signal_handler = create_signal_handler(args)
    signal.signal(signal.SIGINT, signal_handler)
    # 更新配置文件
    update_config(args)
    args.local_path = os.path.abspath(args.local_path)

    # print key infos
    print("[KEY INFOS]")
    print("(local  path): ", args.local_path)
    print("(remote user): ", args.username)
    print("(remote host): ", args.hostname)
    print("(remote path): ", args.remote_path)

    print("[COMMANDS]")
    # local operation
    spilt_wav_file(args)

    # remote operation
    args.ssh = ssh_connect(args.hostname, args.port,
                           args.username, args.password)
    ssh = args.ssh
    if ssh:
        # 准备系统
        system_prepare(ssh, args)
        # 显示系统信息
        dump_info(ssh, args)
        # 执行命令
        execute_remote_command(ssh, args)
        reset_alsa_client(ssh, args)
        set_volume(ssh, args)
        get_value(ssh, args)
        execute_scp_command(ssh, args)
        exec_record_audio(ssh, args)
        exec_play_audio(ssh, args)
        # 关闭SSH连接
        ssh.close()
    else:
        print("SSH connection failed")


if __name__ == "__main__":
    main()
