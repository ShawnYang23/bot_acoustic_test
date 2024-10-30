#!/usr/bin/env python
import paramiko
import argparse
import subprocess
import os
import time
import configparser
import sys


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
        stdout_text = stdout.read().decode()

        if not args.verbose:
            print(f"{args.remote_path} #: {args.command}")
            print(stdout_text)

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


def execute_local_command(command):
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
        stdout = result.stdout
        stderr = result.stderr
        return stdout, stderr
    except subprocess.CalledProcessError as e:
        print(f"Command failed with return code {e.returncode}")
        print(f"STDERR: {e.stderr}")
        # Handle errors (command failed)
        return e.stdout, e.stderr


def execute_scp_command(ssh, args):
    # If path has a "*" in it, it needs to be quoted to prevent shell expansion
    if args.download:
        if "*" in args.remote_path:
            args.command = f"ls {args.remote_path}"
            text = execute_remote_command(ssh, args)
            for file in text.split("\n"):
                if file:
                    command = f"sshpass -p {args.password} scp -r " + \
                              f"{args.username}@{args.hostname}:{file}" + \
                              f"{args.local_path}"
                    stdout, stderr = execute_local_command(command)
            if stdout == "" and stderr == "":
                print(
                    "Download: \n[remote]:"
                    + args.remote_path
                    + "\n-->\n[local] :"
                    + args.local_path
                )
        else:
            command = f"sshpass -p {args.password} scp -r {args.username}@" + \
                      f"{args.hostname}:{args.remote_path} {args.local_path}"
            stdout, stderr = execute_local_command(command)
            if stdout == "" and stderr == "":
                print(
                    "Download: \n[remote]:"
                    + args.remote_path
                    + "\n-->\n[local] :"
                    + args.local_path
                )
            else:
                print(f"Download failed: {stderr}")
    elif args.upload:
        if "*" in args.local_path:
            stdout, stderr = execute_local_command(f"ls {args.local_path}")
            for file in stdout.split("\n"):
                if file:
                    command = f"sshpass -p {args.password} scp -r " + \
                              f"{file} {args.username}@{args.hostname}:{args.remote_path}"
                    stdout, stderr = execute_local_command(command)
                    print(command)

            if stdout == "" and stderr == "":
                print(
                    "Upload: \n[local] :"
                    + args.local_path
                    + "\n-->\n[remote]:"
                    + args.remote_path
                )
            else:
                print(f"Upload failed: {stderr}")
        else:
            command = f"sshpass -p {args.password} scp -r {args.local_path} " + \
                      f"{args.username}@{args.hostname}:{args.remote_path}"
            stdout, stderr = execute_local_command(command)
            if stdout == "" and stderr == "":
                print(
                    "Upload: \n[local] :"
                    + args.local_path
                    + "\n-->\n[remote]:"
                    + args.remote_path
                )
            else:
                print(f"Upload failed: {stderr}")




def system_prepare(ssh, args):
    if not args.init:
        return True
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
        execute_local_command("cp ./config_default.ini ./config.ini")
    print("[init]: Local config file is prepared")
    # Copy the test audio files to the remote system
    args.command = f"sshpass -p {args.password} scp -r ./plays {args.username}@{args.hostname}:/root/"
    execute_remote_command(ssh, args)
    print("[init]: Remote test audio files are prepared")
    # Restart alsa service
    reset_alsa_client(ssh, args)
    print("[init]: reset alsa client")
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
    stdout, stderr = execute_local_command(
        f"tree --noreport {args.local_path}")
    print(stdout)
    # remote file info
    print("[Remote file info]")
    args.command = f"tree --noreport {args.remote_path}"
    text = execute_remote_command(ssh, args)
    
    print(text)
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
        text = execute_remote_command(ssh, args)
        if text.strip() == "":
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
                execute_local_command(upload_command)
                time.sleep(1)
                play_file_path = remote_store_path + \
                    os.path.basename(local_play_file_path)
        else:
            pass

        # play audio
        # get audio file duration
        args.command = f"sox --i -D {play_file_path}"
        text = execute_remote_command(ssh, args)
        duration = text.strip().split(".")[0]
        # delay before playing audio
        time.sleep(1)
        print("Playing " + play_file_path + " for " + duration + "s")
        args.command = f"cras_test_client  --playback_file {play_file_path} --duration_seconds {duration}"
        if args.engine == "alsa":
            args.command = f"aplay {play_file_path}"
        execute_remote_command(ssh, args)
        time.sleep(int(duration))


