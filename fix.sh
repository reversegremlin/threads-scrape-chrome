#!/bin/bash

# Define the input and output file
input_file="output/lakelanierofficial_threads_20250315_213919.md"
output_file="output/lakelanierofficial_threads_fixed.md"

# Function to check if a URL is accessible
check_url() {
    curl --output /dev/null --silent --head --fail "$1"
}

# Create or clear the output file
> "$output_file"

# Use sed to fix the image links and process each line
while IFS= read -r line; do
    # Check if the line contains an image link
    if [[ "$line" =~ \!\[Thread\ Image\]\((https?://[^)]+)\) ]]; then
        url="${BASH_REMATCH[1]}"
        # Check if the URL is accessible
        if check_url "$url"; then
            echo "$line" >> "$output_file"
        else
            echo "![Broken Image](https://via.placeholder.com/150)" >> "$output_file"  # Placeholder for broken images
        fi
    else
        echo "$line" >> "$output_file"
    fi
done < <(sed -E 's|!\[Thread Image\]\((https?://[^)]+)\)|![Thread Image](\1)|g' "$input_file")

echo "Image links have been processed and saved to $output_file"
