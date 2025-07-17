
# Tool Description

### This tool is used for sound-related testing and bug troubleshooting for the product vibe-bot, primarily targeting devices such as built-in or external speakers and microphones. It can also be used for acoustic testing of other RK3588-based products, such as the S1B.
### The main functionalities are divided into three categories:
#### 1. General Functions: File upload/download, audio recording and playback, etc.
#### 2. Acoustic Analysis: Frequency response and distortion analysis of microphones and speakers, etc.
#### 3. Special Functions (requiring additional devices): Accurate positioning analysis, built-in microphone airtightness testing, audio quality  evaluation using PESQ (Perceptual Evaluation of Speech Quality), etc.


# Environment setting (Ubunutu/Deb as example)
# Linux System
## 1. Install python3 >= 3.11(recommand)
### Be careful, following cmd will change your system python env. Of course, when the problem entercount, you can switch python version back.

```shell
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.11 python3-pip sshpass rsync ffmpeg -y

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
python ./ui.py 
```

# Windows Sytem
## 1. Download and install windows requirements based on your PC
###
[git](https://git-scm.com/downloads/win) \
[python3.11](https://www.python.org/downloads/windows/) \
[vs_BuildTools](https://visualstudio.microsoft.com/zh-hans/visual-cpp-build-tools/)\
[ffmpeg](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z)： Unzip this file into a known path

## 2. Setup environment (powershell)
``` powershell
  # get python related path
  py -3.11 -c "import sys; print(sys.executable)" 
  #eg. get: C:\Users\jmysy\AppData\Local\Programs\Python\Python311\python.exe
```
### List required environment path
[PY_PATH]: "C:\Users\jmysy\AppData\Local\Programs\Python\Python311" \
[PIP_PATH]: "C:\Users\jmysy\AppData\Local\Programs\Python\Python311/Scripts" \
[FFMPEG_PATH]: /your/path/to/ffmpeg/bin/
### Add these [PY_PATH PIP_PATH FFMPEG_PATH] to win environment (recommanded adding as the first items), following under directio:
[Search]->[Edit System Environment Varibles]->[Environment Varibles]->[Path]->[NEW]

## 3. Install requirement.txt
``` shell
pip install -r requirements.txt -i https://pypi.mirrors.ustc.edu.cn/simple
```

## 4. Init bot_acoustic_testing  tool
``` shell
#Only GUI version
py ./ui.py 
```