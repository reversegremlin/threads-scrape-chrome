# Threads Scraper

A Python script that scrapes posts and replies from a Threads.net account and saves them to PDF, JSON, or TXT format, including images from posts.

## Features

- Scrapes posts and replies from any public Threads account
- Downloads and includes post images in the PDF output
- Formats content with timestamps, text, and engagement stats
- Multiple output formats (PDF, JSON, TXT)
- Robust error handling with automatic fallback options
- Chromium/Chrome support with automatic browser detection
- Customizable scroll depth for controlling how many posts to fetch

## Requirements

- Python 3.7+
- Chrome or Chromium browser
- ChromeDriver (installed automatically)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/threads-scraper.git
cd threads-scraper
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Scrape a Threads account:
```bash
python threads_scraper_fixed.py --username USERNAME
```

### Command-line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--username` | Threads username to scrape (without @ symbol) | Required |
| `--output-dir` | Directory to save output files | `output` |
| `--max-scrolls` | Maximum number of scrolls to perform | `10` |
| `--skip-replies` | Skip scraping replies | `False` |
| `--skip-posts` | Skip scraping posts | `False` |
| `--output-format` | Output format: `pdf`, `json`, or `txt` | `pdf` |

### Examples

Scrape with more posts:
```bash
python threads_scraper_fixed.py --username USERNAME --max-scrolls 20
```

Only scrape replies:
```bash
python threads_scraper_fixed.py --username USERNAME --skip-posts
```

Save as JSON:
```bash
python threads_scraper_fixed.py --username USERNAME --output-format json
```

Save as plain text:
```bash
python threads_scraper_fixed.py --username USERNAME --output-format txt
```

## Browser Setup

### Chrome Installation

#### Ubuntu/Debian:
```bash
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
sudo apt update
sudo apt install -y google-chrome-stable
```

#### Newer Debian versions:
```bash
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install -y google-chrome-stable
```

### Chromium Installation

#### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install -y chromium-browser
```

#### Fedora:
```bash
sudo dnf install -y chromium
```

### Browser Path Configuration

If the script can't find your browser automatically, set the `CHROME_DRIVER_PATH` environment variable:

```bash
export CHROME_DRIVER_PATH=/usr/bin/chromium
```

Or run in one line:
```bash
CHROME_DRIVER_PATH=/usr/bin/chromium python threads_scraper_fixed.py --username USERNAME
```

## Troubleshooting

### Browser Detection Issues

If you see "Could not initialize WebDriver" errors:

1. Verify Chrome/Chromium installation:
```bash
which google-chrome
# or
which chromium-browser
```

2. Set the browser path:
```bash
export CHROME_DRIVER_PATH=/path/to/browser
```

### PDF Generation Issues

If the PDF output is unreadable:

1. Try a different output format:
```bash
python threads_scraper_fixed.py --username USERNAME --output-format txt
```

2. Reduce the number of posts:
```bash
python threads_scraper_fixed.py --username USERNAME --max-scrolls 5
```

3. Check the debug files:
- `debug_False_page.png`: Screenshot of posts page
- `debug_True_page.png`: Screenshot of replies page
- `debug_False_page.html`: HTML source of posts page
- `debug_True_page.html`: HTML source of replies page

## Limitations

- Only works with public Threads accounts
- May be affected by Threads website changes
- Subject to rate limiting and anti-scraping measures
- PDF generation may fail with very large amounts of content

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for educational purposes only. Be sure to comply with Threads' terms of service and respect rate limits when using this script.