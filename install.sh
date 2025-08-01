#!/bin/bash
# Milo Audio System - Installation Script v1.1

set -e

MILO_USER="milo"
MILO_HOME="/home/$MILO_USER"
MILO_APP_DIR="$MILO_HOME/milo"
MILO_DATA_DIR="/var/lib/milo"
MILO_REPO="https://github.com/Leshauts/Milo.git"
REQUIRED_HOSTNAME="milo"
REBOOT_REQUIRED=false

# Variables pour stocker les choix utilisateur
USER_HOSTNAME_CHANGE=""
USER_HIFIBERRY_CHOICE=""
USER_RESTART_CHOICE=""
HIFIBERRY_OVERLAY=""
CARD_NAME=""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_banner() {
    echo -e "${BLUE}"
    echo "  __  __ _ _       "
    echo " |  \/  (_) | ___  "
    echo " | |\/| | | |/ _ \ "
    echo " | |  | | | | (_) |"
    echo " |_|  |_|_|_|\___/ "
    echo ""
    echo "Audio System Installation Script v1.1"
    echo -e "${NC}"
}

check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "Ce script ne doit pas être exécuté en tant que root."
        exit 1
    fi
}

check_system() {
    log_info "Vérification du système..."
    
    if ! grep -q "Raspberry Pi" /proc/cpuinfo; then
        log_error "Ce script est conçu pour Raspberry Pi uniquement."
        exit 1
    fi
    
    ARCH=$(uname -m)
    if [[ "$ARCH" != "aarch64" ]]; then
        log_error "Architecture non supportée: $ARCH. Raspberry Pi OS 64bit requis."
        exit 1
    fi
    
    log_success "Système compatible détecté"
}

# ===============================
# NOUVELLE FONCTION POUR COLLECTER TOUS LES CHOIX
# ===============================
collect_user_choices() {
    echo ""
    log_info "Configuration initiale - Répondez aux questions suivantes :"
    echo ""
    
    # 1. Vérification du hostname
    local current_hostname=$(hostname)
    log_info "Hostname actuel: $current_hostname"
    
    if [ "$current_hostname" != "$REQUIRED_HOSTNAME" ]; then
        echo ""
        echo -e "${YELLOW}⚠️  IMPORTANT:${NC} Milo nécessite le hostname '${REQUIRED_HOSTNAME}' pour:"
        echo "   • Accès via ${REQUIRED_HOSTNAME}.local depuis le navigateur"
        echo "   • Fonctionnement optimal du multiroom (Snapserver)"
        echo "   • Découverte réseau des autres instances Milo"
        echo ""
        echo -e "${BLUE}🔄 Changement de hostname requis:${NC} '$current_hostname' → '$REQUIRED_HOSTNAME'"
        echo ""
        
        while true; do
            read -p "Changer le hostname vers '$REQUIRED_HOSTNAME' ? (O/n): " USER_HOSTNAME_CHANGE
            case $USER_HOSTNAME_CHANGE in
                [Nn]* )
                    log_error "Installation annulée. Le hostname '$REQUIRED_HOSTNAME' est requis."
                    exit 1
                    ;;
                [Oo]* | "" )
                    USER_HOSTNAME_CHANGE="yes"
                    break
                    ;;
                * )
                    echo "Veuillez répondre par 'O' (oui) ou 'n' (non)."
                    ;;
            esac
        done
    else
        USER_HOSTNAME_CHANGE="already_set"
    fi
    
    # 2. Choix de la carte HiFiBerry
    echo ""
    log_info "Configuration de la carte audio HiFiBerry..."
    echo ""
    echo "Sélectionnez votre carte audio HiFiBerry:"
    echo ""
    echo "1) Amp2"
    echo "2) Amp4"
    echo "3) Amp4 Pro"
    echo "4) Amp100"
    echo "5) Beocreate 4CA"
    echo "6) Ignorer (pas de HiFiBerry)"
    echo ""
    
    while true; do
        read -p "Votre choix [1]: " USER_HIFIBERRY_CHOICE
        USER_HIFIBERRY_CHOICE=${USER_HIFIBERRY_CHOICE:-1}
        
        case $USER_HIFIBERRY_CHOICE in
            1) HIFIBERRY_OVERLAY="hifiberry-dacplus-std"; CARD_NAME="sndrpihifiberry"; log_success "Carte sélectionnée: Amp2"; break;;
            2) HIFIBERRY_OVERLAY="hifiberry-dacplus-std"; CARD_NAME="sndrpihifiberry"; log_success "Carte sélectionnée: Amp4"; break;;
            3) HIFIBERRY_OVERLAY="hifiberry-amp4pro"; CARD_NAME="sndrpihifiberry"; log_success "Carte sélectionnée: Amp4 Pro"; break;;
            4) HIFIBERRY_OVERLAY="hifiberry-amp100"; CARD_NAME="sndrpihifiberry"; log_success "Carte sélectionnée: Amp100"; break;;
            5) HIFIBERRY_OVERLAY="hifiberry-dac"; CARD_NAME="sndrpihifiberry"; log_success "Carte sélectionnée: Beocreate 4CA"; break;;
            6) HIFIBERRY_OVERLAY=""; CARD_NAME=""; log_warning "Configuration HiFiBerry ignorée"; break;;
            *) echo "Choix invalide. Veuillez entrer un nombre entre 1 et 6.";;
        esac
    done
    
    # 3. Choix du redémarrage (on le demande maintenant mais on l'utilisera à la fin)
    echo ""
    log_info "Un redémarrage sera nécessaire à la fin de l'installation."
    while true; do
        read -p "Redémarrer automatiquement à la fin ? (O/n): " USER_RESTART_CHOICE
        case $USER_RESTART_CHOICE in
            [Nn]* )
                USER_RESTART_CHOICE="no"
                break
                ;;
            [Oo]* | "" )
                USER_RESTART_CHOICE="yes"
                break
                ;;
            * )
                echo "Veuillez répondre par 'O' (oui) ou 'n' (non)."
                ;;
        esac
    done
    
    echo ""
    log_success "Configuration terminée ! L'installation va maintenant se poursuivre automatiquement..."
    echo ""
    sleep 2
}

