# Deploying to a small VPS (Hetzner)

This runs the bot 24/7 on a cheap virtual server, as a systemd service that restarts on
crashes and reboots. These steps were written for Hetzner Cloud, but any Debian or Ubuntu
VPS works the same after step 1. Prices change, so check the current plan list.

## 0. Before you start

- **Use a separate Discord application for production** (recommended). In the Developer
  Portal, make a second application (e.g. `dailyslop-prod`) with its own token, turn on
  both the **Message Content** and **Server Members** intents, and invite it to your real
  server. That way testing locally never takes the live bot offline. Follow the "Setup"
  section of the README for each step.
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

## 2. Lock the server down (do this first)

Servers start with root login. Make a normal admin user and turn root login off before
doing anything else. **Keep your root session open until step 2d proves the new login works,**
otherwise a typo can lock you out.

**2a. Log in as root and create the admin user:**

```bash
ssh root@<server-ip>

apt update && apt upgrade -y
apt install -y sudo git python3-venv

adduser --disabled-password --gecos "" admin
usermod -aG sudo admin
echo 'admin ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/90-admin
chmod 440 /etc/sudoers.d/90-admin && visudo -cf /etc/sudoers.d/90-admin

mkdir -p /home/admin/.ssh
cp /root/.ssh/authorized_keys /home/admin/.ssh/
chown -R admin:admin /home/admin/.ssh
chmod 700 /home/admin/.ssh && chmod 600 /home/admin/.ssh/authorized_keys
```

`admin` has no password, so only your SSH key can log in as it. That is also why `sudo` is
passwordless. Your key's passphrase is what protects it.

**2b. In a second terminal on your computer, test the new login:**

```bash
ssh admin@<server-ip> 'sudo whoami'      # must print: root
```

**2c. Back in the root session, turn off root and password logins:**

```bash
cat > /etc/ssh/sshd_config.d/00-hardening.conf <<'EOF'
PermitRootLogin no
PasswordAuthentication no
EOF
sshd -t && systemctl reload ssh
```

The `00-` prefix matters: SSH uses the first value it reads, and cloud images can ship their
own drop-in files that would otherwise win. `sshd -t` checks the syntax before reloading.

**2d. In a third terminal, confirm:**

```bash
ssh admin@<server-ip> 'sudo whoami'      # still works
ssh root@<server-ip>                     # now refused
```

Only then close the root session. From here on, log in as `admin`. A handy shortcut is an
entry in `~/.ssh/config` on your computer:

```
Host slothbots
    HostName <server-ip>
    User admin
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
```

so that `ssh slothbots` works.

## 3. Create the bot's user and get the code

Run these as `admin`. The bot runs as its own login-less user, and the server pulls the code
with a read-only deploy key, so it can never push. (The deploy key is only needed for a private
repo. For a public one, skip the key steps and clone over `https://`.)

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin dailyslop

sudo -u dailyslop mkdir -m 700 /home/dailyslop/.ssh
sudo -u dailyslop ssh-keygen -t ed25519 -N '' -C 'dailyslop-vm' -f /home/dailyslop/.ssh/id_ed25519
sudo cat /home/dailyslop/.ssh/id_ed25519.pub
```

Copy that public key. On GitHub, go to the repo's **Settings → Deploy keys → Add deploy
key**, paste it, and leave **Allow write access unchecked**. Then:

```bash
sudo mkdir -p /opt/dailyslop && sudo chown dailyslop:dailyslop /opt/dailyslop
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

If `journalctl` says you have no permission to read the journal, prefix it with `sudo`.
The bot should now show as online in your server.

## Everyday operations

| Task | Command |
|---|---|
| Watch logs | `sudo journalctl -u dailyslop -f` |
| Restart | `sudo systemctl restart dailyslop` |
| Stop | `sudo systemctl stop dailyslop` |
| Run a backup now | `sudo systemctl start dailyslop-backup` |
| List backups | `ls -l /opt/dailyslop/backups` |
| Check backups are healthy | `sudo bash /opt/dailyslop/deploy/check-backup.sh` |

### Updating the bot

```bash
cd /opt/dailyslop
sudo systemctl start dailyslop-backup      # first, if the release notes mention a migration
sudo -u dailyslop git pull
sudo -u dailyslop .venv/bin/pip install -e .
sudo systemctl restart dailyslop
sleep 5; sudo journalctl -u dailyslop --since "1 min ago" --no-pager
```

The last line should show `Logged in as ...` and no traceback. Database migrations run
automatically on start and only add to the data, but take the backup anyway when a release
changes the schema. New slash commands can take a while to appear in Discord.

### Backups

A timer runs `deploy/backup.py` daily and keeps the last 14 copies in
`/opt/dailyslop/backups/`. It uses SQLite's backup API, so it's safe while the bot runs.

Those copies sit on the same disk as the database, so they don't protect you if the server
is lost. Occasionally copy one to your own machine, from your computer:

```bash
scp slothbots:/opt/dailyslop/backups/<file>.db .
```

### Restoring

```bash
sudo systemctl stop dailyslop
sudo -u dailyslop cp /opt/dailyslop/backups/<file>.db /opt/dailyslop/data/dailyslop.db
sudo systemctl start dailyslop
```

## Security notes

- The production token lives only in `/opt/dailyslop/.env` (mode 600). If it ever leaks,
  click **Reset Token** in the Developer Portal and update the file.
- Root login and password login over SSH are both off (step 2). Keep your private key's
  passphrase on, since the key is the only way in.
- The deploy key is read-only. If the server is compromised, delete it under the repo's
  Deploy keys.
- Keep the OS patched: `sudo apt update && sudo apt upgrade -y` every so often, or enable
  `unattended-upgrades`.
- If you ever lock yourself out, the Hetzner console can attach a rescue system or reset
  access to the server.
