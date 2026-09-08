#!/usr/bin/env python3
"""
Create Drum Rack Kits — several 32-pad racks, each pad a velocity-layered,
round-robin Sampler drawn from a themed selection of instruments.

templates/sampler_drum_rack_template.adg is a full 32-pad Drum Rack built in
Ableton, with a real Sampler already loaded on every pad (macros, colors,
choke groups, etc. all authored by hand). Every pad's SendingNote is fixed
at 60 (C3) regardless of which note triggers the pad. This script only
touches each pad's MultiSampleMap/SampleParts — nothing structural about the
rack (macros, mixer, view state) is reconstructed or copied, so there's
nothing to fall out of sync with the donor.

Also generates randomized kits: 32 instruments sampled from the entire
library (all 9 categories), seeded per kit index for reproducible re-runs.

The full library catalog excludes long/evolving material (rolls, swells,
crescendos, reverses, bowed/scraped/rattled gong articulations, and the
whole Transitions category, which is nothing but those) — everything here
is meant to trigger as a one-shot hit. The excluded gong/bass-drum
articulations get their own dedicated "Gong Articulations" kit instead of
being dropped entirely.

Combo kits add a third generation mode on top of the curated/random ones:
32 pads are split into fixed "roles" (kick/snare/tom/hat-cymbal/metal-impact/
perc-junk/wildcard) that mimic a familiar kit layout — low notes always
kick-like, high notes always wildcard — while which specific instrument
fills each role is randomized per kit. Predictable shape, varied content.

Every pad is also colored by its actual source category (not a name guess),
using the CATEGORY_COLORS Ableton DocumentColorIndex map below.

Usage:
    export PYTHONPATH=src
    python3 scripts/create_variety_drum_rack.py
"""

import random
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ableton_device_creator.core import decode_adg, encode_adg
from ableton_device_creator.sampler import SamplerCreator
from multisample_utils import build_sample_parts, enable_round_robin, parse_velocity_layers, velocity_bins

SAMPLE_LIBRARY_ROOT = Path("/Users/Shared/Music/Soundbanks/Ben Multisamples/Heavyocity/Damage")
DRUM_RACK_TEMPLATE = Path(__file__).parent.parent / "templates" / "sampler_drum_rack_template.adg"
OUTPUT_BASE_DIR = SAMPLE_LIBRARY_ROOT / "Drum Racks"
MIC_POSITIONS = ["Close", "Full"]  # builds one identical set of kits per mic position, in its own subfolder

PAD_ROOT_NOTE = 60  # C3 — matches every pad's fixed SendingNote
NUM_RANDOM_KITS = 5
RANDOM_KIT_SIZE = 32
RANDOM_SEED_BASE = 20250701

# Folders excluded from the catalog entirely (long/evolving, not one-shot hits).
EXCLUDED_CATEGORIES = {"Transitions"}
EXCLUDE_NAME_RE = re.compile(r"roll|swell|cresc|reverse|moan|wail|rattle|scrape|scratch", re.IGNORECASE)
ARTICULATION_NAME_RE = re.compile(r"moan|wail|rattle|scrape|scratch", re.IGNORECASE)

# Ableton DocumentColorIndex per source category — reused indices already
# validated elsewhere in this project (color_mapper.py / CLAUDE.md).
CATEGORY_COLORS = {
    "Organic": 9,
    "Ethnic": 16,
    "Taikos": 26,
    "Cymbals-Gongs": 45,
    "Damaged Elements": 60,
    "Hybrid Elements": 43,
    "Found Sounds": 49,
    "Monster Ensembles": 58,
    "Transitions": 62,
}

NUM_COMBO_KITS = 25
COMBO_SEED_BASE = 20250801
# Ordered high-note-to-low-note (first role fills the highest ReceivingNote,
# matching build_kit's descending pad sort) so kicks land low, wildcards high.
ROLE_SLOTS = [
    ("WILDCARD", 4),
    ("PERC_JUNK", 4),
    ("METAL_IMPACT", 6),
    ("HAT_CYMBAL", 6),
    ("TOM", 4),
    ("SNARE", 4),
    ("KICK", 4),
]


