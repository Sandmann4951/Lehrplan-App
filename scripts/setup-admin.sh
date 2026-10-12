#!/usr/bin/env bash
# Erstadministrator anlegen (Passwort wird interaktiv abgefragt, keine Standardzugangsdaten).
# Aufruf: scripts/setup-admin.sh admin@schule.de "Vorname Nachname"
source "$(dirname "$0")/_common.sh"
EMAIL="${1:?E-Mail-Adresse angeben}"
NAME="${2:-}"
$DC run --rm --no-deps app python -m app.cli create-admin --email "$EMAIL" ${NAME:+--name "$NAME"}
