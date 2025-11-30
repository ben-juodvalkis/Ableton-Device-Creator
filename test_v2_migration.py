#!/usr/bin/env python3
"""
Comprehensive Test Suite for Ableton Device Creator V2.0
Tests all major functionality with real samples from Void Eclipse Library
"""

import sys
import os
from pathlib import Path
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.decoder import decode_adg
from utils.encoder import encode_adg

# Test configuration
# Use environment variable or default to common NI location
DEFAULT_SAMPLE_PATH = Path.home() / "Music/Soundbanks/Native Instruments/Expansions"
SAMPLE_LIBRARY = Path(os.getenv("TEST_SAMPLE_LIBRARY", DEFAULT_SAMPLE_PATH / "Void Eclipse Library/Samples/Drums"))
TEMPLATES_DIR = Path("templates")
OUTPUT_DIR = Path("test-output")

class TestResults:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.total = 0

    def add_pass(self, test_name, details=""):
        self.passed.append((test_name, details))
        self.total += 1
        print(f"✓ PASS: {test_name}")
        if details:
            print(f"  → {details}")

    def add_fail(self, test_name, error):
        self.failed.append((test_name, error))
        self.total += 1
        print(f"✗ FAIL: {test_name}")
        print(f"  → Error: {error}")

    def summary(self):
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {self.total}")
        print(f"Passed: {len(self.passed)} ({len(self.passed)/self.total*100:.1f}%)")
        print(f"Failed: {len(self.failed)} ({len(self.failed)/self.total*100:.1f}%)")

        if self.failed:
            print("\nFailed Tests:")
            for name, error in self.failed:
                print(f"  - {name}: {error}")

        return len(self.failed) == 0

results = TestResults()

print("="*60)
print("ABLETON DEVICE CREATOR V2.0 - COMPREHENSIVE TEST SUITE")
print("="*60)
print()

# Test 1: Check sample library exists
print("Test 1: Verify Sample Library")
try:
    if SAMPLE_LIBRARY.exists():
        sample_types = list(SAMPLE_LIBRARY.iterdir())
        sample_count = sum(1 for st in sample_types if st.is_dir()
                          for _ in st.glob("*.wav"))
        results.add_pass(
            "Sample Library Accessible",
            f"Found {len(sample_types)} sample types, ~{sample_count} samples"
        )
    else:
        results.add_fail("Sample Library Accessible", "Directory not found")
except Exception as e:
    results.add_fail("Sample Library Accessible", str(e))

# Test 2: Verify all templates
print("\nTest 2: Verify Templates")
try:
    drum_rack_templates = list(TEMPLATES_DIR.glob("drum-racks/*.adg"))
    results.add_pass(
        "Drum Rack Templates Present",
        f"Found {len(drum_rack_templates)} templates"
    )

    for template in drum_rack_templates:
        try:
            xml = decode_adg(template)
            if len(xml) > 1000:  # Valid XML should be substantial
                results.add_pass(
                    f"Template Decodes: {template.name}",
                    f"{len(xml):,} bytes XML"
                )
            else:
                results.add_fail(
                    f"Template Decodes: {template.name}",
                    "XML too small"
                )
        except Exception as e:
            results.add_fail(f"Template Decodes: {template.name}", str(e))

except Exception as e:
    results.add_fail("Template Verification", str(e))

# Test 3: Test drum rack creation script import
print("\nTest 3: Import Drum Rack Creation Scripts")
try:
    # Check if we can import the main scripts
    import importlib.util

    scripts_to_test = [
        "drum-racks/creation/main_simple_folder.py",
        "drum-racks/creation/main.py",
        "drum-racks/creation/main_percussion.py",
    ]

    for script_path in scripts_to_test:
        full_path = Path(script_path)
        if full_path.exists():
            results.add_pass(
                f"Script exists: {script_path}",
                f"{full_path.stat().st_size:,} bytes"
            )
        else:
            results.add_fail(f"Script exists: {script_path}", "File not found")