def classify_role(category: str, name: str) -> str:
    """Assign one instrument to exactly one kit-shape role, first match wins."""
    if category == "Organic":
        if re.search(r"bass drum|gran casa|g\. casa", name, re.IGNORECASE):
            return "KICK"
        if re.search(r"snare", name, re.IGNORECASE):
            return "SNARE"
        if re.search(r"tom", name, re.IGNORECASE):
            return "TOM"
        return "WILDCARD"
    if category == "Damaged Elements":
        if re.search(r"kick", name, re.IGNORECASE):
            return "KICK"
        if re.search(r"snare", name, re.IGNORECASE):
            return "SNARE"
        if re.search(r"\btom\b", name, re.IGNORECASE):
            return "TOM"
        if re.search(r"hat|cym", name, re.IGNORECASE):
            return "HAT_CYMBAL"
        if re.search(r"metal|clang|anvil|punch|smash|crunch|bang|impact|hammer", name, re.IGNORECASE):
            return "METAL_IMPACT"
        return "WILDCARD"
    if category in ("Ethnic", "Taikos"):
        return "TOM"
    if category == "Cymbals-Gongs":
        return "HAT_CYMBAL"
    if category == "Hybrid Elements":
        return "METAL_IMPACT"
    if category == "Found Sounds":
        return "PERC_JUNK"
    if category == "Monster Ensembles":
        if re.search(r"bucket kicks|bass blast", name, re.IGNORECASE):
            return "KICK"
        return "PERC_JUNK"
    return "WILDCARD"

