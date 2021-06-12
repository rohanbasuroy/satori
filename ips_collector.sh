sudo perf stat -e instructions -p $1  -a sleep 0.01 &> $2