# ===============================
# FONCTIONS MODIFIÉES POUR UTILISER LES VARIABLES
# ===============================

setup_hostname() {
    local current_hostname=$(hostname)
    
    log_info "Application de la configuration hostname..."
    
    if [ "$USER_HOSTNAME_CHANGE" == "yes" ]; then
        log_info "Configuration du hostname '$REQUIRED_HOSTNAME'..."
        configure_hostname "$REQUIRED_HOSTNAME"
        log_success "Hostname configuré"
        REBOOT_REQUIRED=true
    elif [ "$USER_HOSTNAME_CHANGE" == "already_set" ]; then
        log_success "Hostname '$REQUIRED_HOSTNAME' déjà configuré"
    fi
}

configure_hostname() {
    local new_hostname="$1"
    echo "$new_hostname" | sudo tee /etc/hostname > /dev/null
    sudo sed -i "s/127.0.1.1.*/127.0.1.1\t$new_hostname/" /etc/hosts
    sudo hostnamectl set-hostname "$new_hostname"
}

configure_audio_hardware() {
    if [[ -z "$HIFIBERRY_OVERLAY" ]]; then
        log_info "Configuration HiFiBerry ignorée"
        return
    fi
    
    log_info "Configuration du hardware audio pour HiFiBerry..."
    
    local config_file="/boot/firmware/config.txt"
    
    if [[ ! -f "$config_file" ]]; then
        config_file="/boot/config.txt"
        if [[ ! -f "$config_file" ]]; then
            log_error "Fichier config.txt non trouvé"
            exit 1
        fi
    fi
    
    sudo cp "$config_file" "$config_file.backup.$(date +%Y%m%d_%H%M%S)"
    
    sudo sed -i '/^dtparam=audio=on/d' "$config_file"
    
    if grep -q "vc4-fkms-v3d" "$config_file"; then
        sudo sed -i 's/dtoverlay=vc4-fkms-v3d.*/dtoverlay=vc4-fkms-v3d,audio=off/' "$config_file"
    fi
    
    if grep -q "vc4-kms-v3d" "$config_file"; then
        sudo sed -i 's/dtoverlay=vc4-kms-v3d.*/dtoverlay=vc4-kms-v3d,noaudio/' "$config_file"
    fi
    
    if ! grep -q "$HIFIBERRY_OVERLAY" "$config_file"; then
        echo "" | sudo tee -a "$config_file"
        echo "#AMP2" | sudo tee -a "$config_file"
        echo "dtoverlay=$HIFIBERRY_OVERLAY" | sudo tee -a "$config_file"
    fi
    
    if ! grep -q "usb_max_current_enable=1" "$config_file"; then
        echo "usb_max_current_enable=1" | sudo tee -a "$config_file"
    fi
    
    log_success "Configuration audio hardware terminée"
    REBOOT_REQUIRED=true
}