# Each kit is a themed spread of (category, instrument) pairs, using each
# folder's "Close" mic position.
KITS = {
    "Variety": [
        ("Organic", "Gran Casa 32in"),
        ("Organic", "Bass Drum 22in"),
        ("Damaged Elements", "Blocked Kick"),
        ("Organic", "High Snare"),
        ("Damaged Elements", "Crowed Snare"),
        ("Organic", "Tom 14in"),
        ("Organic", "Roto Tom 12in"),
        ("Damaged Elements", "Tom of Death"),
        ("Ethnic", "Alfaias"),
        ("Ethnic", "Dhols"),
        ("Ethnic", "Tombaks Open Hands"),
        ("Ethnic", "Darbukas Open Hands"),
        ("Ethnic", "Surdos"),
        ("Taikos", "Low Taiko 25in"),
        ("Taikos", "Mid Taiko 19in"),
        ("Taikos", "High Taikos"),
        ("Cymbals-Gongs", "Crash Cymbal 1"),
        ("Cymbals-Gongs", "Ride Cymbal 1"),
        ("Cymbals-Gongs", "Piatti Hi-Hat Tight"),
        ("Cymbals-Gongs", "Small Gong 32in"),
        ("Damaged Elements", "Alien Hat"),
        ("Damaged Elements", "Clanger Stutter Cym"),
        ("Hybrid Elements", "Metallic Crash Large"),
        ("Hybrid Elements", "Anvil to the Face"),
        ("Hybrid Elements", "Sub Debris Punch"),
        ("Hybrid Elements", "Bell Ringer Punch"),
        ("Found Sounds", "Trash Can - High"),
        ("Found Sounds", "Dumpster Wrench 1"),
        ("Found Sounds", "Metal Pole Clangs"),
        ("Monster Ensembles", "Monster Low War Drums"),
        ("Monster Ensembles", "Monster High Buckets"),
        ("Hybrid Elements", "Planet Collision"),
    ],
    "Organic Percussion": [
        ("Organic", "Gran Casa 40in"),
        ("Organic", "Bass Drum 24in"),
        ("Organic", "High Snare"),
        ("Organic", "Mid Snare"),
        ("Organic", "Low Snare"),
        ("Organic", "Tom 8in"),
        ("Organic", "Tom 10in"),
        ("Organic", "Tom 12in"),
        ("Organic", "Tom 14in"),
        ("Organic", "Tom 16in"),
        ("Organic", "Roto Tom 8in"),
        ("Organic", "Roto Tom 12in"),
        ("Organic", "Roto Tom 14in"),
        ("Ethnic", "Alfaias"),
        ("Ethnic", "Low Alfaia"),
        ("Ethnic", "Mid Alfaia"),
        ("Ethnic", "Dhols"),
        ("Ethnic", "Low Dhol"),
        ("Ethnic", "Mid Dhol"),
        ("Ethnic", "Dunun"),
        ("Ethnic", "Low Dunun"),
        ("Ethnic", "High Dunun"),
        ("Ethnic", "Darbukas Open Hands"),
        ("Ethnic", "Darbukas Rims"),
        ("Ethnic", "Tombaks Open Hands"),
        ("Ethnic", "Tombaks Muted Hands"),
        ("Ethnic", "Tombaks Rims"),
        ("Ethnic", "Frame Drums Hands"),
        ("Ethnic", "Frame Drums Fingertips"),
        ("Ethnic", "Surdos"),
        ("Taikos", "Low Taiko 25in"),
        ("Taikos", "Mid Taiko 19in"),
    ],
    "Damaged Glitch": [
        ("Damaged Elements", "Blocked Kick"),
        ("Damaged Elements", "Destructo Kick"),
        ("Damaged Elements", "Gurgle Kick"),
        ("Damaged Elements", "Head Puncher Kick"),
        ("Damaged Elements", "Crowed Snare"),
        ("Damaged Elements", "Dive Ripper Snare"),
        ("Damaged Elements", "Gunshot Snare"),
        ("Damaged Elements", "Ping Shot Snare"),
        ("Damaged Elements", "Alien Hat"),
        ("Damaged Elements", "Blip Hat"),
        ("Damaged Elements", "Crispy Hat Closed"),
        ("Damaged Elements", "Crispy Hat Open"),
        ("Damaged Elements", "Clocking Tom"),
        ("Damaged Elements", "DestructoTom"),
        ("Damaged Elements", "Tom of Death"),
        ("Damaged Elements", "Clanger Stutter Cym"),
        ("Damaged Elements", "GrungeCrasher Cym"),
        ("Damaged Elements", "Metal Pinger 01"),
        ("Damaged Elements", "Dirty Metal"),
        ("Damaged Elements", "Broken Bucket"),
        ("Hybrid Elements", "Anvil to the Face"),
        ("Hybrid Elements", "Metallic Crash Large"),
        ("Hybrid Elements", "Metallic Crash Medium"),
        ("Hybrid Elements", "Sub Debris Punch"),
        ("Hybrid Elements", "Bell Ringer Punch"),
        ("Hybrid Elements", "Knockout Thud"),
        ("Hybrid Elements", "Clang Diver"),
        ("Hybrid Elements", "Broken Metal Frame"),
        ("Found Sounds", "Trash Can - High"),
        ("Found Sounds", "Trash Can - Low"),
        ("Found Sounds", "Dumpster Wrench 1"),
        ("Found Sounds", "Metal Pole Clangs"),
    ],
    "Cinematic Impact": [
        ("Monster Ensembles", "Monster High Buckets"),
        ("Monster Ensembles", "Monster High Ethnics"),
        ("Monster Ensembles", "Monster High Ethnics Rims"),
        ("Monster Ensembles", "Monster Low Bass Blast"),
        ("Monster Ensembles", "Monster Low Bucket Kicks"),
        ("Monster Ensembles", "Monster Low Ethnic"),
        ("Monster Ensembles", "Monster Low Jangles"),
        ("Monster Ensembles", "Monster Low War Drums"),
        ("Monster Ensembles", "Monster Mids"),
        ("Monster Ensembles", "Monster Mids Rims"),
        ("Monster Ensembles", "Monster Trash Brigade"),
        ("Cymbals-Gongs", "Large Gong 40in"),
        ("Cymbals-Gongs", "Medium Gong 36in"),
        ("Cymbals-Gongs", "Small Gong 32in"),
        ("Cymbals-Gongs", "Chopper Cymbal"),
        ("Cymbals-Gongs", "Crash Cymbal 1"),
        ("Cymbals-Gongs", "Crash Cymbal 2"),
        ("Cymbals-Gongs", "Crash Cymbal 3"),
        ("Cymbals-Gongs", "Ride Cymbal 1"),
        ("Cymbals-Gongs", "Ride Cymbal 2"),
        ("Hybrid Elements", "Hybrid Sub 01"),
        ("Hybrid Elements", "Hybrid Sub 03"),
        ("Hybrid Elements", "Planet Collision"),
        ("Hybrid Elements", "The Anvil"),
        ("Hybrid Elements", "Metallic Crash Large"),
        ("Hybrid Elements", "Metallic Boom"),
        ("Hybrid Elements", "Metallic Force"),
        ("Hybrid Elements", "Power Wall"),
        ("Hybrid Elements", "Cannon Fodder"),
        ("Hybrid Elements", "Atomic Cloud"),
        ("Hybrid Elements", "Explosive Decisions"),
        ("Hybrid Elements", "Steel Vengeance"),
    ],
    "Taikos": [
        ("Taikos", "Chinese Toms"),
        ("Taikos", "High Chinese Tom"),
        ("Taikos", "High Taikos"),
        ("Taikos", "Low Chinese Tom"),
        ("Taikos", "Low Taiko 24in"),
        ("Taikos", "Low Taiko 25in"),
        ("Taikos", "Low Taikos"),
        ("Taikos", "Mega Low Taiko 60in"),
        ("Taikos", "Mid Taiko 19in"),
        ("Taikos", "Mid Taiko 19in Rim"),
        ("Taikos", "Mid Taiko 20in"),
        ("Taikos", "Mid Taiko 20in Rim"),
        ("Taikos", "Mid Taikos"),
        ("Taikos", "Mid Taikos Rims"),
    ],
    "Cymbals and Gongs": [
        ("Cymbals-Gongs", "Chopper Cymbal"),
        ("Cymbals-Gongs", "Crash Cymbal 1"),
        ("Cymbals-Gongs", "Crash Cymbal 2"),
        ("Cymbals-Gongs", "Crash Cymbal 3"),
        ("Cymbals-Gongs", "Crash Cymbals 1"),
        ("Cymbals-Gongs", "Crash Cymbals 2"),
        ("Cymbals-Gongs", "Crash Cymbals 3"),
        ("Cymbals-Gongs", "Ride Cymbal 1"),
        ("Cymbals-Gongs", "Ride Cymbal 2"),
        ("Cymbals-Gongs", "Piatti 16in"),
        ("Cymbals-Gongs", "Piatti 18in"),
        ("Cymbals-Gongs", "Piatti 20in"),
        ("Cymbals-Gongs", "Piatti Hi-Hat Loose"),
        ("Cymbals-Gongs", "Piatti Hi-Hat Medium"),
        ("Cymbals-Gongs", "Piatti Hi-Hat Tight"),
        ("Cymbals-Gongs", "Small Gong 32in"),
        ("Cymbals-Gongs", "Medium Gong 36in"),
        ("Cymbals-Gongs", "Large Gong 40in"),
    ],
    "Ethnic Drums": [
        ("Ethnic", "Alfaias"),
        ("Ethnic", "Low Alfaia"),
        ("Ethnic", "Mid Alfaia"),
        ("Ethnic", "Dhols"),
        ("Ethnic", "Low Dhol"),
        ("Ethnic", "Mid Dhol"),
        ("Ethnic", "Dunun"),
        ("Ethnic", "Low Dunun"),
        ("Ethnic", "High Dunun"),
        ("Ethnic", "Darbukas Open Hands"),
        ("Ethnic", "Darbukas Rims"),
        ("Ethnic", "Tombaks Open Hands"),
        ("Ethnic", "Tombaks Muted Hands"),
        ("Ethnic", "Tombaks Rims"),
        ("Ethnic", "Tombaks Side Clacks"),
        ("Ethnic", "Frame Drums Hands"),
        ("Ethnic", "Frame Drums Fingertips"),
        ("Ethnic", "Frame Drum Rims"),
        ("Ethnic", "Surdos"),
        ("Ethnic", "Stick Clicks - Drum Sticks"),
        ("Ethnic", "Stick Clicks - PVC Pipes"),
        ("Ethnic", "Stick Clicks - Puilis"),
        ("Ethnic", "Stick Clicks - Taiko Bachi"),
        # Ethnic only has 23 instruments — filled out to 32 pads with Organic
        # toms/kicks for a cohesive acoustic low-end.
        ("Organic", "Gran Casa 32in"),
        ("Organic", "Bass Drum 22in"),
        ("Organic", "Tom 10in"),
        ("Organic", "Tom 12in"),
        ("Organic", "Tom 14in"),
        ("Organic", "Tom 16in"),
        ("Organic", "Roto Tom 8in"),
        ("Organic", "Roto Tom 12in"),
        ("Organic", "Roto Tom 14in"),
    ],
    "Hybrid Elements": [
        ("Hybrid Elements", "Abrupt Wood Slam"),
        ("Hybrid Elements", "Anvil to the Face"),
        ("Hybrid Elements", "Atomic Cloud"),
        ("Hybrid Elements", "Bell Ringer Punch"),
        ("Hybrid Elements", "Blowback"),
        ("Hybrid Elements", "Bottom Feeder"),
        ("Hybrid Elements", "Break the Mic"),
        ("Hybrid Elements", "Broken Debris 01"),
        ("Hybrid Elements", "Broken Machines"),
        ("Hybrid Elements", "Broken Metal Frame"),
        ("Hybrid Elements", "Cannon Fodder"),
        ("Hybrid Elements", "Clang Diver"),
        ("Hybrid Elements", "Clanky Shakes"),
        ("Hybrid Elements", "Debris Gut Punch"),
        ("Hybrid Elements", "Dirty Pound"),
        ("Hybrid Elements", "Door Slam Shards"),
        ("Hybrid Elements", "Earthy Shards"),
        ("Hybrid Elements", "Ejector Blast"),
        ("Hybrid Elements", "Explosive Decisions"),
        ("Hybrid Elements", "Falling Projectiles"),
        ("Hybrid Elements", "Fuzz Stomp"),
        ("Hybrid Elements", "Ghost Machine"),
        ("Hybrid Elements", "Hollow Metalic"),
        ("Hybrid Elements", "Jettison"),
        ("Hybrid Elements", "Jingle Submarine"),
        ("Hybrid Elements", "Junk Slam"),
        ("Hybrid Elements", "Klaxon Control"),
        ("Hybrid Elements", "Knockout Thud"),
        ("Hybrid Elements", "Metallic Boom"),
        ("Hybrid Elements", "Metallic Crash Large"),
        ("Hybrid Elements", "Planet Collision"),
        ("Hybrid Elements", "Power Wall"),
    ],
    "Damaged Elements": [
        ("Damaged Elements", "Aliased"),
        ("Damaged Elements", "Bang And Boom"),
        ("Damaged Elements", "Bazaar Hazard"),
        ("Damaged Elements", "Blocked 2"),
        ("Damaged Elements", "Broken Transmitter"),
        ("Damaged Elements", "Bucket Clash"),
        ("Damaged Elements", "Cage Match 1"),
        ("Damaged Elements", "Chained"),
        ("Damaged Elements", "Clave Hat"),
        ("Damaged Elements", "Crack Ring"),
        ("Damaged Elements", "Crunch Time"),
        ("Damaged Elements", "Crusty Clapper 1"),
        ("Damaged Elements", "Cyborg Meeting 1"),
        ("Damaged Elements", "Damage Face"),
        ("Damaged Elements", "Darkblast"),
        ("Damaged Elements", "Dish Plate"),
        ("Damaged Elements", "Dopple Down"),
        ("Damaged Elements", "Downfall"),
        ("Damaged Elements", "Dry Snap"),
        ("Damaged Elements", "Duck This"),
        ("Damaged Elements", "Dust Bunny"),
        ("Damaged Elements", "Fractured Hall"),
        ("Damaged Elements", "Gas Leak"),
        ("Damaged Elements", "Ghost Pit"),
        ("Damaged Elements", "Gigantus Tomus"),
        ("Damaged Elements", "Gun Powder"),
        ("Damaged Elements", "Hollow Boomer"),
        ("Damaged Elements", "Kickish"),
        ("Damaged Elements", "Knockit"),
        ("Damaged Elements", "MegaBite"),
        ("Damaged Elements", "Nasal Punch"),
        ("Damaged Elements", "Robo Punch"),
    ],
    "Monster Ensembles": [
        ("Monster Ensembles", "Monster High Buckets"),
        ("Monster Ensembles", "Monster High Ethnics"),
        ("Monster Ensembles", "Monster High Ethnics Rims"),
        ("Monster Ensembles", "Monster Low Bass Blast"),
        ("Monster Ensembles", "Monster Low Bucket Kicks"),
        ("Monster Ensembles", "Monster Low Ethnic"),
        ("Monster Ensembles", "Monster Low Jangles"),
        ("Monster Ensembles", "Monster Low War Drums"),
        ("Monster Ensembles", "Monster Mids"),
        ("Monster Ensembles", "Monster Mids Rims"),
        ("Monster Ensembles", "Monster Trash Brigade"),
    ],
    "Organic": [
        ("Organic", "All Toms (Rods)"),
        ("Organic", "All Toms (Sticks)"),
        ("Organic", "Bass Drum 20in"),
        ("Organic", "Bass Drum 22in"),
        ("Organic", "Bass Drum 24in"),
        ("Organic", "Bass Drums"),
        ("Organic", "Gran Casa 32in"),
        ("Organic", "Gran Casa 40in"),
        ("Organic", "Gran Casa 70in"),
        ("Organic", "High Snare"),
        ("Organic", "High Toms (Sticks)"),
        ("Organic", "Low Snare"),
        ("Organic", "Low Toms (Sticks)"),
        ("Organic", "Low Toms Rims"),
        ("Organic", "Mid Snare"),
        ("Organic", "Mid Toms (Rods)"),
        ("Organic", "Mid Toms (Sticks)"),
        ("Organic", "Roto Tom 12in"),
        ("Organic", "Roto Tom 14in"),
        ("Organic", "Roto Tom 8in"),
        ("Organic", "Single Head Tom 20in"),
        ("Organic", "Single Head Tom 22in"),
        ("Organic", "Single Head Toms"),
        ("Organic", "Snares Off"),
        ("Organic", "Snares On"),
        ("Organic", "Snares Rims"),
        ("Organic", "Tom 10in"),
        ("Organic", "Tom 12in"),
        ("Organic", "Tom 13in"),
        ("Organic", "Tom 14in"),
        ("Organic", "Tom 16in"),
        ("Organic", "Tom 8in"),
    ],
    "Found Sounds": [
        ("Found Sounds", "Dumpster Crowbar 1"),
        ("Found Sounds", "Dumpster Crowbar 2"),
        ("Found Sounds", "Dumpster High Hammer"),
        ("Found Sounds", "Dumpster Low Hammer 1"),
        ("Found Sounds", "Dumpster Low Hammer 2"),
        ("Found Sounds", "Dumpster Wrench 1"),
        ("Found Sounds", "Dumpster Wrench 2"),
        ("Found Sounds", "Dumpster Wrench 3"),
        ("Found Sounds", "Dumpster Wrench 4"),
        ("Found Sounds", "Hammers on Crowbars"),
        ("Found Sounds", "Low Plastic Trash Bins"),
        ("Found Sounds", "Low Plastic Tubs"),
        ("Found Sounds", "Low Trash Cans 1"),
        ("Found Sounds", "Metal Pole Clangs"),
        ("Found Sounds", "Plastic High Buckets"),
        ("Found Sounds", "Plastic Mid Buckets"),
        ("Found Sounds", "Plastic Mid Buckets Rims"),
        ("Found Sounds", "Rod on Trash Can - High"),
        ("Found Sounds", "Rod on Trash Can -Low"),
        ("Found Sounds", "Rod on Trash Lid"),
        ("Found Sounds", "Rods on Trash Cans - High"),
        ("Found Sounds", "Rods on Trash Cans - Low"),
        ("Found Sounds", "Rods on Trash Lids"),
        ("Found Sounds", "Small Metal Buckets - High"),
        ("Found Sounds", "Small Metal Buckets - Low"),
        ("Found Sounds", "Trash Can - High"),
        ("Found Sounds", "Trash Can - Low"),
    ],
    # Bowed/scraped/rattled gong & bass-drum technique articulations — long,
    # evolving textures rather than hits. Kept separate from the main kits.
    "Gong Articulations": [
        ("Cymbals-Gongs", "Gong 30in FX - Moan 01"),
        ("Cymbals-Gongs", "Gong 30in FX - Moan 02"),
        ("Cymbals-Gongs", "Gong 30in FX - Rattle 01"),
        ("Cymbals-Gongs", "Gong 30in FX - Rattle 02"),
        ("Cymbals-Gongs", "Gong 30in FX - Scrape 01"),
        ("Cymbals-Gongs", "Gong 30in FX - Scrape 02"),
        ("Cymbals-Gongs", "Gong 30in FX - Wail 01"),
        ("Cymbals-Gongs", "Gong 30in FX - Wail 02"),
        ("Cymbals-Gongs", "Gong 32in FX - Moan 01"),
        ("Cymbals-Gongs", "Gong 32in FX - Moan 02"),
        ("Cymbals-Gongs", "Gong 32in FX - Rattle 01"),
        ("Cymbals-Gongs", "Gong 32in FX - Rattle 02"),
        ("Cymbals-Gongs", "Gong 32in FX - Scrape 01"),
        ("Cymbals-Gongs", "Gong 32in FX - Scrape 02"),
        ("Cymbals-Gongs", "Gong 32in FX - Scratch 01"),
        ("Cymbals-Gongs", "Gong 32in FX - Scratch 02"),
        ("Cymbals-Gongs", "Gong 32in FX - R. Scrape"),
        ("Cymbals-Gongs", "Gong 40in FX - Moan 01"),
        ("Cymbals-Gongs", "Gong 40in FX - Moan 02"),
        ("Cymbals-Gongs", "Gong 40in FX - Rattle 01"),
        ("Cymbals-Gongs", "Gong 40in FX - Rattle 02"),
        ("Cymbals-Gongs", "Gong 40in FX - Scrape 01"),
        ("Cymbals-Gongs", "Gong 40in FX - Scrape 02"),
        ("Cymbals-Gongs", "Gong 40in FX - R. Scrape"),
        ("Organic", "G. Casa 32in Scrape FX 01"),
        ("Organic", "G. Casa 32in Scrape FX 02"),
        ("Organic", "G. Casa 32in Scrape FX 03"),
        ("Organic", "G. Casa 32in Scrape FX 04"),
        ("Organic", "G. Casa 70in Scrape FX 01"),
        ("Organic", "G. Casa 70in Scrape FX 02"),
        ("Organic", "G. Casa 70in Scrape FX 03"),
        ("Organic", "G. Casa 70in Scrape FX 04"),
    ],
}


