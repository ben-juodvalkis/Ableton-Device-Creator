#!/usr/bin/env python3
"""
Test script to demonstrate the enhanced metadata filtering capabilities
"""

import json
from pathlib import Path

METADATA_FILE = "omnisphere_metadata.json"

def load_metadata_database():
    """Load the metadata database"""
    try:
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Metadata file not found: {METADATA_FILE}")
        print("   Run the enhanced extractor first to generate the database")
        return None
    except Exception as e:
        print(f"❌ Error loading metadata: {e}")
        return None

def filter_patches(database, genres=None, moods=None, types=None, authors=None):
    """Filter patches by multiple criteria with AND logic"""
    if not database:
        return []
    
    all_patch_ids = set(range(len(database["patches"])))
    matching_ids = all_patch_ids.copy()
    
    # Apply genre filters (AND logic)
    if genres:
        genre_matches = set()
        for genre in genres:
            if genre in database["indexes"]["byGenre"]:
                genre_matches.update(database["indexes"]["byGenre"][genre])
        matching_ids &= genre_matches
    
    # Apply mood filters (AND logic)  
    if moods:
        mood_matches = set()
        for mood in moods:
            if mood in database["indexes"]["byMood"]:
                mood_matches.update(database["indexes"]["byMood"][mood])
        matching_ids &= mood_matches
    
    # Apply type filters (AND logic)
    if types:
        type_matches = set()
        for patch_type in types:
            if patch_type in database["indexes"]["byType"]:
                type_matches.update(database["indexes"]["byType"][patch_type])
        matching_ids &= type_matches
    
    # Apply author filters
    if authors:
        author_matches = set()
        for author in authors:
            if author in database["indexes"]["byAuthor"]:
                author_matches.update(database["indexes"]["byAuthor"][author])
        matching_ids &= author_matches
    
    # Return matching patches
    return [database["patches"][patch_id] for patch_id in sorted(matching_ids)]

def demo_filtering():
    """Demonstrate various filtering scenarios"""
    
    print("🔍 Enhanced Omnisphere Metadata Filtering Demo")
    print("=" * 60)
    
    # Load database
    database = load_metadata_database()
    if not database:
        return
    
    print(f"📊 Loaded database with {database['metadata']['totalPatches']:,} patches")
    print(f"🎭 Available Genres: {len(database['indexes']['byGenre'])}")
    print(f"😊 Available Moods: {len(database['indexes']['byMood'])}")
    print(f"🎼 Available Types: {len(database['indexes']['byType'])}")
    print()
    
    # Demo 1: Show available categories
    print("📋 Available Filter Categories:")
    print("  🎭 Genres:", list(database["indexes"]["byGenre"].keys())[:10], "...")
    print("  😊 Moods:", list(database["indexes"]["byMood"].keys())[:10], "...")
    print("  🎼 Types:", list(database["indexes"]["byType"].keys())[:10], "...")
    print()
    
    # Demo 2: Electronic music
    print("🎵 Demo 1: Electronic Patches")
    electronic_patches = filter_patches(database, genres=["Electronic"])
    print(f"   Found {len(electronic_patches)} electronic patches")
    for i, patch in enumerate(electronic_patches[:5]):
        print(f"   {i+1}. {patch['name']} ({patch['library']})")
    print()
    
    # Demo 3: Dark + Electronic + Bass
    print("🎸 Demo 2: Dark Electronic Bass Patches")
    dark_bass = filter_patches(database, 
                              genres=["Electronic"], 
                              moods=["Dark", "Aggressive"],
                              types=["Bass"])
    print(f"   Found {len(dark_bass)} dark electronic bass patches")
    for i, patch in enumerate(dark_bass[:3]):
        moods_str = ", ".join(patch['moods']) if patch['moods'] else "No moods"
        print(f"   {i+1}. {patch['name']} - Moods: {moods_str}")
    print()
    
    # Demo 4: Bells and ambient
    print("🔔 Demo 3: Mysterious Bell Patches")
    mysterious_bells = filter_patches(database,
                                    types=["Bells"],
                                    moods=["Mysterious"])
    print(f"   Found {len(mysterious_bells)} mysterious bell patches")
    for i, patch in enumerate(mysterious_bells[:3]):
        types_str = ", ".join(patch['types']) if patch['types'] else "No types"
        print(f"   {i+1}. {patch['name']} - Types: {types_str}")
        print(f"       File: {patch['filePath']}")
    print()
    
    # Demo 5: Eric Persing patches
    print("👨‍🎤 Demo 4: Eric Persing Patches")
    eric_patches = filter_patches(database, authors=["Eric Persing"])
    print(f"   Found {len(eric_patches)} patches by Eric Persing")
    for i, patch in enumerate(eric_patches[:3]):
        description = patch['description'][:100] + "..." if len(patch['description']) > 100 else patch['description']
        print(f"   {i+1}. {patch['name']}")
        print(f"       Description: {description}")
    print()
    
    print("✨ Demo Complete! Ready for Max MSP integration.")

if __name__ == "__main__":
    demo_filtering()