install_dependencies() {
    log_info "Mise à jour du système..."
    
    export DEBIAN_FRONTEND=noninteractive
    export DEBCONF_NONINTERACTIVE_SEEN=true
    
    echo 'Dpkg::Options {
       "--force-confdef";
       "--force-confnew";
    }' | sudo tee /etc/apt/apt.conf.d/local >/dev/null
    
    sudo apt update
    sudo apt upgrade -y
    
    log_info "Installation des dépendances de base..."
    sudo apt install -y git python3-pip python3-venv python3-dev libasound2-dev libssl-dev \
    cmake build-essential pkg-config nodejs npm
    
    log_info "Mise à jour de Node.js et npm..."
    sudo npm install -g n
    sudo n stable
    sudo npm install -g npm@latest
    hash -r
    
    sudo rm -f /etc/apt/apt.conf.d/local
    
    log_success "Dépendances installées"
}

create_milo_user() {
    if id "$MILO_USER" &>/dev/null; then
        log_info "Utilisateur '$MILO_USER' existe déjà"
    else
        log_info "Création de l'utilisateur '$MILO_USER'..."
        sudo useradd -m -s /bin/bash -G audio,sudo "$MILO_USER"
        log_success "Utilisateur '$MILO_USER' créé"
    fi
    
    sudo mkdir -p "$MILO_DATA_DIR"
    sudo chown -R "$MILO_USER:audio" "$MILO_DATA_DIR"
}

install_milo_application() {
    log_info "Clonage et configuration de Milo..."
    
    if [[ -d "$MILO_APP_DIR" ]]; then
        log_warning "Le répertoire $MILO_APP_DIR existe déjà, suppression..."
        sudo rm -rf "$MILO_APP_DIR"
    fi
    
    sudo -u "$MILO_USER" git clone "$MILO_REPO" "$MILO_APP_DIR"
    cd "$MILO_APP_DIR"
    
    log_info "Configuration de l'environnement Python..."
    sudo -u "$MILO_USER" python3 -m venv venv
    sudo -u "$MILO_USER" bash -c "source venv/bin/activate && pip install --upgrade pip"
    sudo -u "$MILO_USER" bash -c "source venv/bin/activate && pip install -r requirements.txt"
    
    log_info "Compilation du frontend..."
    cd frontend
    sudo -u "$MILO_USER" npm install
    sudo -u "$MILO_USER" npm run build
    cd ..
    
    log_success "Application Milo installée"
}

suppress_pulseaudio() {
    log_info "Suppression de PulseAudio/PipeWire..."
    sudo apt remove -y pulseaudio pipewire || true
    sudo apt autoremove -y
    log_success "PulseAudio/PipeWire supprimés"
}

install_go_librespot() {
    log_info "Installation de go-librespot..."
    
    sudo apt-get install -y libogg-dev libvorbis-dev libasound2-dev
    
    local temp_dir=$(mktemp -d)
    cd "$temp_dir"
    
    wget https://github.com/devgianlu/go-librespot/releases/download/v0.3.1/go-librespot_linux_arm64.tar.gz
    tar -xvzf go-librespot_linux_arm64.tar.gz
    sudo cp go-librespot /usr/local/bin/
    sudo chmod +x /usr/local/bin/go-librespot
    
    sudo mkdir -p "$MILO_DATA_DIR/go-librespot"
    sudo chown -R "$MILO_USER:audio" "$MILO_DATA_DIR/go-librespot"
    
    sudo tee "$MILO_DATA_DIR/go-librespot/config.yml" > /dev/null << 'EOF'
device_name: "Milo"
device_type: "speaker"
bitrate: 320

audio_backend: "alsa"
audio_device: "milo_spotify"

external_volume: true

server:
  enabled: true
  address: "0.0.0.0"
  port: 3678
  allow_origin: "*"
EOF
    
    sudo chown -R "$MILO_USER:audio" "$MILO_DATA_DIR/go-librespot"
    
    cd ~
    rm -rf "$temp_dir"
    
    log_success "go-librespot installé"
}

install_roc_toolkit() {
    log_info "Installation de roc-toolkit..."
    
    sudo apt install -y g++ pkg-config scons ragel gengetopt libuv1-dev \
      libspeexdsp-dev libunwind-dev libsox-dev libsndfile1-dev libssl-dev libasound2-dev \
      libtool intltool autoconf automake make cmake avahi-utils libpulse-dev
    
    local temp_dir=$(mktemp -d)
    cd "$temp_dir"
    
    git clone https://github.com/roc-streaming/roc-toolkit.git
    cd roc-toolkit
    scons -Q --build-3rdparty=openfec
    sudo scons -Q --build-3rdparty=openfec install
    sudo ldconfig
    
    cd ~
    rm -rf "$temp_dir"
    
    roc-recv --version
    
    log_success "roc-toolkit installé"
}

