import os
import numpy as np
import argparse
import re
import subprocess
import sys

# doa data structure
doa = {
    # distance from the source to the microphone array
    "radius": 0,
    # relative height of the source to the microphone array
    "height": 0,
    # azimuth angle of the source
    "azimuth": 0,
    "invalid_thresh": 0,
    "angle_error": 0,
    "accuracy": 0,
    "sensitivity": 0,
    "duration": 0,
    "erorr_arzimuth": [],
    # raw data dict {angle: count}
    "raw_data": {},

}


def execute_local_command(command, verbose=True, fatal=True):
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
        if not verbose:
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


def arzimuth_map_mic(arzimuth):
    # arzimuth is in the range of 0-360
    if arzimuth < 0 or arzimuth > 360:
        print("Invalid angle")
        return None
    if (arzimuth >= 0 and arzimuth <= 30) or (arzimuth >= 330 and arzimuth <= 360):
        return 1
    elif arzimuth >= 30 and arzimuth <= 90:
        return 2
    elif arzimuth >= 90 and arzimuth <= 150:
        return 3
    elif arzimuth >= 150 and arzimuth <= 210:
        return 4
    elif arzimuth >= 210 and arzimuth <= 270:
        return 5
    elif arzimuth >= 270 and arzimuth <= 330:
        return 6


def load_doa_data(file_path, args):
    if not os.path.exists(file_path):
        print("File not found")
        return None
    # initialize the doa data
    local_doa = {
        "radius": 0,
        "height": 0,
        "azimuth": 0,
        "mic_num": 0,
        "invalid_thresh": int(args.invalid_thresh),
        "angle_error": int(args.angle_error),
        "accuracy": 0,
        "sensitivity": 0,
        "duration": int(args.duration),
        "real_azimuth": 0,
        "erorr_arzimuth": [],
        "raw_data": {},
    }
    # parse the file name 100cm_-60cm_240.txt
    if args.device == "std":
        match = re.match(r"std_([0-9]+)cm_(-?[0-9]+)cm_(-?[0-9]+).txt",
                     os.path.basename(file_path))
    else:
        match = re.match(r"evt3_([0-9]+)cm_(-?[0-9]+)cm_(-?[0-9]+).txt",
                     os.path.basename(file_path))
    if match:
        local_doa["radius"] = int(match.group(1))
        local_doa["height"] = int(match.group(2))
        local_doa["azimuth"] = int(match.group(3))
        local_doa["mic_num"] = arzimuth_map_mic(local_doa["azimuth"])
    else:
        # print(f"Invalid file name: {os.path.basename(file_path)}")
        return None
    # parse the file content
    # print(f"Parse the file: {file_path}")
    stdout = execute_local_command(
        f"cat {file_path} | sort | uniq -c | sort -nr")
    # print(stdout)
    for line in stdout.splitlines():
        count, angle = line.split()
        local_doa["raw_data"][angle] = count
    return local_doa


def load_doa_file(data_dir, args):
    if not os.path.exists(data_dir):
        print("Directory not found")
        return None
    doas = []
    for file in os.listdir(data_dir):
        if file.endswith(".txt"):
            doa = load_doa_data(os.path.join(data_dir, file), args)
            if doa:
                doas.append(doa)
                # return doas
    return doas


def doa_angle_diff(angle1, angle2):
    # arzimuth is in the range of 0-360
    if angle1 < 0 or angle1 > 360 or angle2 < 0 or angle2 > 360:
        print("Invalid angle")
        return None
    # if the angle in the range of 300-360 and 0-60 is near to each other
    if angle1 > 300 and angle2 < 60:
        angle1 -= 360
    if angle2 > 300 and angle1 < 60:
        angle2 -= 360
    diff = abs(angle1 - angle2)
    return diff


