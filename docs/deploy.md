# Deploying to a small VPS (Hetzner)

This runs the bot 24/7 on a cheap virtual server, as a systemd service that restarts on
crashes and reboots. These steps were written for Hetzner Cloud, but any Debian or Ubuntu
VPS works the same after step 1. Prices change, so check the current plan list.

## 0. Before you start

- **Use a separate Discord application for production.** In the Developer Portal, make a
  second application (e.g. `dailyslop-prod`) with its own token and Message Content Intent
  turned on, and invite it to your real server. That way testing locally never takes the
  live bot offline. Follow the "Setup" section of the README for each step.
- **Have an SSH key.** If `ls ~/.ssh/id_ed25519.pub` finds nothing, make one on your own
  computer:

  ```bash
  ssh-keygen -t ed25519 -C "your-label"
  cat ~/.ssh/id_ed25519.pub     # this public half is what you give the provider
  ```

  Set a passphrase when asked.

## 1. Create the server

At <https://console.hetzner.cloud/>:

1. Create an account and a project.
2. **Add Server**:
   - **Location:** any. Discord latency barely depends on it, so pick the cheapest or
     closest.
   - **Image:** Debian 12 or Ubuntu 24.04 (Python 3.11+ is required).
   - **Type:** the smallest shared-vCPU plan. The bot needs very little.
   - **Networking:** keep the public IPv4 address. GitHub and Discord are reachable over
     IPv4, so don't go IPv6-only.
   - **SSH key:** click *Add SSH key* and paste your public key. This is what lets you log in.
   - **Backups:** optional extra (a percentage of the server price). The guide's own daily
     backup covers the database, so you can skip it.
3. Optionally add a **Firewall** that allows inbound SSH (port 22) only. The bot makes
   outbound connections only, so nothing else needs to be open.
4. Create the server and note its IPv4 address.

Connect from your computer:

```bash
ssh root@<server-ip>
```

## 2. Prepare the server

Run these on the server:

```bash
apt update && apt upgrade -y
apt install -y sudo git python3-venv

# A dedicated, login-less user to run the bot
useradd --system --create-home --shell /usr/sbin/nologin dailyslop
```

## 3. Get the code (the repo is private)

Use a read-only deploy key so the server can pull but never push.

```bash
sudo -u dailyslop mkdir -m 700 /home/dailyslop/.ssh
sudo -u dailyslop ssh-keygen -t ed25519 -N '' -C 'dailyslop-vm' -f /home/dailyslop/.ssh/id_ed25519
cat /home/dailyslop/.ssh/id_ed25519.pub
```

Copy that public key. On GitHub, go to the repo's **Settings → Deploy keys → Add deploy
key**, paste it, and leave **Allow write access unchecked**. Then:

```bash
mkdir -p /opt/dailyslop && chown dailyslop:dailyslop /opt/dailyslop
sudo -u dailyslop sh -c 'ssh-keyscan github.com >> /home/dailyslop/.ssh/known_hosts'
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
chmod 600 /opt/dailyslop/.env
sudo -u dailyslop nano .env
```

Leave `DEV_GUILD_ID` empty here, so slash commands register globally. Global sync can take a
little while to show up the first time.

## 5. Start it

```bash
cp deploy/dailyslop.service deploy/dailyslop-backup.service deploy/dailyslop-backup.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now dailyslop.service dailyslop-backup.timer

systemctl status dailyslop        # should say "active (running)"
journalctl -u dailyslop -f        # live logs; look for "Logged in as"
```

The bot should now show as online in your server.

## Everyday operations

| Task | Command |
|---|---|
| Watch logs | `journalctl -u dailyslop -f` |
| Restart | `systemctl restart dailyslop` |
| Stop | `systemctl stop dailyslop` |
| Run a backup now | `systemctl start dailyslop-backup` |
| List backups | `ls -l /opt/dailyslop/backups` |

### Updating the bot

```bash
cd /opt/dailyslop
sudo -u dailyslop git pull
sudo -u dailyslop .venv/bin/pip install -e .
systemctl restart dailyslop
```

### Backups

A timer runs `deploy/backup.py` daily and keeps the last 14 copies in
`/opt/dailyslop/backups/`. It uses SQLite's backup API, so it's safe while the bot runs.

Those copies sit on the same disk as the database, so they don't protect you if the server
is lost. Occasionally copy one to your own machine, from your computer:

```bash
scp root@<server-ip>:/opt/dailyslop/backups/<file>.db .
```

### Restoring

```bash
systemctl stop dailyslop
sudo -u dailyslop cp /opt/dailyslop/backups/<file>.db /opt/dailyslop/data/dailyslop.db
systemctl start dailyslop
```

## Security notes

- The production token lives only in `/opt/dailyslop/.env` (mode 600). If it ever leaks,
  click **Reset Token** in the Developer Portal and update the file.
- Log in with your SSH key only. Hetzner disables password login when you add a key at
  creation. Keep your private key's passphrase on.
- The deploy key is read-only. If the server is compromised, delete it under the repo's
  Deploy keys.
- Keep the OS patched: `apt update && apt upgrade -y` every so often, or enable
  `unattended-upgrades`.