install_bluez_alsa() {
    log_info "Installation de bluez-alsa..."
    
    sudo apt install -y \
      libasound2-dev \
      libbluetooth-dev \
      libdbus-1-dev \
      libglib2.0-dev \
      libsbc-dev \
      bluez \
      bluez-tools \
      pkg-config \
      build-essential \
      autotools-dev \
      automake \
      libtool
    
    REBOOT_REQUIRED=true
    
    local temp_dir=$(mktemp -d)
    cd "$temp_dir"
    
    git clone https://github.com/arkq/bluez-alsa.git
    cd bluez-alsa
    git checkout v4.3.1
    
    autoreconf --install
    mkdir build && cd build
    
    ../configure --prefix=/usr --enable-systemd \
      --with-alsaplugindir=/usr/lib/aarch64-linux-gnu/alsa-lib \
      --with-bluealsauser="$MILO_USER" --with-bluealsaaplayuser="$MILO_USER" \
      --enable-cli
    
    make -j$(nproc)
    sudo make install
    sudo ldconfig
    
    cd ~
    rm -rf "$temp_dir"
    
    sudo systemctl stop bluealsa-aplay.service bluealsa.service || true
    sudo systemctl disable bluealsa-aplay.service bluealsa.service || true
    
    log_success "bluez-alsa installé"
}

install_snapcast() {
    log_info "Installation de Snapcast..."
    
    local temp_dir=$(mktemp -d)
    cd "$temp_dir"
    
    wget https://github.com/badaix/snapcast/releases/download/v0.31.0/snapserver_0.31.0-1_arm64_bookworm.deb
    wget https://github.com/badaix/snapcast/releases/download/v0.31.0/snapclient_0.31.0-1_arm64_bookworm.deb
    
    sudo apt install -y ./snapserver_0.31.0-1_arm64_bookworm.deb
    sudo apt install -y ./snapclient_0.31.0-1_arm64_bookworm.deb
    
    cd ~
    rm -rf "$temp_dir"
    
    snapserver --version
    snapclient --version
    
    sudo systemctl stop snapserver.service snapclient.service || true
    sudo systemctl disable snapserver.service snapclient.service || true
    
    log_success "Snapcast installé"
}