def discover_catalog(library_root: Path) -> list:
    """Find every (category, instrument) pair with a non-empty Close folder,
    excluding rolls/swells/crescendos/reverses and the Transitions category
    entirely — this catalog is one-shot hits only."""
    catalog = []
    for category_dir in sorted(p for p in library_root.iterdir() if p.is_dir()):
        if category_dir.name in EXCLUDED_CATEGORIES:
            continue
        for instrument_dir in sorted(p for p in category_dir.iterdir() if p.is_dir()):
            if EXCLUDE_NAME_RE.search(instrument_dir.name):
                continue
            close = instrument_dir / "Close"
            if close.is_dir() and any(close.glob("*.wav")):
                catalog.append((category_dir.name, instrument_dir.name))
    return catalog


def discover_raw_catalog(library_root: Path, category: str) -> list:
    """All instruments in one category, no hit-only filtering — for a
    category that's entirely long/evolving material by design (Transitions)."""
    catalog = []
    category_dir = library_root / category
    for instrument_dir in sorted(p for p in category_dir.iterdir() if p.is_dir()):
        close = instrument_dir / "Close"
        if close.is_dir() and any(close.glob("*.wav")):
            catalog.append((category, instrument_dir.name))
    return catalog


def discover_articulation_catalog(library_root: Path) -> list:
    """All bowed/scraped/rattled gong & bass-drum technique samples across
    Cymbals-Gongs and Organic — the material discover_catalog() excludes."""
    catalog = []
    for category in ("Cymbals-Gongs", "Organic"):
        category_dir = library_root / category
        for instrument_dir in sorted(p for p in category_dir.iterdir() if p.is_dir()):
            if not ARTICULATION_NAME_RE.search(instrument_dir.name):
                continue
            close = instrument_dir / "Close"
            if close.is_dir() and any(close.glob("*.wav")):
                catalog.append((category, instrument_dir.name))
    return catalog


