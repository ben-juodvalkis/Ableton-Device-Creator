#!/usr/bin/env python3
"""
Safe Omnisphere Aupreset Automation Mapper

Creates safe, targeted automation mappings for performance parameters only.
Avoids risky parameters that could affect patch structure (like linkvs).
"""

import base64
import xml.etree.ElementTree as ET
import re
import argparse
from pathlib import Path
import time
import logging
from datetime import datetime
import os

class SafeAupresetMapper:
    """Safely maps automation to performance parameters only"""
    
    def __init__(self):
        # Setup logging to both console and file
        self.setup_logging()
        
        # Full automation mapping configuration - including linkvs for advanced control
        self.automation_config = {
            # Filter bypass - safe for live performance control
            'bypass': [
                {'device': 16, 'id': 6, 'channel': -1, 'instance': 1}
            ],
            # Envelope attack - safe performance parameter
            'attk': [
                {'device': 16, 'id': 0, 'channel': -1, 'instance': 1}
            ],
            # Envelope release - safe performance parameter  
            'rels': [
                {'device': 16, 'id': 1, 'channel': -1, 'instance': 1}
            ],
            # Layer linking - advanced control (use with caution during live performance)
            'linkvs': [
                {'device': 16, 'id': 2, 'channel': -1, 'instance': 1},  # Map 1st occurrence
                {'device': 16, 'id': 3, 'channel': -1, 'instance': 2},  # Map 2nd occurrence  
                {'device': 16, 'id': 4, 'channel': -1, 'instance': 3},  # Map 3rd occurrence
                {'device': 16, 'id': 5, 'channel': -1, 'instance': 4}   # Map 4th occurrence
            ]
        }
    
    def setup_logging(self):
        """Setup logging to both console and desktop log file"""
        # Create log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        desktop_path = os.path.expanduser("~/Desktop")
        log_filename = f"omnisphere_aupreset_mapper_{timestamp}.log"
        self.log_file_path = os.path.join(desktop_path, log_filename)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(message)s',
            handlers=[
                logging.FileHandler(self.log_file_path, encoding='utf-8'),
                logging.StreamHandler()  # Console output
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def log(self, message):
        """Log message to both console and file"""
        self.logger.info(message)
        
    def extract_preset_data(self, aupreset_path):
        """Extract and decode the preset data from aupreset file"""
        try:
            tree = ET.parse(aupreset_path)
            root = tree.getroot()
            
            # Find data0 element
            dict_elem = root.find('dict')
            if dict_elem is None:
                raise ValueError("No dict element found in aupreset")
                
            data0_found = False
            
            for child in dict_elem:
                if child.tag == 'key' and child.text == 'data0':
                    data0_found = True
                elif data0_found and child.tag == 'data':
                    encoded_data = child.text.strip() if child.text else ""
                    if not encoded_data:
                        raise ValueError("Empty data0 element")
                    decoded_data = base64.b64decode(encoded_data).decode('utf-8')
                    return decoded_data
            
            raise ValueError("No data0 element found in aupreset")
            
        except Exception as e:
            raise Exception(f"Error extracting preset data: {e}")
    
    def inject_safe_mappings(self, preset_xml_data):
        """Inject automation mappings including direct VOICE element injection for linkvs"""
        modified_data = preset_xml_data
        total_mappings = 0
        
        self.log(f"🎛️  Applying FULL automation mappings (including linkvs)...")
        
        for param_name, mappings in self.automation_config.items():
            self.log(f"\n🔍 Processing parameter '{param_name}':")
            
            if param_name == 'linkvs':
                # Special handling for linkvs - inject directly into VOICE elements
                voice_pattern = r'<VOICE\s+([^>]*)>'
                voice_matches = list(re.finditer(voice_pattern, modified_data))
                
                self.log(f"  📊 Found {len(voice_matches)} VOICE elements for linkvs injection")
                
                if len(voice_matches) >= len(mappings):
                    mappings_applied = 0
                    offset = 0
                    
                    for mapping in mappings:
                        instance = mapping['instance'] 
                        device = mapping['device']
                        param_id = mapping['id']
                        channel = mapping['channel']
                        
                        if instance <= len(voice_matches):
                            # Get the VOICE match for this instance
                            voice_match = voice_matches[instance - 1]
                            
                            # Calculate position with offset
                            match_start = voice_match.start() + offset
                            match_end = voice_match.end() + offset
                            
                            # Get the VOICE tag content
                            original_voice_tag = modified_data[match_start:match_end]
                            
                            # Create linkvs automation injection
                            linkvs_injection = (
                                f'  linkvsMidiLearnDevice0="{device}" '
                                f'linkvsMidiLearnIDnum0="{param_id}" '
                                f'linkvsMidiLearnChannel0="{channel}"'
                            )
                            
                            # Insert before the closing >
                            new_voice_tag = original_voice_tag[:-1] + linkvs_injection + ' >'
                            
                            # Replace the VOICE tag
                            modified_data = (
                                modified_data[:match_start] +
                                new_voice_tag +
                                modified_data[match_end:]
                            )
                            
                            # Update offset
                            offset += len(new_voice_tag) - len(original_voice_tag)
                            mappings_applied += 1
                            total_mappings += 1
                            
                            self.log(f"  ✅ VOICE {instance}: Injected linkvs automation → Device {device}, ID {param_id}")
                        else:
                            self.log(f"  ⚠️  VOICE {instance}: Not found (only {len(voice_matches)} VOICE elements exist)")
                    
                    self.log(f"  📈 Applied {mappings_applied}/{len(mappings)} linkvs injections")
                else:
                    self.log(f"  ⚠️  Not enough VOICE elements ({len(voice_matches)}) for {len(mappings)} mappings")
                    
            else:
                # Special handling for envelope parameters - target specific envelope types
                if param_name in ['attk', 'rels']:
                    # Look for amp envelope parameters specifically (in AENVPARAMS context)
                    aenv_pattern = f'<AENVPARAMS[^>]*{param_name}="[^"]*"[^>]*>'
                    aenv_matches = list(re.finditer(aenv_pattern, modified_data))
                    
                    if aenv_matches:
                        # Find the attk/rels parameter within the AENVPARAMS context
                        aenv_context = aenv_matches[0]  # First AENVPARAMS element
                        aenv_start = aenv_context.start()
                        aenv_end = aenv_context.end()
                        aenv_content = modified_data[aenv_start:aenv_end]
                        
                        # Find the specific parameter within this AENVPARAMS
                        param_pattern = f'{param_name}="[^"]*"'
                        param_match = re.search(param_pattern, aenv_content)
                        
                        if param_match:
                            # Calculate absolute position in the full document
                            absolute_start = aenv_start + param_match.start()
                            absolute_end = aenv_start + param_match.end()
                            
                            # Create a fake match object for consistent handling
                            class FakeMatch:
                                def __init__(self, start, end):
                                    self._start = start
                                    self._end = end
                                def start(self): return self._start
                                def end(self): return self._end
                            
                            matches = [FakeMatch(absolute_start, absolute_end)]
                            self.log(f"  📊 Found {len(matches)} amp envelope occurrence for '{param_name}'")
                        else:
                            matches = []
                            self.log(f"  ⚠️  No {param_name} found in AENVPARAMS")
                    else:
                        matches = []
                        self.log(f"  ⚠️  No AENVPARAMS found for '{param_name}'")
                else:
                    # Regular parameter handling for bypass and others
                    pattern = f'{param_name}="[^"]*"'
                    matches = list(re.finditer(pattern, modified_data))
                    
                    if not matches:
                        self.log(f"  ⚠️  No occurrences found for '{param_name}'")
                        continue
                        
                    self.log(f"  📊 Found {len(matches)} total occurrences")
                
                # Apply mappings to specific instances only
                mappings_applied = 0
                offset = 0  # Track text length changes
                
                for mapping in mappings:
                    instance = mapping['instance']
                    device = mapping['device'] 
                    param_id = mapping['id']
                    channel = mapping['channel']
                    
                    if instance <= len(matches):
                        # Get the match for this instance (1-based indexing)
                        match = matches[instance - 1]
                        
                        # Calculate position with offset from previous injections
                        match_start = match.start() + offset
                        match_end = match.end() + offset
                        
                        # Create the automation mapping injection
                        automation_injection = (
                            f' {param_name}MidiLearnDevice0="{device}" '
                            f'{param_name}MidiLearnIDnum0="{param_id}" '
                            f'{param_name}MidiLearnChannel0="{channel}"'
                        )
                        
                        # Insert automation mapping right after the parameter
                        modified_data = (
                            modified_data[:match_end] + 
                            automation_injection + 
                            modified_data[match_end:]
                        )
                        
                        # Update offset for next injection
                        offset += len(automation_injection)
                        mappings_applied += 1
                        total_mappings += 1
                        
                        self.log(f"  ✅ Instance {instance}: Mapped to Device {device}, ID {param_id}")
                        
                    else:
                        self.log(f"  ⚠️  Instance {instance}: Not found (only {len(matches)} occurrences exist)")
                
                self.log(f"  📈 Applied {mappings_applied}/{len(mappings)} mappings for '{param_name}'")
        
        self.log(f"\n🎛️  Total automation mappings applied: {total_mappings}")
        if total_mappings >= 7:
            self.log(f"     (includes linkvs layer linking - use with caution during live performance)")
        return modified_data
    
    def save_mapped_preset(self, original_path, modified_xml_data, replace_original=False):
        """Save the modified preset data back to an aupreset file"""
        
        # Parse original file to get structure
        tree = ET.parse(original_path)
        root = tree.getroot()
        
        # Find and update the data0 element
        dict_elem = root.find('dict')
        data0_found = False
        
        for child in dict_elem:
            if child.tag == 'key' and child.text == 'data0':
                data0_found = True
            elif data0_found and child.tag == 'data':
                # Encode the modified XML data
                encoded_data = base64.b64encode(modified_xml_data.encode('utf-8')).decode('ascii')
                child.text = encoded_data
                break
        
        # Use original path to replace file
        if replace_original:
            output_path = original_path
        else:
            # Generate new output path
            original_path_obj = Path(original_path)
            output_path = original_path_obj.parent / f"{original_path_obj.stem} safe mapped{original_path_obj.suffix}"
        
        # Save the modified file
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
        
        if replace_original:
            self.log(f"💾 Updated original preset: {output_path}")
        else:
            self.log(f"💾 Saved safe mapped preset: {output_path}")
        
        return output_path
    
    def map_preset(self, input_path, output_path=None, replace_original=False):
        """Main method to safely map automation parameters"""
        
        self.log(f"🔄 Processing aupreset with SAFE mapping: {input_path}")
        
        # Extract preset data
        try:
            preset_xml_data = self.extract_preset_data(input_path)
            self.log(f"📊 Extracted {len(preset_xml_data):,} characters of preset data")
        except Exception as e:
            self.log(f"❌ Failed to extract preset data: {e}")
            return None
        
        # Check if already mapped
        if "MidiLearnDevice" in preset_xml_data:
            self.log("⚠️  Preset appears to already have automation mappings")
            self.log("   Proceeding anyway - may result in duplicate mappings")
        
        # Apply safe automation mappings
        try:
            mapped_xml_data = self.inject_safe_mappings(preset_xml_data)
            
            # Calculate size difference
            size_diff = len(mapped_xml_data) - len(preset_xml_data)
            self.log(f"📈 Added {size_diff} characters of automation data")
            
        except Exception as e:
            self.log(f"❌ Failed to inject mappings: {e}")
            return None
        
        # Save mapped preset
        try:
            output_file = self.save_mapped_preset(input_path, mapped_xml_data, replace_original)
            return output_file
        except Exception as e:
            self.log(f"❌ Failed to save mapped preset: {e}")
            return None
    
    def batch_map_presets(self, input_dir, output_dir=None, pattern="*.aupreset", replace_originals=False):
        """Batch process multiple aupreset files safely with detailed logging"""
        
        batch_start_time = time.time()
        batch_start_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        input_path = Path(input_dir)
        if not input_path.exists():
            self.log(f"❌ Input directory not found: {input_dir}")
            return []
        
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
        else:
            output_path = input_path
        
        # Find aupreset files recursively
        aupreset_files = list(input_path.rglob(pattern))  # rglob = recursive glob
        self.log(f"🔍 Found {len(aupreset_files)} aupreset files to process")
        self.log(f"📅 Batch started at: {batch_start_datetime}")
        self.log(f"📂 Input directory: {input_path}")
        if replace_originals:
            self.log(f"🔄 Mode: Replacing original files")
        else:
            self.log(f"📂 Output directory: {output_path}")
        self.log(f"📄 Log file: {self.log_file_path}")
        
        if not aupreset_files:
            self.log("   No aupreset files found matching pattern")
            return []
        
        # Process each file with detailed logging
        processed_files = []
        failed_files = []
        total_input_size = 0
        total_output_size = 0
        
        for i, aupreset_file in enumerate(aupreset_files, 1):
            file_start_time = time.time()
            file_start_datetime = datetime.now().strftime("%H:%M:%S")
            
            # Get file size
            try:
                input_size = aupreset_file.stat().st_size
                total_input_size += input_size
            except Exception as e:
                input_size = 0
                self.log(f"⚠️  Could not get file size for {aupreset_file}: {e}")
            
            self.log(f"\n{'='*80}")
            self.log(f"📄 Processing file {i}/{len(aupreset_files)}")
            self.log(f"⏰ Started at: {file_start_datetime}")
            self.log(f"📁 Input:  {aupreset_file}")
            self.log(f"📊 Size:   {input_size:,} bytes ({input_size/1024:.1f} KB)")
            self.log(f"📍 Relative path: {aupreset_file.relative_to(input_path)}")
            
            if replace_originals:
                output_file = None  # Will use original file
            else:
                output_file = output_path / f"{aupreset_file.stem} safe mapped{aupreset_file.suffix}"
            
            try:
                result = self.map_preset(aupreset_file, output_file, replace_originals)
                file_end_time = time.time()
                file_duration = file_end_time - file_start_time
                
                if result:
                    # Get output file size
                    try:
                        output_size = Path(result).stat().st_size
                        total_output_size += output_size
                        size_increase = output_size - input_size
                        size_increase_pct = (size_increase / input_size * 100) if input_size > 0 else 0
                    except Exception as e:
                        output_size = 0
                        size_increase = 0
                        size_increase_pct = 0
                        self.log(f"⚠️  Could not get output file size: {e}")
                    
                    processed_files.append(result)
                    self.log(f"✅ SUCCESS - Processing completed in {file_duration:.2f} seconds")
                    if replace_originals:
                        self.log(f"📤 Updated: {result}")
                    else:
                        self.log(f"📤 Output: {result}")
                    self.log(f"📊 Output size: {output_size:,} bytes ({output_size/1024:.1f} KB)")
                    self.log(f"📈 Size increase: +{size_increase:,} bytes (+{size_increase_pct:.1f}%)")
                else:
                    failed_files.append({
                        'file': aupreset_file,
                        'error': 'Processing returned None',
                        'duration': file_end_time - file_start_time
                    })
                    self.log(f"❌ FAILED - Processing returned None after {file_duration:.2f} seconds")
                    
            except Exception as e:
                file_end_time = time.time()
                file_duration = file_end_time - file_start_time
                failed_files.append({
                    'file': aupreset_file,
                    'error': str(e),
                    'duration': file_duration
                })
                self.log(f"❌ ERROR - Exception after {file_duration:.2f} seconds: {e}")
        
        # Final summary
        batch_end_time = time.time()
        batch_duration = batch_end_time - batch_start_time
        batch_end_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self.log(f"\n{'='*80}")
        self.log(f"🎯 BATCH PROCESSING COMPLETE")
        self.log(f"={'='*80}")
        self.log(f"📅 Started:  {batch_start_datetime}")
        self.log(f"📅 Ended:    {batch_end_datetime}")
        self.log(f"⏱️  Duration: {batch_duration:.2f} seconds ({batch_duration/60:.1f} minutes)")
        self.log(f"")
        self.log(f"📊 RESULTS SUMMARY:")
        self.log(f"   Total files found:     {len(aupreset_files):,}")
        self.log(f"   Successfully processed: {len(processed_files):,}")
        self.log(f"   Failed:                {len(failed_files):,}")
        self.log(f"   Success rate:          {len(processed_files)/len(aupreset_files)*100:.1f}%")
        self.log(f"")
        self.log(f"📈 SIZE STATISTICS:")
        self.log(f"   Total input size:      {total_input_size:,} bytes ({total_input_size/1024/1024:.1f} MB)")
        self.log(f"   Total output size:     {total_output_size:,} bytes ({total_output_size/1024/1024:.1f} MB)")
        self.log(f"   Total size increase:   +{total_output_size-total_input_size:,} bytes")
        self.log(f"   Avg processing speed:  {len(aupreset_files)/batch_duration:.1f} files/second")
        self.log(f"📄 Complete log saved to: {self.log_file_path}")
        
        if failed_files:
            self.log(f"\n❌ FAILED FILES ({len(failed_files)}):")
            for i, failure in enumerate(failed_files, 1):
                self.log(f"   {i}. {failure['file'].name}")
                self.log(f"      Error: {failure['error']}")
                self.log(f"      Duration: {failure['duration']:.2f}s")
        
        return processed_files

def main():
    """Command line interface for safe mapping"""
    
    parser = argparse.ArgumentParser(
        description="Safely add host automation mappings to Omnisphere aupreset files (performance parameters only)"
    )
    parser.add_argument('input', help='Input aupreset file or directory')
    parser.add_argument('-o', '--output', help='Output file or directory')
    parser.add_argument('--batch', action='store_true', help='Process all aupreset files in input directory')
    parser.add_argument('--pattern', default='*.aupreset', help='File pattern for batch processing')
    parser.add_argument('--replace', action='store_true', help='Replace original files instead of creating new ones')
    
    args = parser.parse_args()
    
    print("🎛️  Full Omnisphere Aupreset Automation Mapper")
    print("=" * 55)
    print("Maps ALL parameters including linkvs layer linking")
    print("⚠️  Use linkvs automation with caution during live performance")
    if args.replace:
        print("🔄 Mode: Replacing original files (backup recommended)")
    print()
    
    mapper = SafeAupresetMapper()
    
    if args.batch:
        print(f"📂 Batch processing directory: {args.input}")
        results = mapper.batch_map_presets(args.input, args.output, args.pattern, args.replace)
        
        if results:
            print(f"\n🎉 Batch processing complete!")
            print(f"   Processed {len(results)} files successfully with SAFE mappings")
        else:
            print(f"\n❌ Batch processing failed")
    else:
        print(f"📄 Processing single file: {args.input}")
        result = mapper.map_preset(args.input, args.output, args.replace)
        
        if result:
            print(f"\n🎉 Safe mapping complete!")
            print(f"   Output: {result}")
            print(f"   Ready for live performance with safe parameter control")
        else:
            print(f"\n❌ Safe mapping failed")

if __name__ == "__main__":
    main()