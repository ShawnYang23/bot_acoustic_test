
# Tool Description

### This tool is used for sound-related testing and bug troubleshooting for the product vibe-bot, primarily targeting devices such as built-in or external speakers and microphones. It can also be used for acoustic testing of other RK3588-based products, such as the S1B.
### The main functionalities are divided into three categories:
#### 1. General Functions: File upload/download, audio recording and playback, etc.
#### 2. Acoustic Analysis: Frequency response and distortion analysis of microphones and speakers, etc.
#### 3. Special Functions (requiring additional devices): Accurate positioning analysis, built-in microphone airtightness testing, audio quality  evaluation using PESQ (Perceptual Evaluation of Speech Quality), etc.


# Environment setting (Ubunutu/Deb as example)

## 1. Install python3 >= 3.11(recommand)
### Be careful, following cmd will change your system python env. Of course, when the problem entercount, you can switch python version back.

```shell
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.11 python3-pip sshpass rsync -y

# method1: change the default python3 to python3.11
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
sudo update-alternatives --config python3
# method2: with conda, create a new env
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda
conda create -name 3.11 python=3.11 -y
source $HOME/miniconda/bin/activate 3.11
conda activate 3.11
# method3: with pyenv, install python3.11
curl https://pyenv.run | bash
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"
pyenv install 3.11.9
pyenv global 3.11.9
```

## 2. Install requirement.txt
``` shell
   pip install -r requirements.txt -i https://pypi.mirrors.ustc.edu.cn/simple
```

## 3. Init bot_acoustic_testing  tool
``` shell
#1. CMD version
./run_test.py --init
#2. GUI version
./ui.py 
```