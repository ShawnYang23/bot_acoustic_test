import os
import sys
import json
import argparse
import matplotlib.pyplot as plt


def process_json_file(filepath, odas_delays, component_delays, module_delays):
    try:
        if not os.path.isfile(filepath):
            raise FileNotFoundError
        if not filepath.endswith(".json"):
            raise ValueError("Invalid file format")
        with open(filepath, 'r') as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading file {filepath}: {e}")
        return
    # moving averge of odas_delay
    window_size = 10
    odas_delay = data.get("odas_delay", [])
    # odas_delay = odas_delay[0:6000]
    odas_delay_moving_avg = [sum(odas_delay[i:i + window_size]) /
                             window_size for i in range(len(odas_delay) - window_size + 1)]
    # sort components and modules by descending value of performance
    component_delay = data.get("Components", {})
    component_delay_sorted = dict(
        sorted(component_delay.items(), key=lambda x: x[1], reverse=True))
    module_delay = data.get("Modules", {})
    module_delay_sorted = dict(
        sorted(module_delay.items(), key=lambda x: x[1], reverse=True))
    odas_delays.append(odas_delay_moving_avg)
    component_delays.append(component_delay_sorted)
    module_delays.append(module_delay_sorted)


def singleton_analysis(args):
    # init data lists
    odas_delay = []
    component_delay = []
    module_delay = []
    label = []

    # process single json file
    if os.path.isfile(args.input):
        process_json_file(args.input, odas_delay,
                          component_delay, module_delay)
        file_name = os.path.basename(args.input)
        label = (file_name.split(".")[0])
    else:
        print(f"Error: {args.input} is not a valid file.")
        sys.exit(1)

    # create a figure with 2x2 subplots
    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"Performance Analysis of {label}")
    print(f"shape of odas_delay: {len(odas_delay)}")
    # draw line chart for odas_delay
    for i, delays in enumerate(odas_delay):
        delays = [d * 1000 for d in delays]
        axs[0, 0].plot(range(len(delays)), delays, marker='o',
                       linestyle='-', label="odas_delay")
    axs[0, 0].set_title('Odas Delay Line Chart')
    axs[0, 0].set_xlabel('Index')
    axs[0, 0].set_ylabel('Delay (us)')
    axs[0, 0].grid(True)
    avg = sum(delays) / len(delays)
    avg_line = [avg] * len(delays)
    axs[0, 0].plot(
        avg_line, label=f"Avg ({avg:.2f} us)", marker='none', linestyle='--')
    axs[0, 0].legend()
    # axs[0, 0].set_ylim([avg - 500, avg + 500])

    # draw bar chart for component_delay
    if component_delay:
        Module_Time = component_delay[0].get("Module", 0)
        Duration_Time = component_delay[0].get("Duration", 0)
        keys = list(component_delay[0].keys())
        all_keys = set(k for d in component_delay for k in d.keys())
        keys = [k for k in keys if k in all_keys]
        for i, perf in enumerate(component_delay):
            values = [perf.get(k, 0) * 1000 for k in keys]
            axs[0, 1].bar([x + i * 0.2 for x in range(len(keys))],
                          values, width=0.2, label="component_delay")
        axs[0, 1].set_xticks(range(len(keys)))
        axs[0, 1].set_xticklabels(keys, rotation=45)
        axs[0, 1].set_title('Component Performance Histogram')
        axs[0, 1].set_xlabel('Component')
        axs[0, 1].set_ylabel('Consuming Time (us)')
        axs[0, 1].grid(axis='y')
        axs[0, 1].legend()
        total = Duration_Time
        for i, perf in enumerate(component_delay):
            for j, key in enumerate(keys):
                value = perf.get(key, 0)
                axs[0, 1].text(j + i * 0.2, value + 0.1,
                               f"{value/total:.2%}", ha='center')

    # draw pie chart for component_delay
    if component_delay:
        component_delay[0].pop("Duration")
        keys = list(component_delay[0].keys())
        all_keys = set(k for d in component_delay for k in d.keys())
        keys = [k for k in keys if k in all_keys]
        for i, perf in enumerate(component_delay):
            values = [perf.get(k, 0) * 1000 for k in keys]
            axs[1, 0].pie(values, labels=keys, autopct='%1.1f%%')
        axs[1, 0].set_title('Component Performance Pie Chart')
        axs[1, 0].legend()

    # draw bar chart for module_delay
    if module_delay:
        keys = list(module_delay[0].keys())
        all_keys = set(k for d in module_delay for k in d.keys())
        keys = [k for k in keys if k in all_keys]
        for i, perf in enumerate(module_delay):
            values = [perf.get(k, 0) * 1000 for k in keys]
            axs[1, 1].bar([x + i * 0.2 for x in range(len(keys))],
                          values, width=0.2, label="module_delay")
        axs[1, 1].set_xticks(range(len(keys)))
        axs[1, 1].set_xticklabels(keys, rotation=45)
        axs[1, 1].set_title('Module Performance Histogram')
        axs[1, 1].set_xlabel('Module')
        axs[1, 1].set_ylabel('Consuming Time (us)')
        axs[1, 1].grid(axis='y')
        axs[1, 1].legend()
        total = Module_Time
        for i, perf in enumerate(module_delay):
            total = sum(perf.values())
            for j, key in enumerate(keys):
                value = perf.get(key, 0)
                axs[1, 1].text(j + i * 0.2, value + 0.1,
                               f"{value/total:.2%}", ha='center')

    # adjust layout and save the figure to output file
    plt.tight_layout()
    plt.savefig(args.output)
    plt.show()


