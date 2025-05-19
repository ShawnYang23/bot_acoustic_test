import json
import matplotlib.pyplot as plt
from datetime import datetime
import argparse


def filter_out_data(json_file_path, args):
    with open(json_file_path, 'r') as file:
        data = json.load(file)["histograms"]
    filtered_data = []
    if args.type == 'audio':
        filtered_data = [
            entry for entry in data if entry['name'].startswith('Media.Audio')]
    elif args.type == 'video':
        filtered_data = [
            entry for entry in data if entry['name'].startswith('Media.Video')]
    elif args.type == 'other':
        pass

    if args.keyword:
        # ingore case sensitivity
        args.keyword = args.keyword.lower()
        filtered_data = [
            entry for entry in filtered_data if args.keyword in entry['name'].lower()]

    return filtered_data


def plot_histogram_data(filtered_data, plot_title=None, save_as=None):
    num_plots = len(filtered_data)
    num_cols = 3
    num_rows = (num_plots + num_cols - 1) // num_cols
    fig, axs = plt.subplots(num_rows, num_cols, figsize=(15, 5 * num_rows))

    axs = axs.flatten()

    for i, entry in enumerate(filtered_data):
        name = entry['name']
        buckets = entry['buckets']
        counts = [bucket['count'] for bucket in buckets]
        lows = [bucket['low'] for bucket in buckets]
        highs = [bucket['high'] for bucket in buckets]
        params = entry.get('params', {})

        # print(f"Name: {name}\nBuckets:\n" + "\n".join([f"  Range: {low}-{high}, Count: {count}" for low, high, count in zip(lows, highs, counts)]))
        # print(f"Params: {json.dumps(params, indent=4)}")
        print(f"Name: {name}\n")
        axs[i].bar(range(len(counts)), counts, tick_label=[
                   "{}-{}".format(low, high) for low, high in zip(lows, highs)])
        axs[i].set_xlabel('Range')
        axs[i].set_ylabel('Count')

        # Split title into two lines if too long
        if len(name) > 30:
            name = '\n'.join([name[:30], name[30:]])

        axs[i].set_title(name, fontsize=10)
        axs[i].tick_params(axis='x', rotation=45)

    for j in range(i + 1, len(axs)):
        fig.delaxes(axs[j])

    if plot_title:
        fig.suptitle(plot_title, fontsize=16, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    if save_as:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plt.savefig(f"{save_as}_{timestamp}.png")

    plt.show()

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description='View histograms from a JSON file.')
    parser.add_argument('json_file_path', type=str,
                        help='Path to the JSON file containing histogram data.')
    parser.add_argument('--type', type=str, choices=[
                        'audio', 'video', 'other'], help='Type of histogram to plot (audio, video, or other).')
    parser.add_argument('--keyword', type=str,
                        help='Keyword to filter histogram names.')
    parser.add_argument('--plot_title', type=str,
                        help='Title for the plot.', default=None)

    args = parser.parse_args()

    filtered_data = filter_out_data(args.json_file_path, args)
    plot_histogram_data(filtered_data, args.plot_title, args.plot_title)
