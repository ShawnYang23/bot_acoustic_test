#!/usr/bin/env python
import paramiko
import argparse
import subprocess
import os
import time


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


def download_file(ssh, remote_filepath, local_filepath):
    """从远程服务器下载文件到本地"""
    try:
        sftp = ssh.open_sftp()
        sftp.get(remote_filepath, local_filepath)
        sftp.close()
        print(f"文件已从 {remote_filepath} 下载到 {local_filepath}")
    except Exception as e:
        print(f"文件下载失败: {e}")


def upload_file(ssh, local_filepath, remote_filepath):
    """上传本地文件到远程服务器"""
    try:
        sftp = ssh.open_sftp()
        sftp.put(local_filepath, remote_filepath)
        sftp.close()
        print(f"文件已从 {local_filepath} 上传到 {remote_filepath}")
    except Exception as e:
        print(f"文件上传失败: {e}")


def execute_remote_command(ssh, command):
    """执行远程命令"""
    try:
        stdin, stdout, stderr = ssh.exec_command(command)
        # print(stdout.read().decode())
        return None, stdout, stderr
    except Exception as e:
        print(f"命令执行失败: {e}")
        return None, e.stdout, e.stderr


def execute_local_command(command):
    """执行本地命令"""
    try:
        # Use subprocess.run for easy command execution and output capture
        result = subprocess.run(command, shell=True, check=True, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return None, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        print(f"Command failed with return code {e.returncode}")
        # Handle errors (command failed)
        return None, e.stdout, e.stderr


def execute_scp_command(ssh, args):
    #If path has a "*" in it, it needs to be quoted to prevent shell expansion
    if args.download:
        if "*" in args.remote_filepath:
            stdin, stdout, stderr = execute_remote_command(ssh, f"ls {args.remote_filepath}")
            for file in stdout.read().decode().split("\n"):
                if file:
                    command = f"sshpass -p {args.password} scp -r root@{args.hostname}:{file} {args.local_filepath}"
                    stdin, stdout, stderr = execute_local_command(command)
            if stdout == "" and stderr == "":
                print("Download: \n[remote]:" + args.remote_filepath + "\n-->\n[local] :" + args.local_filepath)
        else:
            command = f"sshpass -p {args.password} scp -r root@{args.hostname}:{args.remote_filepath} {args.local_filepath}"
            stdin, stdout, stderr = execute_local_command(command)
            if stdout == "" and stderr == "":
                print("Download: \n[remote]:" + args.remote_filepath + "\n-->\n[local] :" + args.local_filepath)
    elif args.upload:
        if "*" in args.local_filepath:
            stdin, stdout, stderr = execute_local_command(f"ls {args.local_filepath}")
            for file in stdout.split("\n"):
                if file:
                    command = f"sshpass -p {args.password} scp -r {file} root@{args.hostname}:{args.remote_filepath}"
                    stdin, stdout, stderr = execute_local_command(command)
                    
            if stdout == "" and stderr == "":
                print("Upload: \n[local] :" + args.local_filepath +"\n-->\n[remote]:" + args.remote_filepath)
        else:
            command = f"sshpass -p {args.password} scp -r {args.local_filepath} root@{args.hostname}:{args.remote_filepath}"
            stdin, stdout, stderr = execute_local_command(command)
            if stdout == "" and stderr == "":
                print("Upload: \n[local] :" + args.local_filepath +"\n-->\n[remote]:" + args.remote_filepath)

def execute_command_and_check(ssh, command, error_message):
    """Execute a command on a remote system and check for errors."""
    stdin, stdout, stderr = execute_remote_command(ssh, command)
    
    stderr = stderr.read().decode()
    if stderr.strip():
        # Log the error message and details from stderr
        print(f"Error: {error_message}\nDetails: {stderr.strip()}")
        return False
    return True

def system_prepare(ssh,args):
    # Check if the root directory is writable and remount if necessary
    if not execute_command_and_check(
        ssh, 
        "mount | grep ' / ' | grep rw || mount -o remount,rw /", 
        "Failed to ensure root directory is writable"):
        return False
    print("[init]: Remote root directory is writable")
    # Ensure the necessary directories exist
    if not execute_command_and_check(
        ssh,
        "mkdir -p /root/plays /root/records",
        "Failed to create necessary directories /root/plays or /root/records"):
        return False
    print("[init]: Remote directories are created")
    # Copy the test audio files to the remote system
    command = f"sshpass -p {args.password} scp -r ./plays {args.username}@{args.hostname}:/root/"
    stdin, stdout, stderr = execute_local_command(command)
    if stderr.strip():
        print(f"Error: Failed to copy test audio files to remote system\nDetails: {stderr.strip()}")
        return False
    print("[init]: Remote test audio files are prepared")
    return True

def show_file(ssh, file_path):
    """显示文件"""
    try:
        file_path = "/root/" + file_path
        stdin, stdout, stderr = ssh.exec_command(f"tree --noreport {file_path}")
        print(stdout.read().decode())
    except Exception as e:
        print(f"文件显示失败: {e}")

def dump_info(ssh,args):
    #args info
    print("[Args info]")
    print(" hostname: ", args.hostname)
    print(" port: ", args.port)
    print(" username: ", args.username)
    print(" password: ", args.password)
    print(" record duration: ", args.duration, "s")
    print(" local_filepath: ", args.local_filepath)
    print(" remote_filepath: ", args.remote_filepath)
    print("\n")
    #local file info
    print("[Local file info]")
    stdin, stdout, stderr = execute_local_command(f"tree --noreport {args.local_filepath}")
    print(stdout)
    #remote file info
    print("[Remote file info]")
    show_file(ssh, "plays")
    show_file(ssh, "records")
    print("info done!")

def main():
    # 设置命令行参数
    parser = argparse.ArgumentParser(description="通过SSH进行文件上传或下载")
    parser.add_argument("--hostname", required=False, default="192.168.51.49", help="远程主机IP地址")
    parser.add_argument("--port", type=int, default=22, help="SSH端口, 默认22")
    parser.add_argument("--username", required=False, default="root", help="SSH用户名")
    parser.add_argument("--password", required=False, default="test0000", help="SSH密码")
    parser.add_argument("--init", action="store_true", help="初始化系统")
    parser.add_argument("--info", action="store_true", help="显示系统信息")
    parser.add_argument("--show", default="", help="显示/root/plays(records)文件")
    parser.add_argument("--duration", default="10", help="录制音频时长(s)")
    parser.add_argument("-l", "--local_filepath", required=False,  default="./", help="本地文件路径")
    parser.add_argument("-r", "--remote_filepath", required=False, default="/root", help="远程文件路径")
    parser.add_argument("-c", "--command", required=False, default="", help="远程命令")
    parser.add_argument("-d", "--download", action="store_true", help="下载文件")
    parser.add_argument("-u", "--upload", action="store_true", help="上传文件")
    parser.add_argument("-D", "--play", type=str, help="alsa播放/root/plays/下的音频")
    parser.add_argument("-R", "--record", default="", help="alsa录制音频到/root/records/,并下载到本地./records")
    args = parser.parse_args()
    
    args.local_filepath = os.path.abspath(args.local_filepath)

    # 建立SSH连接
    ssh = ssh_connect(args.hostname, args.port, args.username, args.password)
    if ssh:
        # 准备系统
        if  args.init:
            if not system_prepare(ssh, args):
                print("System preparation failed")
                return
        # 显示系统信息
        if args.info:
            dump_info(ssh, args)
        # 执行命令
        if args.download or args.upload:
            execute_scp_command(ssh, args)

        if args.command:
            stdin, stdout, stderr = execute_remote_command(ssh, args.command)
            print(stdout.read().decode())

        if args.play:
            play_file_name = "./plays/" + args.play
            stdin, stdout, stderr = execute_local_command(f"sox --i -D {play_file_name}")
            duration = stdout.strip().split(".")[0]
            time.sleep(1)
            print("playing " + play_file_name + " for " + duration + "s")
            execute_remote_command(ssh, "aplay -D hw:1,0 " + play_file_name)
            time.sleep(int(duration))

        if args.record:
            record_file_name = "/root/records/" + args.record 
            duration = args.duration
            execute_remote_command(ssh, "arecord -D hw:2,0 -f S16_LE -r 48000 -c 8 -t wav -d " + duration + " > " + record_file_name)
            print(duration +"s Recording...")
            time.sleep(int(duration))
            print("Recording Done!")
            args.remote_filepath = record_file_name
            args.local_filepath = args.local_filepath + "/records"
            args.download = True
            execute_scp_command(ssh, args)
            print("split 8 channel wav file to 1-6 channel wav file and 8 channel wav file")
            #split 8 channel wav file to 0-5 channel wav file and 7 channel wav file
            path = args.local_filepath
            file_name = args.record.split(".")[0]
            suffix = args.record.split(".")[1]
            file_path = path + "/" + args.record
            file_path_mic = path + "/" + file_name + "_mic.wav"
            file_path_lp =  path + "/" + file_name + "_lp.wav"
            print(file_path, "\n", file_path_mic, "\n", file_path_lp)
            execute_local_command(f"sox {file_path} {file_path_mic} remix 1 2 3 4 5 6")
            execute_local_command(f"sox {file_path} {file_path_lp} remix 8")

        if args.show:
            show_file(ssh, args.show)
        # 关闭SSH连接
        ssh.close()


if __name__ == "__main__":
    main()
