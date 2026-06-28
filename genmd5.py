import os
import hashlib
import sys
import json

def compute_md5(file_path):
    """Computes the MD5 hash of a given file."""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096 * 1024), b""): # 4MB chunks
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

def generate_hashes(selected_date, compressed_file_path="", original_file_path=""):
    """
    Programmatic entry point to generate MD5 hashes for a specific date directory.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.join(script_dir, 'datamaps')
    
    if not os.path.exists(base_dir):
        print(f"Error: Directory '{base_dir}' does not exist.")
        return False

    target_dir = os.path.join(base_dir, selected_date, 'chunks')
    output_split_json = os.path.join(base_dir, selected_date, 'md5-split.json')
    output_compressed_txt = os.path.join(base_dir, selected_date, 'md5-compressed.txt')
    output_original_txt = os.path.join(base_dir, selected_date, 'md5-original.txt')

    # Process chunks
    if os.path.exists(target_dir):
        files_to_hash = []
        for root, _, files in os.walk(target_dir):
            for file in files:
                files_to_hash.append(os.path.join(root, file))

        if files_to_hash:
            print(f"\nFound {len(files_to_hash)} chunk files in {target_dir}. Computing MD5 hashes...")
            
            results_dict = {}
            for file_path in sorted(files_to_hash):
                relative_path = os.path.relpath(file_path, os.path.join(base_dir, selected_date))
                md5_hash = compute_md5(file_path)
                if md5_hash:
                    results_dict[relative_path] = md5_hash
                    print(f"{md5_hash}  {relative_path}")

            try:
                with open(output_split_json, 'w') as f:
                    json.dump(results_dict, f, indent=4)
                print(f"\nSuccessfully wrote split MD5 hashes to '{output_split_json}'")
            except Exception as e:
                print(f"Error writing to {output_split_json}: {e}")
        else:
            print(f"No files found in '{target_dir}'")
    else:
        print(f"Chunks directory '{target_dir}' does not exist. Skipping chunk processing.")

    # Process compressed file
    if compressed_file_path and os.path.exists(compressed_file_path):
        print(f"\nComputing MD5 for compressed file: {compressed_file_path}")
        md5_hash = compute_md5(compressed_file_path)
        if md5_hash:
            relative_path = os.path.basename(compressed_file_path)
            entry = f"{md5_hash}  {relative_path}"
            print(entry)
            try:
                with open(output_compressed_txt, 'w') as f:
                    f.write(entry + '\n')
                print(f"Successfully wrote compressed MD5 hash to '{output_compressed_txt}'")
            except Exception as e:
                print(f"Error writing to {output_compressed_txt}: {e}")
    elif compressed_file_path:
        print(f"File not found: {compressed_file_path}")

    # Process original file
    if original_file_path and os.path.exists(original_file_path):
        print(f"\nComputing MD5 for original file: {original_file_path}")
        md5_hash = compute_md5(original_file_path)
        if md5_hash:
            relative_path = os.path.basename(original_file_path)
            entry = f"{md5_hash}  {relative_path}"
            print(entry)
            try:
                with open(output_original_txt, 'w') as f:
                    f.write(entry + '\n')
                print(f"Successfully wrote original MD5 hash to '{output_original_txt}'")
            except Exception as e:
                print(f"Error writing to {output_original_txt}: {e}")
    elif original_file_path:
        print(f"File not found: {original_file_path}")
    
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Generate MD5 checksums for split chunks, compressed zip, and original map file."
    )
    parser.add_argument(
        "-d", "--date",
        help="Date directory name (e.g., 15-05-2026). If not provided, lists available directories interactively."
    )
    parser.add_argument(
        "-c", "--compressed",
        default="",
        help="Path to pre-split compressed file (optional)."
    )
    parser.add_argument(
        "-o", "--original",
        default="",
        help="Path to non-compressed original file (optional)."
    )
    args = parser.parse_args()

    # Resolve absolute path to mapdata/datamaps
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.join(script_dir, 'datamaps')
    
    if not os.path.exists(base_dir):
        print(f"Error: Directory '{base_dir}' does not exist.")
        sys.exit(1)

    # Get available date directories
    date_dirs = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    date_dirs.sort(reverse=True) # Show newest dates first
    
    if not date_dirs:
        print(f"No date directories found in {base_dir}")
        sys.exit(1)

    selected_date = args.date
    compressed_file_path = args.compressed
    original_file_path = args.original

    if not selected_date:
        # Interactive selection
        print("Available map data dates:")
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
        except ValueError:
            print("Invalid input.")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            sys.exit(0)
        except EOFError:
            # Fallback if run non-interactively without inputs
            print("Interactive prompt failed. Falling back to the first available directory.")
            selected_date = date_dirs[0]

        # Prompt for optional files in interactive mode only if not provided via CLI
        if not compressed_file_path or not original_file_path:
            print("\nOptional: Compute MD5 for pre-split compressed and original files.")
            try:
                if not compressed_file_path:
                    compressed_file_path = input("Enter path to pre-split compressed file (leave blank to skip): ").strip()
                if not original_file_path:
                    original_file_path = input("Enter path to non-compressed original file (leave blank to skip): ").strip()
            except (KeyboardInterrupt, EOFError):
                pass
    else:
        # Check if the provided date directory exists
        if selected_date not in date_dirs:
            print(f"Error: Date directory '{selected_date}' not found in {base_dir}.")
            print(f"Available directories: {', '.join(date_dirs)}")
            sys.exit(1)

    # Call the reusable function
    generate_hashes(selected_date, compressed_file_path, original_file_path)

if __name__ == "__main__":
    main()
