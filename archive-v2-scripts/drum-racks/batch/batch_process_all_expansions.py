#!/usr/bin/env python3
"""
Batch Process All NI Expansions

Processes all Native Instruments Expansion libraries to create suffix-based dual kits.
"""

import argparse
import sys
from pathlib import Path
import subprocess
import time

def process_expansion(script_path: Path, template_path: Path, expansion_path: Path, output_base: Path) -> dict:
    """
    Process a single expansion library.
    
    Returns:
        dict with results: {'name': str, 'success': bool, 'dual_kits': int, 'error': str}
    """
    expansion_name = expansion_path.name
    output_folder = output_base / f"{expansion_name} Dual Kits"
    
    print(f"\n{'='*60}")
    print(f"Processing: {expansion_name}")
    print(f"{'='*60}")
    
    # Check if expansion has Samples/Drums folder
    drums_path = expansion_path / "Samples" / "Drums"
    if not drums_path.exists():
        return {
            'name': expansion_name,
            'success': False,
            'dual_kits': 0,
            'error': 'No Samples/Drums folder found'
        }
    
    try:
        # Run the suffix-based kit generator
        cmd = [
            'python3', str(script_path),
            str(template_path),
            str(expansion_path),
            '--output-folder', str(output_folder),
            '--dual'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)  # 5 minute timeout
        
        if result.returncode == 0:
            # Count generated files
            if output_folder.exists():
                dual_kits = len(list(output_folder.glob("*.adg")))
                return {
                    'name': expansion_name,
                    'success': True,
                    'dual_kits': dual_kits,
                    'error': None
                }
            else:
                return {
                    'name': expansion_name,
                    'success': False,
                    'dual_kits': 0,
                    'error': 'No output folder created'
                }
        else:
            return {
                'name': expansion_name,
                'success': False,
                'dual_kits': 0,
                'error': f"Script failed: {result.stderr.strip()}"
            }
            
    except subprocess.TimeoutExpired:
        return {
            'name': expansion_name,
            'success': False,
            'dual_kits': 0,
            'error': 'Processing timeout (5 minutes)'
        }
    except Exception as e:
        return {
            'name': expansion_name,
            'success': False,
            'dual_kits': 0,
            'error': str(e)
        }

def main():
    parser = argparse.ArgumentParser(description='Batch process all NI Expansion libraries')
    parser.add_argument('template', type=str, help='Path to ADG template file')
    parser.add_argument('--expansions-root', type=str, 
                       default='/Users/Shared/Music/Soundbanks/Native Instruments/Expansions',
                       help='Path to NI Expansions folder')
    parser.add_argument('--output-root', type=str,
                       default='/Users/Music/Desktop/All_NI_Expansion_Dual_Kits',
                       help='Root output folder')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of expansions to process (for testing)')
    parser.add_argument('--skip-existing', action='store_true',
                       help='Skip expansions that already have output folders')
    
    args = parser.parse_args()
    
    template_path = Path(args.template)
    expansions_root = Path(args.expansions_root)
    output_root = Path(args.output_root)
    script_path = Path(__file__).parent / "main_suffix_based_kits.py"
    
    # Validate inputs
    if not template_path.exists():
        print(f"Error: Template not found: {template_path}")
        return 1
    
    if not expansions_root.exists():
        print(f"Error: Expansions folder not found: {expansions_root}")
        return 1
    
    if not script_path.exists():
        print(f"Error: Script not found: {script_path}")
        return 1
    
    # Create output root
    output_root.mkdir(parents=True, exist_ok=True)
    
    # Get all expansion folders
    expansions = [p for p in expansions_root.iterdir() if p.is_dir()]
    expansions.sort()
    
    # Apply limit if specified
    if args.limit:
        expansions = expansions[:args.limit]
    
    print(f"Found {len(expansions)} expansion libraries to process")
    print(f"Output root: {output_root}")
    print(f"Template: {template_path.name}")
    
    # Process each expansion
    results = []
    start_time = time.time()
    
    for i, expansion_path in enumerate(expansions, 1):
        expansion_name = expansion_path.name
        output_folder = output_root / f"{expansion_name} Dual Kits"
        
        # Skip if output already exists and --skip-existing is set
        if args.skip_existing and output_folder.exists():
            print(f"\n[{i}/{len(expansions)}] Skipping {expansion_name} (already exists)")
            continue
        
        print(f"\n[{i}/{len(expansions)}] Processing {expansion_name}...")
        
        result = process_expansion(script_path, template_path, expansion_path, output_root)
        results.append(result)
        
        if result['success']:
            print(f"✓ Success: {result['dual_kits']} dual kits created")
        else:
            print(f"✗ Failed: {result['error']}")
    
    # Print summary
    elapsed = time.time() - start_time
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    total_kits = sum(r['dual_kits'] for r in successful)
    
    print(f"\n{'='*60}")
    print(f"BATCH PROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"Processed: {len(results)} expansions")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    print(f"Total dual kits created: {total_kits}")
    print(f"Time elapsed: {elapsed/60:.1f} minutes")
    print(f"Output root: {output_root}")
    
    if successful:
        print(f"\nSuccessful expansions:")
        for result in successful:
            print(f"  {result['name']}: {result['dual_kits']} dual kits")
    
    if failed:
        print(f"\nFailed expansions:")
        for result in failed:
            print(f"  {result['name']}: {result['error']}")
    
    return 0 if not failed else 1

if __name__ == "__main__":
    sys.exit(main())