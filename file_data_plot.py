# read data from files and plot in the same figure
import os
import argparse
import matplotlib.pyplot as plt
import numpy as np


def read_data_from_file(file_path):
    data = []
    with open(file_path, "r") as f:
        for line in f:
            data.append(float(line))
    return data


def moving_average(data, window_size):
    return np.convolve(data, np.ones(window_size), 'valid') / window_size


def plot_data(datas, names):
    # if datas contains multiple data, plot them each in the same figure with different color
    # plot line chart
    plt.figure()
    for i, data in enumerate(datas):
        data = data[0:2000]
        data = moving_average(data, 3)
        plt.plot(data, label=names[i], marker='none', linestyle='-')
        avg = np.mean(data)
        avg_line = [avg] * len(data)
        plt.plot(
            avg_line, label=f"{names[i]} avg {avg:.2f}", marker='none', linestyle='--')
    plt.legend()
    plt.show()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--data_dir", type=str,
                        required=True, help="The directory of data files")
    parser.add_argument("-f", "--filter_name", type=str,
                        required=False, help="The filter name")
    args = parser.parse_args()
    if not os.path.exists(args.data_dir):
        print("Directory not found")
        return
    data_datas = []
    data_names = []
    for file in os.listdir(args.data_dir):
        if file.endswith(".txt"):
            if args.filter_name is not None and args.filter_name not in file:
                continue
            name = file.split(".")[0]
            data_names.append(name)
            data_datas.append(read_data_from_file(
                os.path.join(args.data_dir, file)))
    plot_data(data_datas, data_names)


if __name__ == "__main__":
    main()
