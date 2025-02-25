#!/bin/bash

# Define the directory and prefix
dir="/etc/init.d"
prefix="jianghujs_"

# Loop over the files in the directory
for file in "$dir"/$prefix*; do
    # Check if the file contains a line starting with "npm start" or "npm run start" but not containing "&& break"
    if egrep -q '^npm (run )?start' "$file" && ! grep -q '&& break' "$file"; then
        # If it does, replace it with the retry logic
        sed -i '/^npm \(run \)\?start/ {s/^\(npm \(run \)\?start.*\)/attempt=0\nuntil [ $attempt -ge 3 ]\ndo\n  \1 \&\& break\n  attempt=$[$attempt+1]\n  sleep 5\ndone/}' "$file"
        echo "fixed $file"
    fi
done
