#!/usr/bin/env bash
# ==============================================================================
# SIAGA VPS Hardening & Security Provisioning Script (T09)
# Designed for Ubuntu 22.04 / 24.04 LTS on Cloud VPS
#
# HARD SECURITY SPECIFICATIONS:
# 1. Non-root user with sudo privileges.
# 2. SSH Key-Only authentication (PasswordAuthentication NO, PermitRootLogin NO).
# 3. UFW Firewall: Default DENY incoming, allow SSH (22/tcp).
# 4. OpenClaw Gateway (18789) strictly isolated to localhost (NEVER exposed to 0.0.0.0).
# 5. Automated security patches via unattended-upgrades.
# 6. Fail2ban active protection for SSH.
# ==============================================================================

set -euo pipefail

# Text formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}=================================================================${NC}"
echo -e "${CYAN}   SIAGA Cloud VPS Hardening & Security Provisioning (T09)       ${NC}"
echo -e "${CYAN}=================================================================${NC}"

# Ensure script is executed with root privileges
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}[ERROR] Skrip ini harus dijalankan sebagai root (atau via sudo).${NC}" >&2
   exit 1
fi

TARGET_USER="${1:-siaga}"
# Detect configured SSH port from sshd_config or default to $2 / 4422 / 22
DETECTED_PORT=$(grep -E '^[# ]*Port ' /etc/ssh/sshd_config 2>/dev/null | grep -v '^#' | awk '{print $2}' | head -n 1 || true)
SSH_PORT="${2:-${DETECTED_PORT:-4422}}"

echo -e "${CYAN}[INFO] Target User: '${TARGET_USER}', Target SSH Port: ${SSH_PORT}${NC}"

echo -e "${YELLOW}[1/6] Memperbarui paket sistem dan memasang utilitas keamanan...${NC}"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
    ufw \
    fail2ban \
    unattended-upgrades \
    apt-listchanges \
    curl \
    git \
    sudo \
    python3 \
    python3-venv \
    python3-pip

echo -e "${GREEN}[OK] Paket dasar terpasang.${NC}"

# ------------------------------------------------------------------------------
# 2. Setup Non-Root User
# ------------------------------------------------------------------------------
echo -e "${YELLOW}[2/6] Memeriksa / Membuat user non-root '${TARGET_USER}'...${NC}"
if id "$TARGET_USER" &>/dev/null; then
    echo -e "${GREEN}[INFO] User '${TARGET_USER}' sudah ada.${NC}"
else
    useradd -m -s /bin/bash "$TARGET_USER"
    usermod -aG sudo "$TARGET_USER"
    echo -e "${GREEN}[OK] User '${TARGET_USER}' berhasil dibuat dan dimasukkan ke grup sudo.${NC}"
fi

# Setup SSH directory for user
USER_SSH_DIR="/home/${TARGET_USER}/.ssh"
mkdir -p "$USER_SSH_DIR"
chmod 700 "$USER_SSH_DIR"
touch "$USER_SSH_DIR/authorized_keys"
chmod 600 "$USER_SSH_DIR/authorized_keys"
chown -R "${TARGET_USER}:${TARGET_USER}" "$USER_SSH_DIR"

# Copy root authorized_keys if available and target is empty
if [[ -f /root/.ssh/authorized_keys ]] && [[ ! -s "$USER_SSH_DIR/authorized_keys" ]]; then
    cp /root/.ssh/authorized_keys "$USER_SSH_DIR/authorized_keys"
    chown -R "${TARGET_USER}:${TARGET_USER}" "$USER_SSH_DIR"
    echo -e "${GREEN}[INFO] Menyalin authorized_keys dari root ke '${TARGET_USER}'.${NC}"
fi

# ------------------------------------------------------------------------------
# 3. SSH Daemon Hardening
# ------------------------------------------------------------------------------
echo -e "${YELLOW}[3/6] Mengonfigurasi hardening SSH (Key-Only, No Root, No Password)...${NC}"
SSHD_CONF_DIR="/etc/ssh/sshd_config.d"
mkdir -p "$SSHD_CONF_DIR"

