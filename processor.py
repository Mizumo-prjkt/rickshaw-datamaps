import os
import sys
import datetime
import zipfile
import shutil
import json

# Import our md5 generator
import genmd5
import argparse

def split_file(input_file, output_dir, chunk_size=10 * 1024 * 1024): # 10 MiB
    """Splits a file into chunk_size pieces."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    base_name = os.path.basename(input_file)
    chunk_index = 0
    
    with open(input_file, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
                
            # Generate suffix like .partaa, .partab ...
            # To handle more than 26 chunks, we use two letters
            first_char = chr(ord('a') + (chunk_index // 26))
            second_char = chr(ord('a') + (chunk_index % 26))
            suffix = f".part{first_char}{second_char}"
            
            output_file = os.path.join(output_dir, f"{base_name}{suffix}")
            with open(output_file, 'wb') as chunk_f:
                chunk_f.write(chunk)
            
            chunk_index += 1
            
    print(f"Split {input_file} into {chunk_index} chunks in {output_dir}")

def compress_file(input_file, output_zip):
    """Compresses a file to a zip archive."""
    print(f"Compressing {input_file} to {output_zip}...")
    
    # Try ZSTD if installed via some external module, fallback to DEFLATED
    try:
        # zstandard is not in standard library, but we attempt it to fulfill "use ZSTD if available"
        # pyrefly: ignore [missing-import]
        import zstandard
        print("ZSTD module available. Note: standard Python zipfile does not support ZSTD natively.")
        print("Falling back to ZIP_LZMA (highest compression available natively in Python).")
        compression = zipfile.ZIP_LZMA
        compresslevel = None # LZMA doesn't use standard level parameter
    except ImportError:
        print("ZSTD not available. Falling back to default ZIP_DEFLATED level 9.")
        compression = zipfile.ZIP_DEFLATED
        compresslevel = 9
        
    try:
        # zipfile kwargs depend on the compression type
        kwargs = {"compression": compression}
        if compression == zipfile.ZIP_DEFLATED:
            kwargs["compresslevel"] = compresslevel
            
        with zipfile.ZipFile(output_zip, 'w', **kwargs) as zf:
            zf.write(input_file, arcname=os.path.basename(input_file))
        print("Compression completed.")
        return True
    except Exception as e:
        print(f"Compression failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Compress and split a map data file into 10MiB chunks, generating MD5 hashes."
    )
    parser.add_argument(
        "input_file",
        help="The map data file to process (e.g., philippines-latest.osm.pbf)"
    )
    args = parser.parse_args()
    input_file = args.input_file
    
    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found.")
        sys.exit(1)
        
    script_dir = os.path.dirname(os.path.abspath(__file__))
    datamaps_dir = os.path.join(script_dir, 'datamaps')
    
    # Format current date as DD-MM-YYYY
    current_date = datetime.datetime.now().strftime("%d-%m-%Y")
    date_dir = os.path.join(datamaps_dir, current_date)
    chunks_dir = os.path.join(date_dir, 'chunks')
    
    os.makedirs(date_dir, exist_ok=True)
    os.makedirs(chunks_dir, exist_ok=True)
    
    # Setup compressed file path
    base_filename = os.path.basename(input_file)
    compressed_file = os.path.join(date_dir, f"{base_filename}.zip")
    
    # 1. Compress
    success = compress_file(input_file, compressed_file)
    if not success:
        sys.exit(1)
        
    # 2. Split
    print("\nSplitting compressed file into 10MiB chunks...")
    split_file(compressed_file, chunks_dir)
    
    # 3. Generate MD5s
    print("\nGenerating MD5 hashes for the process...")
    # Check if original or compressed file vanished abruptly (user intervention)
    if not os.path.exists(input_file):
        print(f"Warning: Original file '{input_file}' is missing! Skipping its MD5 hash.")
        input_file = ""
        
    if not os.path.exists(compressed_file):
        print(f"Warning: Compressed file '{compressed_file}' is missing! Skipping its MD5 hash.")
        compressed_file = ""
        
    genmd5.generate_hashes(
        selected_date=current_date,
        compressed_file_path=compressed_file,
        original_file_path=input_file
    )
    
    # 4. Generate identifier.json
    region_name = base_filename
    if "-latest" in region_name:
        region_name = region_name.split("-latest")[0]
    for ext in [".osm.pbf", ".pbf", ".zip", ".osm"]:
        if region_name.endswith(ext):
            region_name = region_name[:-len(ext)]
            
    processed_at = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
    identifier_data = {
        "date": current_date,
        "region": region_name,
        "processed-at": processed_at
    }
    
    identifier_path = os.path.join(date_dir, "identifier.json")
    try:
        with open(identifier_path, "w") as f:
            json.dump(identifier_data, f, indent=4)
        print(f"Generated identifier file at '{identifier_path}'")
    except Exception as e:
        print(f"Warning: Failed to generate identifier file: {e}")
    
    print(f"\nProcessing complete for {current_date}!")

if __name__ == "__main__":
    main()
