#!/bin/bash

echo "Starter kobling til OnePlus"
sudo uhubctl -l 1-2 -p 1 -a on > /dev/null

echo "Venter på at koblingen skal registreres"
sleep 4

ONEPLUS_IFACE=$(ip -o link show | awk -F': ' '{print $2}' | grep '^enx' | grep -v 'enx6c6e07220cee' | head -n 1)

if [ -z "$ONEPLUS_IFACE" ]; then
    echo "Feil: Klarte ikke å finne OnePlus-nettverket. Er kabelen plugget i?"
    exit 1
fi

echo "Fant telefonen på det nye grensesnittet: $ONEPLUS_IFACE"
echo "Setter opp nettverk..."


sudo ip link set $ONEPLUS_IFACE up
sudo dhclient $ONEPLUS_IFACE

echo "OnePlus er nå på nett og klar (IP: 172.16.42.1)"