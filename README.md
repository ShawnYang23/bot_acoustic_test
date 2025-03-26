
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
sudo apt install python3.11 -y

sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
sudo update-alternatives --config python3

```

## 2. Install requirement.txt
``` shell

   pip install -r requirements.txt
```

## 3. Init bot_acoustic_testing  tool
``` shell

   ./run_test.py --init
```