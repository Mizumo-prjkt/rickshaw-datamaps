#!/usr/bin/env python3
import os
import sys
import json
import zipfile
import glob

# Import md5 function from genmd5
try:
    import genmd5
except ImportError:
    print("Error: Could not import genmd5.py. Make sure it's in the same directory.")
    sys.exit(1)

def verify_hash(file_path, expected_hash, description="File"):
    """Verifies a file against an expected MD5 hash."""
    if not os.path.exists(file_path):
        print(f"[{description}] Error: File not found: {file_path}")
        return False
        
    print(f"[{description}] Verifying MD5 for {os.path.basename(file_path)}...")
    actual_hash = genmd5.compute_md5(file_path)
    
    if actual_hash == expected_hash:
        print(f"[{description}] MD5 Check OK: {actual_hash}")
        return True
    else:
        print(f"[{description}] MD5 Check FAILED!")
        print(f"  Expected: {expected_hash}")
        print(f"  Actual:   {actual_hash}")
        return False

def read_md5_txt(txt_path):
    """Reads a simple md5 text file format: [hash]  [filename]"""
    if not os.path.exists(txt_path):
        return None
        
    try:
        with open(txt_path, 'r') as f:
            content = f.read().strip()
            if content:
                # Expecting format: hash  filename
                parts = content.split('  ')
                if len(parts) >= 1:
                    return parts[0].strip()
    except Exception as e:
        print(f"Error reading {txt_path}: {e}")
    return None

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.join(script_dir, 'datamaps')
    
    if not os.path.exists(base_dir):
        print(f"Error: Directory '{base_dir}' does not exist.")
        sys.exit(1)

    # Get available date directories
    date_dirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    date_dirs.sort(reverse=True)
    
    if not date_dirs:
        print(f"No date directories found in {base_dir}")
        sys.exit(1)

    # Interactive selection
    print("Available map data dates for unification:")
    for i, date_dir in enumerate(date_dirs):
        print(f"{i + 1}. {date_dir}")
    
    try:
        choice = input(f"\nSelect a directory [1-{len(date_dirs)}]: ")
        index = int(choice) - 1
        if 0 <= index < len(date_dirs):
            selected_date = date_dirs[index]
        else:
            print("Invalid selection.")
            sys.exit(1)
    except (ValueError, KeyboardInterrupt, EOFError):
        print("\nOperation cancelled or invalid input.")
        sys.exit(1)

    target_dir = os.path.join(base_dir, selected_date)
    chunks_dir = os.path.join(target_dir, 'chunks')
    
    export_dir = os.path.join(script_dir, 'export')
    os.makedirs(export_dir, exist_ok=True)
    
    if not os.path.exists(chunks_dir):
        print(f"Error: Chunks directory '{chunks_dir}' does not exist.")
        sys.exit(1)

    # 1. Load Split MD5s and verify chunks
    md5_split_path = os.path.join(target_dir, 'md5-split.json')
    if not os.path.exists(md5_split_path):
        print(f"Error: Missing '{md5_split_path}'. Cannot verify chunk integrity.")
        sys.exit(1)
        
    try:
        with open(md5_split_path, 'r') as f:
            chunk_hashes = json.load(f)
    except Exception as e:
        print(f"Error loading JSON hashes: {e}")
        sys.exit(1)
        
    print("\nVerifying chunks...")
    # Sort the relative paths to ensure correct concatenation order
    sorted_chunk_paths = sorted(chunk_hashes.keys())
    
    for rel_path in sorted_chunk_paths:
        expected_hash = chunk_hashes[rel_path]
        # rel_path is like 'chunks/filename.zip.partaa', so we join with target_dir
        # Actually in genmd5.py relative_path was relative to target_dir (selected_date dir)
        # So it's literally target_dir + "/" + rel_path
        abs_chunk_path = os.path.join(target_dir, rel_path)
        
        if not verify_hash(abs_chunk_path, expected_hash, description="Chunk"):
            print("Aborting unification due to anomaly in chunks.")
            sys.exit(1)
            
    if not sorted_chunk_paths:
        print("No chunks found in md5-split.json.")
        sys.exit(1)

    # 2. Unify chunks
    # Deduce output filename from the first chunk name
    # e.g., 'chunks/philippines.osm.pbf.zip.partaa' -> 'philippines.osm.pbf.zip'
    first_chunk_rel = sorted_chunk_paths[0]
    first_chunk_base = os.path.basename(first_chunk_rel) # 'philippines.osm.pbf.zip.partaa'
    
    # Strip the .partXX extension
    if '.part' in first_chunk_base:
        unified_filename = first_chunk_base[:first_chunk_base.rfind('.part')]
    else:
        unified_filename = "unified_archive.zip"
        
    unified_filepath = os.path.join(export_dir, unified_filename)
    
    print(f"\nUnifying chunks into {unified_filepath}...")
    try:
        with open(unified_filepath, 'wb') as outfile:
            for rel_path in sorted_chunk_paths:
                abs_chunk_path = os.path.join(target_dir, rel_path)
                with open(abs_chunk_path, 'rb') as infile:
                    # Write in chunks to save memory
                    while True:
                        data = infile.read(4096 * 1024)
                        if not data:
                            break
                        outfile.write(data)
        print("Unification complete.")
    except Exception as e:
        print(f"Error during unification: {e}")
        sys.exit(1)

    # 3. Verify unified compressed file
    md5_compressed_path = os.path.join(target_dir, 'md5-compressed.txt')
    expected_compressed_hash = read_md5_txt(md5_compressed_path)
    
    if expected_compressed_hash:
        print("\nVerifying unified compressed archive...")
        if not verify_hash(unified_filepath, expected_compressed_hash, "Compressed Archive"):
            print("Warning: Unified archive MD5 mismatch. The file might be corrupted.")
    else:
        print("\nNotice: md5-compressed.txt not found. Skipping unified archive verification.")

    # 4. Decompression Prompt
    print("\nDo you want to decompress the unified archive?")
    try:
        choice = input("Decompress? [Y/n]: ").strip().lower()
        if choice not in ('', 'y', 'yes'):
            print("Skipping decompression. Done!")
            sys.exit(0)
    except (KeyboardInterrupt, EOFError):
        print("\nSkipping decompression. Done!")
        sys.exit(0)

    # 5. Decompress
    print(f"\nDecompressing {unified_filepath} into {export_dir}...")
    extracted_filename = None
    try:
        with zipfile.ZipFile(unified_filepath, 'r') as zf:
            # We expect a single map file inside the archive typically
            file_list = zf.namelist()
            if file_list:
                extracted_filename = file_list[0]
            zf.extractall(export_dir)
        print("Decompression complete.")
    except Exception as e:
        print(f"Error during decompression: {e}")
        sys.exit(1)

    # 6. Verify original file
    if extracted_filename:
        extracted_filepath = os.path.join(export_dir, extracted_filename)
        md5_original_path = os.path.join(target_dir, 'md5-original.txt')
        expected_original_hash = read_md5_txt(md5_original_path)
        
        if expected_original_hash:
            print(f"\nVerifying extracted original file ({extracted_filename})...")
            if not verify_hash(extracted_filepath, expected_original_hash, "Extracted File"):
                print("Warning: Extracted file MD5 mismatch. The file might be corrupted.")
        else:
            print("\nNotice: md5-original.txt not found. Skipping extracted file verification.")
    
    print("\nAll operations completed successfully!")

if __name__ == "__main__":
    main()
