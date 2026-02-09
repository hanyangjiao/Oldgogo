#!/bin/bash
# Installation script for Oldgogo UI systemd service

set -e

# Check if GEMINI_API_KEY is provided
if [ -z "$GEMINI_API_KEY" ]; then
    echo "ERROR: GEMINI_API_KEY environment variable not set"
    echo "Please run: export GEMINI_API_KEY='your_key_here'"
    echo "Then run this script again."
    exit 1
fi

echo "Creating systemd service file with your API key..."

# Create the service file
cat > /tmp/oldgogo-ui.service << EOF
[Unit]
Description=Oldgogo Elder Monitor UI Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment="GEMINI_API_KEY=$GEMINI_API_KEY"
Environment="PATH=/home/xxz/miniconda3/envs/dds/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/xxz/miniconda3/envs/dds/bin/python $(pwd)/src/app/ui_server.py --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "Installing service..."
sudo cp /tmp/oldgogo-ui.service /etc/systemd/system/
sudo systemctl daemon-reload

echo "Enabling service to start on boot..."
sudo systemctl enable oldgogo-ui

echo "Starting service..."
sudo systemctl start oldgogo-ui

echo ""
echo "✓ Service installed and started successfully!"
echo ""
echo "Service status:"
sudo systemctl status oldgogo-ui --no-pager

echo ""
echo "UI available at: http://localhost:8000/src/app/ui/"
echo "                 http://$(hostname -I | awk '{print $1}'):8000/src/app/ui/"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status oldgogo-ui   # Check status"
echo "  sudo systemctl stop oldgogo-ui     # Stop service"
echo "  sudo systemctl restart oldgogo-ui  # Restart service"
echo "  sudo journalctl -u oldgogo-ui -f   # View logs"