create_systemd_services() {
    log_info "Création des services systemd..."
    
    # milo-backend.service
    sudo tee /etc/systemd/system/milo-backend.service > /dev/null << 'EOF'
[Unit]
Description=Milo Backend Service
After=network.target

[Service]
Type=simple
User=milo
Group=milo
WorkingDirectory=/home/milo/milo
ExecStart=/home/milo/milo/venv/bin/python3 backend/main.py

Restart=always
RestartSec=5
TimeoutStopSec=10

StateDirectory=milo
StateDirectoryMode=0755

StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    # milo-frontend.service
    sudo tee /etc/systemd/system/milo-frontend.service > /dev/null << 'EOF'
[Unit]
Description=Milo Frontend Service
After=network.target

[Service]
Type=simple
User=milo
Group=milo
WorkingDirectory=/home/milo/milo/frontend

ExecStartPre=/usr/bin/npm run build
ExecStart=/usr/bin/npm run preview -- --host 0.0.0.0 --port 3000

Restart=always
RestartSec=5
TimeoutStopSec=10

StateDirectory=milo
StateDirectoryMode=0755

Environment=NODE_ENV=production
Environment=HOME=/home/milo

StandardOutput=journal
StandardError=journal
SyslogIdentifier=milo-frontend

[Install]
WantedBy=multi-user.target
EOF
    
    # milo-kiosk.service
    sudo tee /etc/systemd/system/milo-kiosk.service > /dev/null << 'EOF'
[Unit]
Description=Milo Kiosk Mode (Chromium Fullscreen)
After=graphical.target milo-frontend.service
Wants=graphical.target
Requires=milo-frontend.service

[Service]
Type=simple
User=milo
Group=milo
Environment=DISPLAY=:0
Environment=HOME=/home/milo
Environment=XDG_RUNTIME_DIR=/run/user/1000

ExecStartPre=/bin/sleep 8

ExecStart=/usr/bin/chromium-browser \
  --kiosk \
  --incognito \
  --no-first-run \
  --disable-infobars \
  --disable-notifications \
  --disable-popup-blocking \
  --disable-session-crashed-bubble \
  --disable-restore-session-state \
  --disable-background-timer-throttling \
  --disable-backgrounding-occluded-windows \
  --disable-renderer-backgrounding \
  --disable-translate \
  --disable-sync \
  --hide-scrollbars \
  --disable-background-networking \
  --autoplay-policy=no-user-gesture-required \
  --start-fullscreen \
  --no-sandbox \
  --disable-dev-shm-usage \
  --hide-cursor \
  --touch-events=enabled \
  --enable-features=TouchpadAndWheelScrollLatching \
  --force-device-scale-factor=1 \
  --disable-pinch \
  --disable-features=VizDisplayCompositor \
  --app=http://milo.local

Restart=always
RestartSec=5
TimeoutStopSec=5

[Install]
WantedBy=graphical.target
EOF
    
    # milo-roc.service
    sudo tee /etc/systemd/system/milo-roc.service > /dev/null << 'EOF'
[Unit]
Description=Milo ROC Audio Receiver
Documentation=https://roc-streaming.org/
After=network.target sound.service milo-backend.service
Wants=network.target
BindsTo=milo-backend.service

[Service]
Type=exec
User=milo
Group=audio

EnvironmentFile=/etc/environment
Environment=HOME=/home/milo

ExecStart=/usr/bin/roc-recv -vv \
  -s rtp+rs8m://0.0.0.0:10001 \
  -r rs8m://0.0.0.0:10002 \
  -c rtcp://0.0.0.0:10003 \
  -o alsa://milo_roc

Restart=always
RestartSec=5

PrivateNetwork=false
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6

StandardOutput=journal
StandardError=journal
SyslogIdentifier=milo-roc

[Install]
WantedBy=multi-user.target
EOF
    
    # milo-go-librespot.service
    sudo tee /etc/systemd/system/milo-go-librespot.service > /dev/null << 'EOF'
[Unit]
Description=Milo Spotify Connect via go-librespot
After=network-online.target sound.service milo-backend.service
Wants=network-online.target
BindsTo=milo-backend.service

[Service]
Type=simple
User=milo
Group=audio

ExecStart=/usr/local/bin/go-librespot --config_dir /var/lib/milo/go-librespot
Environment=HOME=/home/milo
WorkingDirectory=/var/lib/milo
Restart=always
RestartSec=5

StandardOutput=journal
StandardError=journal
SyslogIdentifier=milo-go-librespot

[Install]
WantedBy=multi-user.target
EOF
    
    # milo-bluealsa.service
    sudo tee /etc/systemd/system/milo-bluealsa.service > /dev/null << 'EOF'
[Unit]
Description=BluezALSA daemon for Milo
Documentation=man:bluealsa(8)
After=dbus.service bluetooth.service milo-backend.service
Requires=dbus.service
Wants=bluetooth.service
BindsTo=milo-backend.service

[Service]
Type=simple
ExecStart=/usr/bin/bluealsa -S -p a2dp-sink
User=milo
Group=audio
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
    
    # milo-bluealsa-aplay.service
    sudo tee /etc/systemd/system/milo-bluealsa-aplay.service > /dev/null << 'EOF'
[Unit]
Description=BlueALSA player for Milo
Requires=milo-bluealsa.service
After=milo-bluealsa.service milo-backend.service
BindsTo=milo-backend.service milo-bluealsa.service

[Service]
Type=simple
User=milo

ExecStart=/usr/bin/bluealsa-aplay --pcm=milo_bluetooth --profile-a2dp 00:00:00:00:00:00

RestartSec=2
Restart=always
PrivateTmp=false
PrivateDevices=false

[Install]
WantedBy=multi-user.target
EOF
    
    # milo-snapserver-multiroom.service
    sudo tee /etc/systemd/system/milo-snapserver-multiroom.service > /dev/null << 'EOF'
[Unit]
Description=Snapcast Server for Milo Multiroom
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/snapserver -c /etc/snapserver.conf
User=milo
Group=audio
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    
    # milo-snapclient-multiroom.service
    sudo tee /etc/systemd/system/milo-snapclient-multiroom.service > /dev/null << 'EOF'
[Unit]
Description=Snapcast Client for Milo Multiroom
After=network-online.target milo-snapserver-multiroom.service
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/snapclient -h 127.0.0.1 -p 1704 --logsink=system --soundcard default:CARD=sndrpihifiberry --mixer hardware:'Digital'
User=milo
Group=audio
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    
    log_success "Services systemd créés"
}

configure_alsa_loopback() {
    log_info "Configuration ALSA Loopback..."
    
    echo "snd_aloop" | sudo tee /etc/modules-load.d/snd-aloop.conf
    
    sudo tee /etc/modprobe.d/snd-aloop.conf > /dev/null << 'EOF'
options snd-aloop index=1 enable=1
EOF
    
    REBOOT_REQUIRED=true
    log_success "Module loopback ALSA configuré"
}

install_alsa_equal() {
    log_info "Installation d'ALSA Equal..."
    sudo apt-get install -y libasound2-plugin-equal
    log_success "ALSA Equal installé"
}