def build_random_kits(catalog: list) -> dict:
    kits = {}
    for i in range(1, NUM_RANDOM_KITS + 1):
        rng = random.Random(RANDOM_SEED_BASE + i)
        kits[f"Random {i:02d}"] = rng.sample(catalog, min(RANDOM_KIT_SIZE, len(catalog)))
    return kits


def build_role_pools(catalog: list) -> dict:
    pools = {}
    for category, name in catalog:
        role = classify_role(category, name)
        pools.setdefault(role, []).append((category, name))
    return pools


def build_combo_kits(role_pools: dict) -> dict:
    """Fixed kit shape (role -> pad count, high note to low note), randomized
    instrument choice per role per kit — predictable layout, varied content."""
    kits = {}
    for i in range(1, NUM_COMBO_KITS + 1):
        rng = random.Random(COMBO_SEED_BASE + i)
        instruments = []
        for role, count in ROLE_SLOTS:
            pool = role_pools.get(role, [])
            if len(pool) < count:
                raise ValueError(f"Role {role} needs {count} instruments, only {len(pool)} available")
            instruments.extend(rng.sample(pool, count))
        kits[f"Combo {i:02d}"] = instruments
    return kits


# Categories large enough that one 32-pad kit can't hold them all — every
# hit-only instrument gets split into sequential, non-overlapping racks
# instead of a hand-picked sample.
FULL_COVERAGE_CATEGORIES = ["Damaged Elements", "Hybrid Elements", "Organic"]


