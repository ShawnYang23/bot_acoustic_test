import os
import argparse


def round_floats_in_file(input_filename, args):
    try:
        input_dir = os.path.dirname(input_filename)
        input_name = os.path.basename(input_filename)
        output_filename = os.path.join(args.output_path, 'rounded_' + input_name)
        with open(input_filename, 'r') as file:
            # 读取所有行
            lines = file.readlines()

        # 处理每一行
        rounded_lines = [str(round(float(line.strip()))) +
                             '\n' for line in lines]

        # 将处理后的内容写入输出文件
        with open(output_filename, 'w') as file:
            file.writelines(rounded_lines)

        print(
            f"Processed numbers were successfully written to {output_filename}.")
    except Exception as e:
        print(f"An error occurred: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Round numbers in a file.')
    parser.add_argument('-i', '--input_filename', type=str, help='The file to process.')   
    parser.add_argument('-o', '--output_path', default="./round", help='The file path to write the processed numbers to.')
    args = parser.parse_args()
    
    if not os.path.exists(args.output_path):
        os.makedirs(args.output_path)
    # if input_filename is a directory, process all files in the directory
    if os.path.isdir(args.input_filename):
        for filename in os.listdir(args.input_filename):
            if filename.endswith('.txt'):
                filename = os.path.join(args.input_filename, filename)
                round_floats_in_file(filename, args)
    else:
        round_floats_in_file(args.input_filename, args)


if __name__ == '__main__':
    main()