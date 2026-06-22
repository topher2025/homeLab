# homeLab
Stuff for my home lab


## `infra/`
```
# from downloading machine
scp -r infra/ user@target:/opt/homeLab/infra/

# from target machine
cd /opt/homeLab/infra
python -m pip install --no-index --find-links=wheelhouse -r requirements.txt
sudo python run_all.py
```
## Goals
Olama
Webserver