def multi_odas_analysis(args):
    # init data lists
    odas_delays = []
    component_delays = []
    module_delays = []
    labels = []

    # process all json files in the input folder
    if os.path.isdir(args.input):
        for file in os.listdir(args.input):
            if file.endswith(".json"):
                if args.filter_name and args.filter_name not in file:
                    continue
                process_json_file(os.path.join(args.input, file), odas_delays,
                                  component_delays, module_delays)
                file_name = os.path.basename(file)
                labels.append(file_name.split(".")[0])
    else:
        print(f"Error: {args.input} is not a valid directory.")
        sys.exit(1)

    if args.perf_name == "pipe":
        # plot all odas_delay in the same figure with line chart
        plt.figure()
        for i, delays in enumerate(odas_delays):
            # us to us
            delays = [d * 1000 for d in delays]
            avg = sum(delays) / len(delays)
            plt.plot(range(len(delays)), delays, marker='o',
                     linestyle='-', label=labels[i])
            avg_line = [avg] * len(delays)
            plt.plot(avg_line, label=f"{labels[i]} Avg ({avg:.2f} us)",
                     marker='none', linestyle='--')

        plt.title('Odas Delay Line Chart')
        plt.xlabel('Frame Index')
        plt.ylabel('Delay (ms)')
        plt.grid(True)
        plt.legend()
        # set y-axis limit to the range of average value
        plt.ylim([avg - 500, avg + 1000])
        # denote the symbol of name under legend
        y_min, y_max = plt.ylim()
        y_range = y_max - y_min
        plt.text(len(odas_delays[0]) * 0.9, y_max - y_range * 0.02,
                 "k denotes audio sample rate", ha='center', fontsize=18, color='red')
        plt.text(len(odas_delays[0]) * 0.9, y_max - y_range * 0.04,
                 "f denotes AI working frames", ha='center', fontsize=18, color='red')
      
    elif args.perf_name == "comp":
        # plot all component_delay in the same figure with bar chart
        keys = list(component_delays[0].keys())
        all_keys = set(k for d in component_delays for k in d.keys())
        keys = [k for k in keys if k in all_keys]
        plt.figure()
        for i, perf in enumerate(component_delays):
            values = [perf.get(k, 0) * 1000 for k in keys]
            plt.bar([x + i * 0.2 for x in range(len(keys))],
                    values, width=0.2, label=labels[i])
        plt.xticks(range(len(keys)), keys, rotation=45)
        plt.title('Component Performance Histogram')
        plt.xlabel('Process Component')
        plt.ylabel('Consuming Time (us)')
        plt.grid(axis='y')
        plt.legend()
    elif args.perf_name == "module":
        # plot all module_delay in the same figure with bar chart
        keys = list(module_delays[0].keys())
        all_keys = set(k for d in module_delays for k in d.keys())
        keys = [k for k in keys if k in all_keys]
        plt.figure()
        for i, perf in enumerate(module_delays):
            values = [perf.get(k, 0) * 1000 for k in keys]
            plt.bar([x + i * 0.2 for x in range(len(keys))],
                    values, width=0.2, label=labels[i])
        plt.xticks(range(len(keys)), keys, rotation=45)
        plt.title('Module Performance Histogram')
        plt.xlabel('Process Module')
        plt.ylabel('Consuming Time (us)')
        plt.grid(axis='y')
        plt.legend()
    else:
        print("Invalid filter name")
        sys.exit(1)

    plt.savefig(args.output)
    plt.show()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", type=str,
                        required=True, help="The input file or folder")
    parser.add_argument("-m", "--mode", choices=["single", "multi"], default="single",
                        help="The mode of input file or folder")
    parser.add_argument("-o", "--output", type=str,
                        required=False, default="output.png", help="The output file")
    parser.add_argument("-p", "--perf_name", choices=["none", "pipe", "comp", "module"], default="none",
                        help="The performance name to be analyzed in multi mode")
    parser.add_argument("-f", "--filter_name", type=str, required=False,
                        help="The filter name to filter the files in the folder")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print("Directory not found")
        return
    output_path_dir = os.path.dirname(args.output)
    if (output_path_dir and not os.path.exists(output_path_dir)):
        os.makedirs(output_path_dir)
    if args.mode == "multi" and args.perf_name == "none":
        args.perf_name = "Odas"

    if args.mode == "single":
        singleton_analysis(args)
    else:
        multi_odas_analysis(args)


if __name__ == "__main__":
    main()