def exec_record_audio(ssh, args):
    if args.record_file:
        local_file_path = args.record_file
        local_file_name = os.path.basename(local_file_path)
        record_file_path = "/root/records/" + local_file_name
        duration = args.duration
        args.command = "arecord -D hw:2,0 -f S16_LE -r 48000 -c 8 -t wav -d " + \
            duration + " > " + record_file_path
        if args.engine == "cras":
            args.command = f"cras_test_client --capture_file {record_file_path} --duration_seconds {duration}"
        execute_remote_command(ssh, args)
        print(duration + "s Recording...")
        time.sleep(int(duration))
        print("Recording Done!")
        args.command = f"sshpass -p {args.password} scp {args.username}@{args.hostname}:" + \
                       f"{record_file_path} {local_file_path}"
        print({"command": args.command})
        execute_local_command(args.command)
        print(
            "split 8 channel wav file to a 1-6 channel wav file and an 8 channel wav file")
        # split 8 channel wav file to 0-5 channel wav file and 7 channel wav file
        file_name = local_file_path.split(".")[0]
        suffix = local_file_name.split(".")[1]
        file_path_mic = file_name + "_mic." + suffix
        file_path_lp = file_name + "_lp." + suffix
        stdout, stderr = execute_local_command(
            f"sox {local_file_path} {file_path_mic} remix 1 2 3 4 5 6"
        )
        execute_local_command(f"sox {local_file_path} {file_path_lp} remix 8")


def set_volume(ssh, args):
    if not args.set:
        return
    if args.set == "speaker":
        args.command = f"amixer set 'Master' {args.value} | grep Mono | awk '{{print $4}}' | sed 's/[^0-9]*//g'"
    elif args.set == "mic":
        args.command = f"amixer set 'Capture' {args.value}"
    text = execute_remote_command(ssh, args)
    print(f"Set {args.set} volume to {text.strip()} done!")


def get_volume(ssh, args):
    if not args.get:
        return
    if args.get == "speaker":
        args.command = f"amixer get 'Master' | grep Mono | awk '{{print $4}}' | sed 's/[^0-9]*//g'"
    elif args.get == "mic":
        args.command = f"amixer get 'Capture'"
    text = execute_remote_command(ssh, args)
    print(f"{args.get} volume is: {text.strip()}")


def reset_alsa_client(ssh, args):
    if not args.reset:
        return
    args.command = f"ps -aux | grep 'arecord\|aplay\|cras_test_client\|scp' " + \
        f"| grep -v grep | awk '{{print $2}}' | xargs kill -9"
    execute_remote_command(ssh, args)

def spilt_wav_file(args):
    if not args.spilt:
        return
    print("args.spilt: ", args.spilt)
    stdout, stderr = execute_local_command(f"ls {args.spilt}")
    if not stdout:
        print("File not found")
        return

    for file in stdout.split("\n"):
        if file.endswith(".wav"):
            # make sure the file is a 6 channel wav file
            command = f"soxi {file} | grep 'Channels' | awk '{{print $3}}'"
            stdout, stderr = execute_local_command(command)
            chn = stdout.strip()
            if chn != "6":
                print(f"{file} is {chn} channel wav file, not 6 channel wav file")
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
                stdout, stderr = execute_local_command(command)
                if stderr:
                    print("spilt failed: ", stderr)
                    return

            print("[spilt]:\n " + file + "\n[to]:\n " + file_path_1 +
                  "\n " + file_path_2 + "\n " + file_path_3)


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
    parser.add_argument("--value", default="50%",
                        help="Volume value, working with --set")
    parser.add_argument("--reset", action="store_true",
                        help="reset system to stop all audio process")
    parser.add_argument("--spilt", default="",
                        help="split 6 channel wav file to 3x2 channel files")
    args = parser.parse_args()

    # 更新配置文件
    update_config(args)
    args.local_path = os.path.abspath(args.local_path)

    # print key infos
    print("[KEY INFOS]")
    print("local  path: ", args.local_path)
    print("remote user: ", args.username)
    print("remote host: ", args.hostname)
    print("remote path: ", args.remote_path)

    print("[COMMANDS]")
    # local operation
    spilt_wav_file(args)

    # remote operation
    ssh = ssh_connect(args.hostname, args.port, args.username, args.password)
    if ssh:
        # 准备系统
        if not system_prepare(ssh, args):
            print("System preparation failed")
            return
        # 显示系统信息
        dump_info(ssh, args)
        # 执行命令
        execute_remote_command(ssh, args)
        reset_alsa_client(ssh, args)
        set_volume(ssh, args)
        get_volume(ssh, args)
        execute_scp_command(ssh, args)
        exec_play_audio(ssh, args)
        exec_record_audio(ssh, args)
        # 关闭SSH连接
        ssh.close()
    else:
        print("SSH connection failed")


if __name__ == "__main__":
    main()