# Clean up cloud-init overrides if present so our policy is absolute
rm -f "$SSHD_CONF_DIR/50-cloud-init.conf" "$SSHD_CONF_DIR/60-cloudimg-settings.conf" 2>/dev/null || true

cat << 'EOF' > "$SSHD_CONF_DIR/00-siaga-hardening.conf"
# SIAGA Hardened SSH Configuration (T09)
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
MaxAuthTries 3
X11Forwarding no
AllowAgentForwarding yes
ClientAliveInterval 300
ClientAliveCountMax 2
EOF

# Test SSH configuration before reloading
if sshd -t; then
    systemctl restart ssh || systemctl restart sshd || service ssh restart || true
    echo -e "${GREEN}[OK] Konfigurasi SSH valid dan di-restart.${NC}"
else
    echo -e "${RED}[ERROR] Konfigurasi SSH tidak valid! Mengembalikan perubahan...${NC}"
    rm -f "$SSHD_CONF_DIR/00-siaga-hardening.conf"
    exit 1
fi

# ------------------------------------------------------------------------------
# 4. Firewall (UFW) Hardening
# ------------------------------------------------------------------------------
echo -e "${YELLOW}[4/6] Mengonfigurasi UFW Firewall...${NC}"
ufw --force reset >/dev/null 2>&1 || true

# Default policies
ufw default deny incoming
ufw default allow outgoing

# Allow SSH on configured port
ufw allow "${SSH_PORT}/tcp" comment "SSH Port ${SSH_PORT}"

# OpenClaw Gateway 18789 is strictly loopback only. UFW denies all incoming by default.
# Only local process or SSH tunnel to 127.0.0.1 can reach it.

ufw --force enable
echo -e "${GREEN}[OK] UFW aktif dengan proteksi default DENY incoming (SSH port ${SSH_PORT} diizinkan).${NC}"

# ------------------------------------------------------------------------------
# 5. Fail2ban & Unattended Upgrades
# ------------------------------------------------------------------------------
echo -e "${YELLOW}[5/6] Mengaktifkan Fail2ban dan Unattended Upgrades...${NC}"
cat << EOF > /etc/fail2ban/jail.local
[DEFAULT]
bantime = 1h
findtime = 10m
maxretry = 3
backend = systemd

[sshd]
enabled = true
port = ${SSH_PORT}
EOF

systemctl enable fail2ban >/dev/null 2>&1 || true
systemctl restart fail2ban >/dev/null 2>&1 || true

# Configure unattended-upgrades
cat << 'EOF' > /etc/apt/apt.conf.d/20auto-upgrades
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF

echo -e "${GREEN}[OK] Fail2ban dan update keamanan otomatis aktif.${NC}"

# ------------------------------------------------------------------------------
# 6. Summary & Verification Checklist
# ------------------------------------------------------------------------------
echo -e "${CYAN}=================================================================${NC}"
echo -e "${GREEN}   HARDENING VPS BERHASIL DIKONFIGURASI!                         ${NC}"
echo -e "${CYAN}=================================================================${NC}"
echo -e "Status UFW Firewall:"
ufw status verbose
echo ""
echo -e "${YELLOW}LANGKAH VERIFIKASI & MANUAL WAJIB OLEH OPERATOR:${NC}"
echo -e "1. ${CYAN}JANGAN TUTUP${NC} sesi terminal saat ini sebelum mengetes login baru!"
echo -e "2. Buka terminal baru di komputer lokal dan tes login:"
echo -e "   ${GREEN}ssh -i ~/.ssh/id_ed25519 ${TARGET_USER}@<IP_VPS>${NC}"
echo -e "3. Pastikan login berhasil TANPA meminta password (pure SSH key)."
echo -e "4. Verifikasi bahwa login root langsung DITOLAK:"
echo -e "   ${GREEN}ssh root@<IP_VPS>${NC} -> (harus ditolak / Permission denied)"
echo -e "5. Untuk mengakses dashboard / OpenClaw dari lokal, gunakan SSH tunnel:"
echo -e "   ${GREEN}ssh -N -L 8000:127.0.0.1:8000 -L 18789:127.0.0.1:18789 ${TARGET_USER}@<IP_VPS>${NC}"
echo -e "${CYAN}=================================================================${NC}"