def build_full_coverage_kits(name_prefix: str, items: list, batch_size: int = 32) -> dict:
    """Split a full list of (category, instrument) pairs into sequential
    racks of batch_size pads, sorted alphabetically, covering every item
    with no overlaps or omissions."""
    items = sorted(items)
    kits = {}
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        kit_num = i // batch_size + 1
        kits[f"{name_prefix} {kit_num:02d}"] = batch
    return kits


def fill_pad(pad: ET.Element, creator: SamplerCreator, folder: Path) -> None:
    """Replace one pad's existing Sampler SampleParts in place with an
    instrument's velocity-layered, round-robin samples, fixed on
    PAD_ROOT_NOTE. Nothing else about the pad or rack is touched."""
    _, layers = parse_velocity_layers(folder)

    sample_map = pad.find(".//MultiSampleMap")
    if sample_map is None:
        raise ValueError("Pad's Sampler missing MultiSampleMap element")

    old_parts = sample_map.find("SampleParts")
    if old_parts is not None:
        sample_map.remove(old_parts)
    new_parts = ET.SubElement(sample_map, "SampleParts")
    for part in build_sample_parts(creator, layers, PAD_ROOT_NOTE):
        new_parts.append(part)

    enable_round_robin(sample_map)

    layer_summary = ", ".join(
        f"V{center}:{len(layers[center])}" for center, _, _ in velocity_bins(layers.keys())
    )
    print(f"    {len(layers)} velocity layers ({layer_summary})")


