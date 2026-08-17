#!/bin/sh

# Hent batteriprosent
b=$(cat /sys/class/power_supply/bq27541-0/capacity)

# Hent batteritemperatur (spesifikk zone for bq27541-0)
bat_t=$(for z in /sys/class/thermal/thermal_zone*; do [ "$(cat $z/type 2>/dev/null)" = "bq27541-0" ] && awk '{print $1/1000}' $z/temp; done | head -n1)

# Regn ut snitt av alle CPU-relaterte termiske soner
cpu_t=$(for z in /sys/class/thermal/thermal_zone*; do cat $z/type 2>/dev/null | grep -q '^cpu' && awk '{print $1/1000}' $z/temp; done | awk '{s+=$1; c++} END {if(c>0) printf "%.1f", s/c; else print "N/A"}')

# Regn ut snitt av alle GPU-relaterte termiske soner
gpu_t=$(for z in /sys/class/thermal/thermal_zone*; do cat $z/type 2>/dev/null | grep -q '^gpu' && awk '{print $1/1000}' $z/temp; done | awk '{s+=$1; c++} END {if(c>0) printf "%.1f", s/c; else print "N/A"}')

# Returner som en ryddig kommaseparert streng til Python
echo "$b,$bat_t,$cpu_t,$gpu_t"