configure_alsa_complete() {
    log_info "Configuration ALSA complète..."
    
    sudo tee /etc/asound.conf > /dev/null << 'EOF'
pcm.!default {
    type plug
    slave.pcm {
        type hw
        card sndrpihifiberry
        device 0
    }
}

ctl.!default {
    type hw
    card sndrpihifiberry
}

pcm.milo_spotify {
    @func concat
    strings [
        "pcm.milo_spotify_"
        { @func getenv vars [ MILO_MODE ] default "direct" }
        { @func getenv vars [ MILO_EQUALIZER ] default "" }
    ]
}

pcm.milo_bluetooth {
    @func concat
    strings [
        "pcm.milo_bluetooth_"
        { @func getenv vars [ MILO_MODE ] default "direct" }
        { @func getenv vars [ MILO_EQUALIZER ] default "" }
    ]
}

pcm.milo_roc {
    @func concat
    strings [
        "pcm.milo_roc_"
        { @func getenv vars [ MILO_MODE ] default "direct" }
        { @func getenv vars [ MILO_EQUALIZER ] default "" }
    ]
}

pcm.milo_spotify_multiroom {
    type plug
    slave.pcm {
        type hw
        card 1
        device 0
        subdevice 2
    }
}

pcm.milo_bluetooth_multiroom {
    type plug
    slave.pcm {
        type hw
        card 1
        device 0
        subdevice 0
    }
}

pcm.milo_roc_multiroom {
    type plug
    slave.pcm {
        type hw
        card 1
        device 0
        subdevice 1
    }
}

pcm.milo_spotify_multiroom_eq {
    type plug
    slave.pcm "equal_multiroom"
}

pcm.milo_bluetooth_multiroom_eq {
    type plug
    slave.pcm "equal_multiroom"
}

pcm.milo_roc_multiroom_eq {
    type plug
    slave.pcm "equal_multiroom"
}

pcm.milo_spotify_direct {
    type plug
    slave.pcm {
        type hw
        card sndrpihifiberry
        device 0
    }
}

pcm.milo_bluetooth_direct {
    type plug
    slave.pcm {
        type hw
        card sndrpihifiberry
        device 0
    }
}

pcm.milo_roc_direct {
    type plug
    slave.pcm {
        type hw
        card sndrpihifiberry
        device 0
    }
}

pcm.milo_spotify_direct_eq {
    type plug
    slave.pcm "equal"
}

pcm.milo_bluetooth_direct_eq {
    type plug
    slave.pcm "equal"
}

pcm.milo_roc_direct_eq {
    type plug
    slave.pcm "equal"
}

pcm.equal {
    type equal
    slave.pcm "plughw:sndrpihifiberry"
}

pcm.equal_multiroom {
    type equal
    slave.pcm "plughw:1,0"
}

ctl.equal {
    type equal
}
EOF
    
    log_success "Configuration ALSA complète terminée"
}

configure_snapserver() {
    log_info "Configuration du serveur snapcast..."
    
    sudo tee /etc/snapserver.conf > /dev/null << 'EOF'
[stream]
default = Multiroom

buffer = 1000
codec = pcm
chunk_ms = 20
sampleformat = 48000:16:2

source = meta:///Bluetooth/ROC/Spotify?name=Multiroom

source = alsa:///?name=Bluetooth&device=hw:1,1,0
source = alsa:///?name=ROC&device=hw:1,1,1
source = alsa:///?name=Spotify&device=hw:1,1,2

[http]
enabled = true
bind_to_address = 0.0.0.0
port = 1780
doc_root = /usr/share/snapserver/snapweb/

[server]
threads = -1

[logging]
enabled = true
EOF
    
    log_success "Snapserver configuré"
}

configure_fan_control() {
    log_info "Configuration du contrôle du ventilateur..."
    
    local config_file="/boot/firmware/config.txt"
    
    if [[ ! -f "$config_file" ]]; then
        config_file="/boot/config.txt"
    fi
    
    if ! grep -q "cooling_fan=on" "$config_file"; then
        echo "" | sudo tee -a "$config_file"
        echo "# Milo - Fan PWM Control" | sudo tee -a "$config_file"
        echo "dtparam=cooling_fan=on" | sudo tee -a "$config_file"
        echo "dtparam=fan_temp0=55000" | sudo tee -a "$config_file"
        echo "dtparam=fan_temp0_hyst=2500" | sudo tee -a "$config_file"
        echo "dtparam=fan_temp0_speed=50" | sudo tee -a "$config_file"
        echo "dtparam=fan_temp1=60000" | sudo tee -a "$config_file"
        echo "dtparam=fan_temp1_hyst=2500" | sudo tee -a "$config_file"
        echo "dtparam=fan_temp1_speed=100" | sudo tee -a "$config_file"
        echo "dtparam=fan_temp2=65000" | sudo tee -a "$config_file"
        echo "dtparam=fan_temp2_hyst=2500" | sudo tee -a "$config_file"
        echo "dtparam=fan_temp2_speed=150" | sudo tee -a "$config_file"
        echo "dtparam=fan_temp3=70000" | sudo tee -a "$config_file"
        echo "dtparam=fan_temp3_hyst=2500" | sudo tee -a "$config_file"
        echo "dtparam=fan_temp3_speed=200" | sudo tee -a "$config_file"
        echo "dtparam=fan_temp4=75000" | sudo tee -a "$config_file"
        echo "dtparam=fan_temp4_hyst=2500" | sudo tee -a "$config_file"
        echo "dtparam=fan_temp4_speed=255" | sudo tee -a "$config_file"
    fi
   
   log_success "Contrôle du ventilateur configuré"
}

