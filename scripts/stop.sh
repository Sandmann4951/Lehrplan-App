#!/usr/bin/env bash
# Anwendung stoppen (Daten bleiben im Volume erhalten).
source "$(dirname "$0")/_common.sh"
$DC stop app
echo "Anwendung gestoppt."
