#!/usr/bin/env bash
# Beispieldaten laden (idempotent – ein zweiter Lauf erzeugt keine Duplikate).
source "$(dirname "$0")/_common.sh"
$DC run --rm --no-deps app python -m app.cli seed