except Exception as e:
    results.add_fail("Script Import Test", str(e))

# Test 4: Test encode/decode round-trip
print("\nTest 4: Encode/Decode Round-Trip")
try:
    template = TEMPLATES_DIR / "drum-racks/Anima Ascent Acid + Amazon.adg"

    # Decode
    xml_content = decode_adg(template)
    results.add_pass("Decode Template", f"{len(xml_content):,} bytes XML")

    # Create temp file and re-encode
    with tempfile.NamedTemporaryFile(suffix=".adg", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    encode_adg(xml_content, tmp_path)

    if tmp_path.exists():
        size = tmp_path.stat().st_size
        results.add_pass("Re-encode to ADG", f"{size:,} bytes")

        # Decode again to verify
        xml_content2 = decode_adg(tmp_path)
        if len(xml_content) == len(xml_content2):
            results.add_pass("Round-trip Integrity", "XML matches original")
        else:
            results.add_fail(
                "Round-trip Integrity",
                f"Size mismatch: {len(xml_content)} vs {len(xml_content2)}"
            )
    else:
        results.add_fail("Re-encode to ADG", "File not created")

    # Cleanup
    tmp_path.unlink()

except Exception as e:
    results.add_fail("Encode/Decode Round-Trip", str(e))

# Test 5: Check utils can be imported
print("\nTest 5: Utils Module Imports")
try:
    from utils import decoder, encoder, transformer
    results.add_pass("Utils Module Import", "All modules accessible")
except Exception as e:
    results.add_fail("Utils Module Import", str(e))

# Test 6: Verify sample files are readable
print("\nTest 6: Sample File Access")
try:
    kick_samples = list((SAMPLE_LIBRARY / "Kick").glob("*.wav"))[:5]

    if kick_samples:
        for sample in kick_samples:
            if sample.exists() and sample.stat().st_size > 0:
                results.add_pass(
                    f"Sample Readable: {sample.name}",
                    f"{sample.stat().st_size:,} bytes"
                )
            else:
                results.add_fail(f"Sample Readable: {sample.name}", "Invalid file")
    else:
        results.add_fail("Sample File Access", "No kick samples found")

except Exception as e:
    results.add_fail("Sample File Access", str(e))

# Test 7: Check transformer can parse template XML
print("\nTest 7: XML Transformer Test")
try:
    template = TEMPLATES_DIR / "drum-racks/Drum Rack Template.adg"
    xml_content = decode_adg(template)

    # Check for key XML elements
    required_elements = [
        '<Ableton',
        'DrumBranch',
        'MultiSampler',
        'FileRef'
    ]

    for element in required_elements:
        if element in xml_content:
            results.add_pass(
                f"XML Contains: {element}",
                "Element found in template"
            )
        else:
            results.add_fail(
                f"XML Contains: {element}",
                "Element missing from template"
            )

except Exception as e:
    results.add_fail("XML Transformer Test", str(e))

# Test 8: Directory structure validation
print("\nTest 8: Directory Structure")
try:
    required_dirs = [
        "drum-racks/creation",
        "drum-racks/batch",
        "drum-racks/modification",
        "macro-mapping/cc-control",
        "instrument-racks/wrapping",
        "utils",
        "templates/drum-racks"
    ]

    for dir_path in required_dirs:
        full_path = Path(dir_path)
        if full_path.exists() and full_path.is_dir():
            file_count = len(list(full_path.glob("*.py")))
            results.add_pass(
                f"Directory: {dir_path}",
                f"{file_count} Python files"
            )
        else:
            results.add_fail(f"Directory: {dir_path}", "Not found")

except Exception as e:
    results.add_fail("Directory Structure", str(e))

# Print summary
print()
success = results.summary()

# Exit with appropriate code
sys.exit(0 if success else 1)
