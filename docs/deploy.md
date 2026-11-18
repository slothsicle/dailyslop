# Deploying to a Google Cloud e2-micro

This runs the bot 24/7 on Google Cloud's Always Free VM, as a systemd service that
restarts on crashes and reboots. Free-tier terms change, so check the current rules at
<https://cloud.google.com/free/docs/free-cloud-features> before you start.

## 0. Before you start

- **Use a separate Discord application for production.** In the Developer Portal, make a
  second application (e.g. `dailyslop-prod`) with its own token and Message Content Intent
  turned on, and invite it to your real server. That way testing locally never takes the
  live bot offline. Follow the "Setup" section of the README for each step.
- You need a Google account and a credit card (Google requires one on file, even for the
  free tier).

## 1. Create the VM

In the [Google Cloud Console](https://console.cloud.google.com/):

1. Create a project (or use the default) and **enable billing** for it.
2. **Set a budget alert first**: *Billing → Budgets & alerts → Create budget*, for $1, so a
   mistake can't quietly cost money.
3. *Compute Engine → VM instances → Create instance*:
   - **Region:** one of `us-west1`, `us-central1` or `us-east1`. The free tier only covers
     these.
   - **Machine type:** `e2-micro` (under *Shared-core*).
   - **Boot disk:** Debian 12 or Ubuntu 24.04 LTS (Python 3.11+ is required). Set the disk
     type to **Standard persistent disk**, not the default Balanced one. The free tier only
     covers standard, up to 30 GB; 10 GB is plenty.
   - **Firewall:** leave HTTP and HTTPS unchecked. The bot only makes outbound connections.
4. **Check the estimated monthly cost** on the right side of the page before clicking
   Create. It should show the free-tier discount. I'm not certain how Google currently
   treats the VM's external IPv4 address; if the estimate shows a small charge for it, that
   is the IP, and you should decide whether it's acceptable. Don't reserve a static IP.
5. Click **Create**, then use the **SSH** button next to the VM to open a browser terminal.
   No key setup is needed.

## 2. Prepare the server

In the SSH terminal:

```bash
sudo apt update && sudo apt install -y git python3-venv

# Optional but sensible on a 1 GB machine: 1 GB of swap
sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# A dedicated, login-less user to run the bot
sudo useradd --system --create-home --shell /usr/sbin/nologin dailyslop
```

## 3. Get the code (the repo is private)

Use a read-only deploy key so the server can pull but never push.

```bash
sudo mkdir -p /opt/dailyslop && sudo chown dailyslop:dailyslop /opt/dailyslop
sudo -u dailyslop mkdir -m 700 /home/dailyslop/.ssh
sudo -u dailyslop ssh-keygen -t ed25519 -N '' -C 'dailyslop-vm' -f /home/dailyslop/.ssh/id_ed25519
sudo cat /home/dailyslop/.ssh/id_ed25519.pub
```

Copy that public key. On GitHub, go to the repo's **Settings → Deploy keys → Add deploy
key**, paste it, and leave **Allow write access unchecked**. Then:

```bash
sudo -u dailyslop ssh-keyscan github.com | sudo -u dailyslop tee -a /home/dailyslop/.ssh/known_hosts
sudo -u dailyslop git clone git@github.com:slothsicle/dailyslop.git /opt/dailyslop
```

## 4. Install and configure

```bash
cd /opt/dailyslop
sudo -u dailyslop python3 -m venv .venv
sudo -u dailyslop .venv/bin/pip install -e .
sudo -u dailyslop mkdir -p data backups

# Create the config. Paste your PRODUCTION token after DISCORD_TOKEN=
sudo -u dailyslop cp .env.example .env
sudo chmod 600 /opt/dailyslop/.env
sudo -u dailyslop nano .env
```

Leave `DEV_GUILD_ID` empty here, so slash commands register globally. Global sync can take a
little while to show up the first time.

## 5. Start it

```bash
sudo cp deploy/dailyslop.service deploy/dailyslop-backup.service deploy/dailyslop-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now dailyslop.service dailyslop-backup.timer

systemctl status dailyslop        # should say "active (running)"
journalctl -u dailyslop -f        # live logs; look for "Logged in as"
```

The bot should now show as online in your server.

## Everyday operations

| Task | Command |
|---|---|
| Watch logs | `journalctl -u dailyslop -f` |
| Restart | `sudo systemctl restart dailyslop` |
| Stop | `sudo systemctl stop dailyslop` |
| Run a backup now | `sudo systemctl start dailyslop-backup` |
| List backups | `ls -l /opt/dailyslop/backups` |

### Updating the bot

```bash
cd /opt/dailyslop
sudo -u dailyslop git pull
sudo -u dailyslop .venv/bin/pip install -e .
sudo systemctl restart dailyslop
```

### Backups

A timer runs `deploy/backup.py` daily and keeps the last 14 copies in
`/opt/dailyslop/backups/`. It uses SQLite's backup API, so it's safe while the bot runs.

Those copies sit on the same disk as the database, so they don't protect you if the VM is
lost. Occasionally copy one to your own machine, for example from your computer:

```bash
gcloud compute scp --zone <zone> <vm-name>:/opt/dailyslop/backups/<file>.db .
```

(That reads the file as your own VM user, so you may need to `sudo cp` it somewhere your
user can read first.)

### Restoring

```bash
sudo systemctl stop dailyslop
sudo -u dailyslop cp /opt/dailyslop/backups/<file>.db /opt/dailyslop/data/dailyslop.db
sudo systemctl start dailyslop
```

## Security notes

- The production token lives only in `/opt/dailyslop/.env` (mode 600). If it ever leaks,
  click **Reset Token** in the Developer Portal and update the file.
- The VM has no inbound ports open except SSH through Google's console tooling.
- The deploy key is read-only. If the VM is compromised, delete it under the repo's
  Deploy keys.
