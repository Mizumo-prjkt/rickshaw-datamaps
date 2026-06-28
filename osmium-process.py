#!/usr/bin/env python3
import os
import sys
import subprocess
import argparse

def main():
    parser = argparse.ArgumentParser(
        description="TranspoLink Map Data Orchestrator: Unified CLI for managing map data downloads, processing, and unification."
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")
    
    # download parser
    subparsers.add_parser(
        "download", 
        help="Download map data from GeoFabrik (delegates to datamap-download.py)",
        add_help=False
    )
    
    # process parser
    subparsers.add_parser(
        "process", 
        help="Compress and split map files (delegates to processor.py)",
        add_help=False
    )
    
    # unify parser
    subparsers.add_parser(
        "unify", 
        help="Verify and merge map chunks back together (delegates to unifier.py)",
        add_help=False
    )
    
    # hash parser
    subparsers.add_parser(
        "hash", 
        help="Generate MD5 hashes for map files (delegates to genmd5.py)",
        add_help=False
    )
    
    # Parse only the first argument to determine the subcommand
    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(0)
        
    cmd = sys.argv[1]
    sub_args = sys.argv[2:]
    
    # Resolve absolute paths to the scripts
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    script_map = {
        "download": "datamap-download.py",
        "process": "processor.py",
        "unify": "unifier.py",
        "hash": "genmd5.py"
    }
    
    if cmd in ["-h", "--help"]:
        parser.print_help()
        sys.exit(0)
        
    if cmd not in script_map:
        print(f"Error: Unknown command '{cmd}'")
        parser.print_help()
        sys.exit(1)
        
    target_script = os.path.join(script_dir, script_map[cmd])
    
    if not os.path.exists(target_script):
        print(f"Error: Target script '{target_script}' does not exist.")
        sys.exit(1)
        
    # Execute target script with all passed arguments
    run_cmd = [sys.executable, target_script] + sub_args
    
    try:
        # Stream stdout/stderr in real-time
        subprocess.run(run_cmd, check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(130)

if __name__ == "__main__":
    main()
