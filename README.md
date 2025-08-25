# YouTube URL Scraper

A Python script that reads URLs from a text file, fetches each URL, scrapes for YouTube video IDs marked with asterisks (youtube/*), and outputs YouTube watch URLs.

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

1. Create a text file with URLs (one per line) named `urls.txt`
2. Run the script:
```bash
python url_scraper.py
```
3. The script will create `youtube_urls.txt` with the YouTube watch URLs

### Custom Files

You can specify custom input and output files:
```bash
python url_scraper.py input_urls.txt output_youtube.txt
```

### Command Line Options

- `input_file`: Input file containing URLs (default: urls.txt)
- `output_file`: Output file for YouTube watch URLs (default: youtube_urls.txt)
- `--delay`: Delay between requests in seconds (default: 0.5)

### Example

```bash
# Use default files
python url_scraper.py

# Use custom files
python url_scraper.py my_urls.txt youtube_results.txt

# With custom delay
python url_scraper.py --delay 1.0
```

## How It Works

The script:
1. Reads URLs from the input file (one URL per line)
2. Fetches each URL's content
3. Searches for patterns like:
   - `youtube/*VIDEO_ID`
   - `youtube/VIDEO_ID` 
   - Various formats with asterisks marking YouTube video IDs
4. Extracts 11-character YouTube video IDs
5. Writes `https://www.youtube.com/watch?v=VIDEO_ID` to the output file

## Pattern Matching

The script looks for YouTube video IDs in various formats:
- Direct patterns: `youtube/VIDEO_ID`
- With asterisk: `youtube/*VIDEO_ID`
- In quotes: `"youtube/*VIDEO_ID"`
- With spaces: `youtube/* VIDEO_ID`

## Error Handling

- The script handles network errors gracefully
- Failed URLs are logged to stderr
- Processing continues even if some URLs fail

## Rate Limiting

The script includes a configurable delay between requests (default 0.5 seconds) to be respectful to servers.