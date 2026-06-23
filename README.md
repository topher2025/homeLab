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

## Postgres
Run a minimal local Postgres container with:

```bash
docker compose up -d postgres
```

It uses `postgres/password`, database `mydb`, and exposes port `5432`.