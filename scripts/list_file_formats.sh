#!/bin/bash

echo "File formats used in this project:"
echo "=================================="

find . -type f -name "*.*" | \
    sed 's/.*\.//' | \
    grep -v "^$" | \
    sort | \
    uniq -c | \
    sort -nr | \
    awk '{printf "%-10s (%d files)\n", $2, $1}'

echo ""
echo "Files without extensions:"
echo "========================"

find . -type f ! -name "*.*" | \
    grep -v "/\." | \
    wc -l | \
    awk '{print $1 " files"}'

echo ""
echo "Total files:"
echo "============"

find . -type f | wc -l | awk '{print $1 " files"}' 