def color_pad(pad: ET.Element, category: str) -> None:
    """Color a pad by its actual source category (elements already exist on
    every pad in the donor, so this is a direct set — no XML surgery)."""
    color = CATEGORY_COLORS.get(category)
    if color is None:
        return
    color_elem = pad.find("DocumentColorIndex")
    if color_elem is not None:
        color_elem.set("Value", str(color))
    auto_colored = pad.find("AutoColored")
    if auto_colored is not None:
        auto_colored.set("Value", "false")


def build_kit(kit_name: str, instruments: list, creator: SamplerCreator, mic: str, output_dir: Path) -> bool:
    output_path = output_dir / f"Drum_Rack_{kit_name.replace(' ', '_')}.adg"

    print(f"\n=== [{mic}] {kit_name} ({len(instruments)} pads) ===")

    rack_xml = decode_adg(DRUM_RACK_TEMPLATE)
    rack_root = ET.fromstring(rack_xml)

    pads = rack_root.findall(".//BranchPresets/DrumBranchPreset")
    pads.sort(key=lambda p: int(p.find(".//ZoneSettings/ReceivingNote").get("Value")), reverse=True)

    if len(instruments) > len(pads):
        print(f"  Error: {len(instruments)} instruments but only {len(pads)} pads available")
        return False

    built = 0
    missing = []
    for pad, (category, name) in zip(pads, instruments):
        folder = SAMPLE_LIBRARY_ROOT / category / name / mic
        if not folder.exists():
            print(f"  SKIP (missing folder): {category}/{name}/{mic}")
            missing.append(f"{category}/{name}")
            continue

        note = pad.find(".//ZoneSettings/ReceivingNote").get("Value")
        print(f"  Note {note}: {category}/{name}")

        fill_pad(pad, creator, folder)
        color_pad(pad, category)

        name_elem = pad.find("Name")
        if name_elem is not None:
            name_elem.set("Value", name)
        built += 1

    if missing:
        print(f"\n  {len(missing)} of {len(instruments)} instrument folders were missing — aborting without writing output.")
        return False

    xml_string = ET.tostring(rack_root, encoding="unicode", xml_declaration=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    encode_adg(xml_string, output_path)
    print(f"  Created: {output_path} ({built} pads)")
    return True


def compose_all_kits() -> dict:
    """Scan the library and assemble every kit definition — curated, random,
    combo, and full-coverage — exactly as the per-mic build uses them. Shared
    with create_damage_close_room_racks.py so both builds stay in sync."""
    print(f"Scanning library: {SAMPLE_LIBRARY_ROOT}")
    catalog = discover_catalog(SAMPLE_LIBRARY_ROOT)
    print(f"  {len(catalog)} hit-only instrument folders found")
    random_kits = build_random_kits(catalog)

    role_pools = build_role_pools(catalog)
    print("  Role pool sizes: " + ", ".join(f"{role}={len(role_pools.get(role, []))}" for role, _ in ROLE_SLOTS))
    combo_kits = build_combo_kits(role_pools)

    full_coverage_kits = {}
    for category in FULL_COVERAGE_CATEGORIES:
        items = [pair for pair in catalog if pair[0] == category]
        batch = build_full_coverage_kits(category, items)
        print(f"  {category}: {len(items)} instruments split into {len(batch)} racks")
        full_coverage_kits.update(batch)

    articulation_catalog = discover_articulation_catalog(SAMPLE_LIBRARY_ROOT)
    batch = build_full_coverage_kits("Gong Articulations", articulation_catalog)
    print(f"  Gong Articulations: {len(articulation_catalog)} instruments split into {len(batch)} racks")
    full_coverage_kits.update(batch)

    transitions_catalog = discover_raw_catalog(SAMPLE_LIBRARY_ROOT, "Transitions")
    batch = build_full_coverage_kits("Transitions", transitions_catalog)
    print(f"  Transitions: {len(transitions_catalog)} instruments split into {len(batch)} racks")
    full_coverage_kits.update(batch)

    return {**KITS, **random_kits, **combo_kits, **full_coverage_kits}


def main():
    if not DRUM_RACK_TEMPLATE.exists():
        print(f"Error: Drum rack template not found: {DRUM_RACK_TEMPLATE}")
        sys.exit(1)

    creator = SamplerCreator(template=DRUM_RACK_TEMPLATE)

    all_kits = compose_all_kits()

    results = {}
    for mic in MIC_POSITIONS:
        output_dir = OUTPUT_BASE_DIR / mic
        for kit_name, instruments in all_kits.items():
            results[(mic, kit_name)] = build_kit(kit_name, instruments, creator, mic, output_dir)

    print("\nSummary:")
    for (mic, kit_name), ok in results.items():
        print(f"  {'OK' if ok else 'FAILED'}: [{mic}] {kit_name}")

    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
