#!/bin/bash
# Installation script for Unbound Manager
set -e

echo 'Installing Unbound Manager...'
cd /root/unbound-manager
pip3 install -e .
echo 'Installation complete! Run unbound-manager to start.'