install_avahi_nginx() {
   log_info "Installation d'Avahi et Nginx..."
   sudo apt install -y avahi-daemon avahi-utils nginx chromium-browser
   log_success "Avahi, Nginx et Chromium installés"
}

configure_avahi() {
   log_info "Configuration d'Avahi..."
   
   sudo tee /etc/avahi/avahi-daemon.conf > /dev/null << 'EOF'
[server]
host-name=milo
domain-name=local
use-ipv4=yes
use-ipv6=no
allow-interfaces=wlan0
deny-interfaces=eth0,docker0,lo
ratelimit-interval-usec=1000000
ratelimit-burst=1000

[wide-area]
enable-wide-area=no

[publish]
publish-hinfo=no
publish-workstation=yes
publish-domain=yes
publish-addresses=yes
publish-aaaa-on-ipv4=no
publish-a-on-ipv6=no
EOF
   
   log_success "Avahi configuré"
}

configure_nginx() {
   log_info "Configuration de Nginx..."
   
   sudo tee /etc/nginx/sites-available/milo > /dev/null << 'EOF'
server {
   listen 80;
   server_name milo.local;
   
   location / {
       proxy_pass http://127.0.0.1:3000;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto $scheme;
   }
   
   location /api/ {
       proxy_pass http://127.0.0.1:8000;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto $scheme;
   }
   
   location /ws {
       proxy_pass http://127.0.0.1:8000;
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto $scheme;
       proxy_read_timeout 86400;
       proxy_send_timeout 86400;
       proxy_buffering off;
   }
}
EOF
   
   sudo ln -s /etc/nginx/sites-available/milo /etc/nginx/sites-enabled/
   sudo rm -f /etc/nginx/sites-enabled/default
   sudo nginx -t
   
   log_success "Nginx configuré"
}

install_brightness_hdmi() {
    log_info "Installation de Brightness-HDMI..."
    
    cd ~/
    git clone https://github.com/waveshare/RPi-USB-Brightness
    cd RPi-USB-Brightness
    cd 64
    cd lite
    ./Raspi_USB_Backlight_nogui -b 6
    
    cd ~
    
    log_success "Brightness-HDMI installé"
}

enable_services() {
   log_info "Démarrage automatique des services..."
   
   sudo systemctl daemon-reload
   sudo systemctl enable milo-backend.service
   sudo systemctl enable milo-frontend.service
   sudo systemctl enable milo-kiosk.service
   sudo systemctl enable milo-snapclient-multiroom.service
   sudo systemctl enable milo-snapserver-multiroom.service
   sudo systemctl enable milo-bluealsa-aplay.service
   sudo systemctl enable milo-bluealsa.service
   sudo systemctl enable avahi-daemon
   sudo systemctl enable nginx
   
   log_success "Démarrage automatique configuré"
}

start_services() {
   log_info "Démarrage des services..."
   
   sudo systemctl start milo-backend.service
   sudo systemctl start milo-frontend.service
   sudo systemctl start milo-kiosk.service
   sudo systemctl start milo-snapclient-multiroom.service
   sudo systemctl start milo-snapserver-multiroom.service
   sudo systemctl start milo-bluealsa-aplay.service
   sudo systemctl start milo-bluealsa.service
   sudo systemctl start avahi-daemon
   sudo systemctl start nginx
   
   log_success "Services démarrés"
}

