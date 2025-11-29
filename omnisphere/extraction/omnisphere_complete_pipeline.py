#!/usr/bin/env python3
"""
Omnisphere Complete Pipeline
Meta-script that combines extraction, automation, and JSON generation

Pipeline:
1. Extract all Omnisphere libraries (including Nylon Sky) → temp/omnisphere_extraction/
2. Apply automation template to all patches → Omnisphere Source/
3. Restructure with type-first organization → Instruments/Omnisphere/ (symlinks)
4. Regenerate instruments.json with updated structure

Usage: python3 omnisphere_complete_pipeline.py
"""

import subprocess
import sys
import time
from pathlib import Path
import os

# Configuration
EXTRACTION_DIR = "/Users/Shared/DevWork/GitHub/Looping/scripts/preset-extraction/spectrasonics/omnisphere/extraction"
SCRIPTS_DIR = "/Users/Shared/DevWork/GitHub/Looping/scripts"
EXTRACTION_SCRIPT = "omnisphere_3_full_extractor.py"
AUTOMATION_SCRIPT = "apply_working_template_batch.py"
RESTRUCTURE_SCRIPT = "restructure-omnisphere.ts"
JSON_SCRIPT = "generate-instruments-json.ts"

def run_command(command, description, cwd=None):
    """Run a command and handle output"""
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(command)}")
    print(f"Directory: {cwd or os.getcwd()}")
    print()
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout
        )
        
        elapsed = time.time() - start_time
        
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
            
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
            
        if result.returncode == 0:
            print(f"✅ {description} completed successfully in {elapsed:.1f} seconds")
            return True
        else:
            print(f"❌ {description} failed with return code {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ {description} timed out after 30 minutes")
        return False
    except Exception as e:
        print(f"❌ {description} failed with error: {e}")
        return False

def check_prerequisites():
    """Check that all required files and directories exist"""
    print("🔍 Checking Prerequisites")
    print("=" * 60)
    
    # Check extraction script
    extraction_path = Path(EXTRACTION_DIR) / EXTRACTION_SCRIPT
    if not extraction_path.exists():
        print(f"❌ Extraction script not found: {extraction_path}")
        return False
    print(f"✅ Extraction script: {extraction_path}")
    
    # Check automation script  
    automation_path = Path(EXTRACTION_DIR) / AUTOMATION_SCRIPT
    if not automation_path.exists():
        print(f"❌ Automation script not found: {automation_path}")
        return False
    print(f"✅ Automation script: {automation_path}")
    
    # Check JSON generation script
    json_path = Path(SCRIPTS_DIR) / JSON_SCRIPT
    if not json_path.exists():
        print(f"❌ JSON script not found: {json_path}")
        return False
    print(f"✅ JSON script: {json_path}")
    
    # Check template file
    template_path = Path("/Users/Music/Desktop/omni-bend.aupreset")
    if not template_path.exists():
        print(f"❌ Automation template not found: {template_path}")
        print("   Please ensure omni-bend.aupreset exists on Desktop")
        return False
    print(f"✅ Automation template: {template_path}")
    
    # Check STEAM directory
    steam_path = Path("/Users/Shared/Music/Soundbanks/Spectrasonics/STEAM")
    if not steam_path.exists():
        print(f"❌ STEAM directory not found: {steam_path}")
        return False
    print(f"✅ STEAM directory: {steam_path}")
    
    print("✅ All prerequisites satisfied")
    return True

def main():
    """Main pipeline execution"""
    print("🎹 Omnisphere Complete Pipeline")
    print("=" * 60)
    print("This will:")
    print("1. Extract all Omnisphere libraries (including Nylon Sky)")
    print("2. Apply automation mappings + enhancements to all patches")
    print("   - Host automation (Orb radius/angle)")
    print("   - Enhanced pitch bend (2→12 semitones)")
    print("   - ArpPhase timing offset (0.02)")
    print("3. Restructure presets with type-first organization (symlinks)")
    print("   - Bass, Drums, Keys, Instruments, FX, Synth, ARP + BPM")
    print("   - ~31,000+ presets across 7 top-level categories")
    print("4. Regenerate instruments.json")
    print("5. Clean up intermediate files")
    print()
    
    # Check prerequisites
    if not check_prerequisites():
        print("❌ Prerequisites not met. Exiting.")
        sys.exit(1)
    
    pipeline_start = time.time()
    
    # Step 1: Extract all patches
    success = run_command(
        [sys.executable, EXTRACTION_SCRIPT],
        "Step 1: Extracting all Omnisphere libraries", 
        cwd=EXTRACTION_DIR
    )
    if not success:
        print("❌ Pipeline failed at extraction step")
        sys.exit(1)
    
    # Step 2: Apply automation template
    success = run_command(
        [sys.executable, AUTOMATION_SCRIPT],
        "Step 2: Applying automation template to all patches",
        cwd=EXTRACTION_DIR
    )
    if not success:
        print("❌ Pipeline failed at automation step")
        sys.exit(1)

    # Step 3: Restructure with type-first organization
    success = run_command(
        ["npx", "tsx", RESTRUCTURE_SCRIPT],
        "Step 3: Restructuring presets (type-first organization with symlinks)",
        cwd=SCRIPTS_DIR
    )
    if not success:
        print("❌ Pipeline failed at restructuring step")
        sys.exit(1)

    # Step 4: Generate instruments.json
    success = run_command(
        ["npx", "tsx", JSON_SCRIPT],
        "Step 4: Regenerating instruments.json",
        cwd=SCRIPTS_DIR
    )
    if not success:
        print("❌ Pipeline failed at JSON generation step")
        sys.exit(1)
    
    # Step 5: Clean up intermediate files
    import shutil
    intermediate_dir = "/Users/Shared/DevWork/GitHub/Looping/temp/omnisphere_extraction"

    print(f"\n{'='*60}")
    print(f"🧹 Step 5: Cleaning up intermediate files")
    print(f"{'='*60}")
    print(f"Removing: {intermediate_dir}")
    
    try:
        if Path(intermediate_dir).exists():
            shutil.rmtree(intermediate_dir)
            print("✅ Intermediate files cleaned up successfully")
        else:
            print("ℹ️  No intermediate files to clean up")
    except Exception as e:
        print(f"⚠️  Warning: Could not clean up intermediate files: {e}")
        print("   This does not affect the pipeline success")
    
    # Pipeline complete
    total_time = time.time() - pipeline_start
    
    print("\n" + "=" * 60)
    print("🎉 OMNISPHERE PIPELINE COMPLETE!")
    print("=" * 60)
    print(f"⏱️  Total time: {total_time/60:.1f} minutes")
    print()
    print("📁 Output locations:")
    print("   • Source patches: /ableton/Presets/Omnisphere Source/")
    print("   • Restructured tree: /ableton/Presets/Instruments/Omnisphere/ (symlinks)")
    print("   • JSON file: /interface/static/data/omnisphere-*.json")
    print("   • Intermediate files: Cleaned up automatically")
    print()
    print("🎹 Omnisphere 3 with Nylon Sky ready for use!")
    print("   • Complete automation mappings applied")
    print("   • Enhanced pitch bend (12 semitones)")
    print("   • ArpPhase timing offset (0.02)")
    print("   • Type-first organization (Bass, Drums, Keys, Instruments, FX, Synth, ARP + BPM)")
    print("   • Browser integration updated")
    print("   • All ~31,000+ patches available")

if __name__ == "__main__":
    main()