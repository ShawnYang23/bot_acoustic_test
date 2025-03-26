
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