finalize_installation() {
   log_info "Finalisation de l'installation..."
   
   echo ""
   echo -e "${GREEN}=================================${NC}"
   echo -e "${GREEN}   Installation Milo terminée !${NC}"
   echo -e "${GREEN}=================================${NC}"
   echo ""
   echo -e "${BLUE}Configuration :${NC}"
   echo "  • Hostname: milo"
   echo "  • Utilisateur: $MILO_USER"
   echo "  • Application: $MILO_APP_DIR"
   echo "  • Données: $MILO_DATA_DIR"
   if [[ -n "$HIFIBERRY_OVERLAY" ]]; then
       echo "  • Carte audio: $HIFIBERRY_OVERLAY"
   fi
   echo ""
   echo -e "${BLUE}Accès :${NC}"
   echo "  • Interface web: http://milo.local"
   echo "  • Spotify Connect: 'Milo'"
   echo "  • Bluetooth: 'Milo · Bluetooth'"
   echo "  • Snapserver: http://milo.local:1780"
   echo ""
   
   if [[ "$REBOOT_REQUIRED" == "true" ]]; then
       echo -e "${YELLOW}⚠️  REDÉMARRAGE REQUIS${NC}"
       echo ""
       
       case $USER_RESTART_CHOICE in
           "yes")
               log_info "Redémarrage automatique dans 5 secondes..."
               sleep 5
               sudo reboot
               ;;
           "no")
               echo -e "${YELLOW}Pensez à redémarrer manuellement avec: sudo reboot${NC}"
               ;;
       esac
   else
       start_services
       
       echo ""
       echo -e "${GREEN}✅ Milo est prêt ! Accédez à http://milo.local${NC}"
   fi
}

uninstall_milo() {
   log_warning "Début de la désinstallation de Milo..."
   echo ""
   read -p "Êtes-vous sûr de vouloir désinstaller Milo ? (o/N): " confirm
   case $confirm in
       [Oo]* )
           ;;
       * )
           log_info "Désinstallation annulée"
           exit 0
           ;;
   esac
   
   log_info "Arrêt des services..."
   sudo systemctl stop milo-*.service || true
   sudo systemctl disable milo-*.service || true
   
   log_info "Suppression des services systemd..."
   sudo rm -f /etc/systemd/system/milo-*.service
   sudo systemctl daemon-reload
   
   log_info "Suppression des configurations..."
   sudo rm -f /etc/nginx/sites-enabled/milo
   sudo rm -f /etc/nginx/sites-available/milo
   sudo rm -f /etc/snapserver.conf
   sudo rm -f /etc/asound.conf
   sudo rm -f /etc/modules-load.d/snd-aloop.conf
   sudo rm -f /etc/modprobe.d/snd-aloop.conf
   
   log_info "Suppression de l'application..."
   sudo rm -rf "$MILO_APP_DIR"
   sudo rm -rf "$MILO_DATA_DIR"
   
   log_info "Suppression des binaires..."
   sudo rm -f /usr/local/bin/go-librespot
   
   log_info "Nettoyage des packages..."
   sudo apt autoremove -y
   
   read -p "Restaurer l'hostname par défaut 'raspberrypi' ? (o/N): " restore_hostname
   case $restore_hostname in
       [Oo]* )
           configure_hostname "raspberrypi"
           log_info "Hostname restauré"
           ;;
   esac
   
   log_info "Redémarrage des services système..."
   sudo systemctl restart nginx avahi-daemon || true
   
   log_success "Désinstallation terminée !"
   echo ""
   log_warning "Note: L'utilisateur '$MILO_USER' n'a pas été supprimé"
   log_warning "Note: Les modifications de /boot/firmware/config.txt sont conservées"
   echo ""
   read -p "Redémarrer maintenant ? (o/N): " restart_now
   case $restart_now in
       [Oo]* )
           sudo reboot
           ;;
   esac
}

# ===============================
# FONCTION PRINCIPALE MODIFIÉE
# ===============================
main() {
   show_banner
   
   if [[ "$1" == "--uninstall" ]]; then
       uninstall_milo
       exit 0
   fi
   
   check_root
   
   log_info "Début de l'installation de Milo Audio System"
   echo ""
   
   check_system
   
   # COLLECTE DE TOUS LES CHOIX UTILISATEUR EN DÉBUT D'INSTALLATION
   collect_user_choices
   
   # INSTALLATION AUTOMATIQUE SANS INTERACTION
   install_dependencies
   setup_hostname
   configure_audio_hardware
   
   create_milo_user
   install_milo_application
   suppress_pulseaudio
   
   install_go_librespot
   install_roc_toolkit
   install_bluez_alsa
   install_snapcast
   
   create_systemd_services
   
   configure_alsa_loopback
   install_alsa_equal
   configure_alsa_complete
   configure_snapserver
   
   configure_fan_control
   
   install_avahi_nginx
   configure_avahi
   configure_nginx
   
   install_brightness_hdmi

   enable_services
   finalize_installation
}

main "$@"