def calculate_accuracy_sensitivity(doa):
    if not doa:
        return None
    real_azimuth = 0
    most_freq_count = 0
    correct_count = 0
    approx_count = 0
    error_count = 0
    invalid_count = 0
    # find most frequent angle as the real azimuth
    for angle, count in doa["raw_data"].items():
        count = int(count)
        if int(angle) == -360:
            invalid_count += count
            continue
        else:
            if count > most_freq_count:
                most_freq_count = count
                real_azimuth = int(angle)
    doa["real_azimuth"] = real_azimuth
    # calculate the accuracy
    for angle, count in doa["raw_data"].items():
        count = int(count)
        if int(angle) == -360:
            continue
        else:
            diff = doa_angle_diff(real_azimuth, int(angle))
            if diff <= doa["angle_error"]:
                correct_count += count
            else:
                if diff >= 30:
                    doa["erorr_arzimuth"].append(int(angle))
                    error_count += count
                else:
                    approx_count += count
    doa["accuracy"] = correct_count / \
        (correct_count + error_count + approx_count) * 100
    # calculate the sensitivity
    invalid_count -= doa["invalid_thresh"]
    if invalid_count < 0:
        invalid_count = 0
    valid_count = correct_count + error_count + approx_count
    doa["sensitivity"] = valid_count / (valid_count + invalid_count) * 100
    return doa


def main():
    parser = argparse.ArgumentParser(
        description='Calculate the doa accuracy and sensitivity of the microphone array')
    parser.add_argument('--radius', default="100",
                        help='distance from the source to the microphone array in cm')
    parser.add_argument('--height', default="0",
                        help='relative height of the source to the microphone array in cm')
    parser.add_argument('--azimuth', default="0",
                        help='azimuth angle of the source in degrees')
    parser.add_argument('-t', '--invalid_thresh', default="500",
                        help='invalid_thresh of the valid angle count')
    parser.add_argument('-e', '--angle_error', default="5",
                        help='tolerance of the angle error in degrees')
    parser.add_argument('-d', '--duration', default="10",
                        help='duration of the test audio in seconds')
    parser.add_argument('-a', '--accuracy', default="all",
                        help='accuracy of the doa in degrees')
    parser.add_argument('-s', '--sensitivity', default="all",
                        help='sensitivity of the doa in degrees')
    parser.add_argument('-D', '--device', choices=["std", "evt3"], default="std",
                        help='device type')
    parser.add_argument('-R', '--radius_filter', choices=["50", "100", "150", "all"], default="all",
                        help='filter the doa data by the radius')
    parser.add_argument('-H', '--height_filter', choices=["-20", "0", "20", "30", "all"], default="all",
                        help='filter the doa data by the height')
    args = parser.parse_args()

    data_dir = f"./doa/"
    doas = load_doa_file(data_dir, args)
    if not doas:
        print("No valid doa data found")
        return
    table_count = 0
    average_accuracy = [0,0,0,0,0,0]
    average_sensitivity = [0,0,0,0,0,0]
    valid_doa_count = [0,0,0,0,0,0]
    for doa in doas:
        doa = calculate_accuracy_sensitivity(doa)
        # filter the doa data
        if args.radius_filter != "all" and int(args.radius_filter) != doa["radius"]:
            continue
        if args.height_filter != "all" and int(args.height_filter) != doa["height"]:
            continue
            
        if doa:
            valid_doa_count[doa["mic_num"]-1] += 1
            average_accuracy[doa["mic_num"]-1] += doa["accuracy"]
            average_sensitivity[doa["mic_num"]-1] += doa["sensitivity"]


    # total print
    print("*" *60)
    print(f"{'invalid_thresh:':<10} {doas[0]['invalid_thresh']:<4} | {'angle_error:':<10} {doas[0]['angle_error']:<5} | {'duration:':<10} {doas[0]['duration']:<10}")
    print(f"{'radius_filter:':<10} {args.radius_filter:<5} | {'height_filter:':<10} {args.height_filter:<5}")
    print("*" *60)
    print(f"{'mic_num':<10} {'accuracy':<10} {'sensitivity':<10}")
    for i in range(6):
        if average_accuracy[i] > 0:
            print(f"{i+1:<10} {average_accuracy[i]/valid_doa_count[i]:<10.2f} {average_sensitivity[i]/valid_doa_count[i]:<10.2f}")
            print("-" *60)
        else:
            print("No valid DOA data to calculate the accuracy and sensitivity")


if __name__ == "__main__":
    main()
