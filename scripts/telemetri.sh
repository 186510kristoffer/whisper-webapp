#!/bin/sh

# Hent batteriprosent og batteritemperatur
b=$(cat /sys/class/power_supply/bq27541-0/capacity)
bat_t=$(for z in /sys/class/thermal/thermal_zone*; do [ "$(cat $z/type 2>/dev/null)" = "bq27541-0" ] && awk '{print $1/1000}' $z/temp; done | head -n1)

# CPU-snitt
cpu_t=$(for z in /sys/class/thermal/thermal_zone*; do cat $z/type 2>/dev/null | grep -q '^cpu' && awk '{print $1/1000}' $z/temp; done | awk '{s+=$1; c++} END {if(c>0) printf "%.1f", s/c; else print "N/A"}')

# PMIC (Ladekrets/Strømstyring) snitt i stedet for GPU
pmic_t=$(for z in /sys/class/thermal/thermal_zone*; do cat $z/type 2>/dev/null | grep -q '^pm8150' && awk '{print $1/1000}' $z/temp; done | awk '{s+=$1; c++} END {if(c>0) printf "%.1f", s/c; else print "N/A"}')

echo "$b,$bat_t,$cpu_t,$pmic_t"