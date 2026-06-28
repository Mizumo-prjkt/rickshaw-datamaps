import os
import sys
import argparse
import urllib.request
import subprocess

# Pre-applied default country name
DEFAULT_COUNTRY_DOWNLOAD_MAP = "philippines"

# Available GeoFabrik regions to search
REGIONS = [
    "asia",
    "europe",
    "north-america",
    "south-america",
    "africa",
    "australia-oceania",
    "central-america",
    "antarctica"
]

def find_country_url(country, region=None):
    """Probes GeoFabrik servers to find the matching PBF download URL."""
    country = country.strip().lower().replace(" ", "-")
    
    if region:
        region = region.strip().lower().replace(" ", "-")
        url = f"https://download.geofabrik.de/{region}/{country}-latest.osm.pbf"
        return url
        
    print("Searching for country download URL across regions...")
    for r in REGIONS:
        url = f"https://download.geofabrik.de/{r}/{country}-latest.osm.pbf"
        try:
            req = urllib.request.Request(url, method='HEAD')
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    print(f"Found match: {url}")
                    return url
        except Exception:
            continue
            
    # Try root level (some country datasets may be at root)
    url = f"https://download.geofabrik.de/{country}-latest.osm.pbf"
    try:
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                print(f"Found match at root: {url}")
                return url
    except Exception:
        pass
        
    return None

def download_file(url, output_path):
    """Downloads a file showing a premium console progress bar."""
    print(f"\nStarting download from {url}")
    try:
        response = urllib.request.urlopen(url)
        meta = response.info()
        file_size = int(meta.get("Content-Length", 0))
        
        if file_size > 0:
            print(f"File size: {file_size / (1024 * 1024):.2f} MB")
        else:
            print("File size: Unknown")
            
        block_size = 1024 * 1024 # 1 MB
        downloaded = 0
        
        with open(output_path, 'wb') as f:
            while True:
                buffer = response.read(block_size)
                if not buffer:
                    break
                downloaded += len(buffer)
                f.write(buffer)
                
                if file_size > 0:
                    percent = downloaded * 100 / file_size
                    bar_len = 30
                    filled_len = int(bar_len * percent / 100)
                    bar = '█' * filled_len + '-' * (bar_len - filled_len)
                    sys.stdout.write(f"\rProgress: |{bar}| {percent:.1f}% ({downloaded / (1024 * 1024):.2f} MB / {file_size / (1024 * 1024):.2f} MB)")
                else:
                    sys.stdout.write(f"\rDownloaded: {downloaded / (1024 * 1024):.2f} MB")
                sys.stdout.flush()
                
        print("\nDownload complete.")
        return True
    except Exception as e:
        print(f"\nError downloading file: {e}")
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Download map data from GeoFabrik and optionally process/split it."
    )
    parser.add_argument(
        "-c", "--country",
        help="Country name to download (e.g., philippines). If omitted, falls back to the default or prompts interactively."
    )
    parser.add_argument(
        "-r", "--region",
        help="Continent/region of the country (e.g., asia, europe). Auto-probed if omitted."
    )
    parser.add_argument(
        "-p", "--process",
        action="store_true",
        default=None,
        help="Run processor.py on the downloaded file to compress, split, and generate MD5s."
    )
    parser.add_argument(
        "-n", "--no-process",
        dest="process",
        action="store_false",
        help="Skip running processor.py on the downloaded file."
    )
    parser.add_argument(
        "-o", "--output",
        help="Custom output file path. Defaults to [country]-latest.osm.pbf in the current directory."
    )
    
    args = parser.parse_args()
    
    country = args.country
    region = args.region
    should_process = args.process
    
    # 1. Determine country
    if not country:
        try:
            country = DEFAULT_COUNTRY_DOWNLOAD_MAP
            print(f"Using default country: {country}")
        except NameError:
            pass
            
        if not country:
            try:
                country = input("Enter country name to download (e.g., philippines): ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nCancelled.")
                sys.exit(1)
                
        if not country:
            print("Error: No country specified.")
            sys.exit(1)
            
    # 2. Locate URL
    url = find_country_url(country, region)
    if not url:
        print(f"Error: Could not locate a GeoFabrik download URL for '{country}' in region '{region or 'any'}'.")
        print("Please check the country spelling (e.g., 'philippines', 'germany').")
        sys.exit(1)
        
    # 3. Determine output path
    output_path = args.output
    if not output_path:
        sanitized_country = country.strip().lower().replace(" ", "-")
        output_path = f"{sanitized_country}-latest.osm.pbf"
        
    # Ensure directory exists if path contains directories
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        
    # 4. Download file
    success = download_file(url, output_path)
    if not success:
        print("Download failed.")
        sys.exit(1)
        
    # 5. Determine whether to run processor.py
    if should_process is None:
        try:
            choice = input("\nDo you want to process, compress and split the downloaded map file? [Y/n]: ").strip().lower()
            should_process = choice in ('', 'y', 'yes')
        except (KeyboardInterrupt, EOFError):
            should_process = False
            
    if should_process:
        print(f"\nRunning processor.py on {output_path}...")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        processor_path = os.path.join(script_dir, "processor.py")
        
        if not os.path.exists(processor_path):
            print(f"Error: {processor_path} not found. Cannot run processor.")
            sys.exit(1)
            
        try:
            result = subprocess.run(
                [sys.executable, processor_path, output_path],
                check=True
            )
            print("\nMap file processing and split completed successfully!")
        except subprocess.CalledProcessError as e:
            print(f"\nError running processor.py: {e}")
            sys.exit(1)
    else:
        print(f"\nFile saved to {output_path}. Done!")

if __name__ == "__main__":
    main()
