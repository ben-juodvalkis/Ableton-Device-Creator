"""
Command-line interface for Ableton Device Creator.

Provides commands for creating and modifying Ableton Live devices from the terminal.
"""

import sys
from pathlib import Path
from typing import Optional

try:
    import click
except ImportError:
    print("Error: Click is not installed. Install with: pip install ableton-device-creator[cli]")
    sys.exit(1)

from . import __version__
from .drum_racks import DrumRackCreator, DrumRackModifier
from .sampler import SamplerCreator, SimplerCreator
from .macro_mapping import DrumPadColorMapper
from .macro_mapping.unmap_batch import FileResult, unmap_tree, write_report
from .macro_mapping.hide_macros_batch import HideResult, hide_macros_tree
from .macro_mapping.hide_macros_batch import write_report as write_hide_report
from .drum_racks.ungroup_batch import UngroupResult, ungroup_tree
from .drum_racks.ungroup_batch import write_report as write_ungroup_report
from .core import decode_adg, encode_adg

# Global options
CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.version_option(version=__version__, prog_name="adc")
def main():
    """
    Ableton Device Creator - Professional toolkit for Ableton Live device creation.

    Create drum racks, samplers, and simpler devices from audio samples.
    Modify existing devices with colors, MIDI remapping, and more.

    Examples:

      # Create drum rack from samples
      adc drum-rack create samples/ -o MyRack.adg

      # Create chromatic sampler
      adc sampler create samples/ --layout chromatic

      # Apply color coding to drum rack
      adc drum-rack color MyRack.adg

    For more help on a specific command, run:
      adc COMMAND --help
    """
    pass


# ============================================================================
# DRUM RACK COMMANDS
# ============================================================================


@main.group(name="drum-rack")
def drum_rack():
    """Create and modify drum racks."""
    pass


@drum_rack.command(name="create")
@click.argument("samples_dir", type=click.Path(exists=True, file_okay=False))
@click.option(
    "-o",
    "--output",
    type=click.Path(),
    help="Output ADG file path (default: output/<folder_name>.adg)",
)
@click.option(
    "-t",
    "--template",
    type=click.Path(exists=True),
    default="templates/input_rack.adg",
    help="Template ADG file to use",
)
@click.option(
    "--layout",
    type=click.Choice(["standard", "808", "percussion"]),
    default="standard",
    help="MIDI note layout for categorized samples",
)
@click.option(
    "--categorize/--no-categorize",
    default=True,
    help="Categorize samples by type (kick, snare, etc.)",
)
@click.option(
    "--recursive/--no-recursive",
    default=True,
    help="Search subdirectories for samples",
)
def drum_rack_create(samples_dir, output, template, layout, categorize, recursive):
    """
    Create a drum rack from audio samples.

    SAMPLES_DIR: Directory containing audio samples (.wav, .aif, .flac, .mp3)

    Examples:

      # Create from folder (auto-categorize)
      adc drum-rack create samples/

      # Create with specific output
      adc drum-rack create samples/ -o MyRack.adg

      # Create with 808 layout
      adc drum-rack create samples/ --layout 808
    """
    samples_dir = Path(samples_dir)
    template = Path(template)

    if not template.exists():
        click.secho(f"Error: Template not found: {template}", fg="red")
        click.echo("Please specify a valid template with --template")
        sys.exit(1)

    click.echo(f"Creating drum rack from: {samples_dir}")
    click.echo(f"Template: {template}")
    click.echo(f"Layout: {layout}")
    click.echo(f"Categorize: {categorize}")

    try:
        creator = DrumRackCreator(template=template)

        if categorize:
            result = creator.from_categorized_folders(
                samples_dir=samples_dir, output=output, layout=layout
            )
        else:
            result = creator.from_folder(
                samples_dir=samples_dir, output=output, categorize=False, recursive=recursive
            )

        click.secho(f"✓ Created drum rack: {result}", fg="green")
        click.echo(f"  File size: {result.stat().st_size / 1024:.1f} KB")

    except Exception as e:
        click.secho(f"Error: {e}", fg="red")
        ctx_obj = click.get_current_context().obj or {}
        if ctx_obj.get("verbose", False):
            import traceback

            traceback.print_exc()
        sys.exit(1)


@drum_rack.command(name="color")
@click.argument("device", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), help="Output file (default: overwrite input)")
def drum_rack_color(device, output):
    """
    Apply color coding to drum rack pads.

    DEVICE: Path to drum rack ADG file

    Colors pads based on sample categorization:
    - Kicks: Orange
    - Snares: Red
    - Hats: Yellow
    - Claps: Pink
    - Toms: Purple
    - Cymbals: Blue
    - Percussion: Green

    Example:
      adc drum-rack color MyRack.adg
    """
    device = Path(device)

    if not device.exists():
        click.secho(f"Error: Device not found: {device}", fg="red")
        sys.exit(1)

    if output is None:
        output = device

    click.echo(f"Applying colors to: {device}")

    try:
        colorizer = DrumPadColorMapper(device)
        colorizer.apply_colors().save(output)

        click.secho(f"✓ Applied colors: {output}", fg="green")

    except Exception as e:
        click.secho(f"Error: {e}", fg="red")
        sys.exit(1)


@drum_rack.command(name="remap")
@click.argument("device", type=click.Path(exists=True))
@click.option("-s", "--shift", type=int, required=True, help="Semitones to shift MIDI notes")
@click.option("-o", "--output", type=click.Path(), help="Output file (default: overwrite input)")
@click.option(
    "--scroll-shift",
    type=int,
    default=7,
    help="Scroll position shift (default: shift/4 rounded)",
)
def drum_rack_remap(device, shift, output, scroll_shift):
    """
    Remap MIDI notes for drum rack pads.

    DEVICE: Path to drum rack ADG file

    Shifts which MIDI notes trigger which pads. Useful for changing
    the keyboard layout or octave range.

    Examples:

      # Shift up one octave (12 semitones)
      adc drum-rack remap MyRack.adg --shift 12

      # Shift down one octave
      adc drum-rack remap MyRack.adg --shift -12
    """
    device = Path(device)

    if not device.exists():
        click.secho(f"Error: Device not found: {device}", fg="red")
        sys.exit(1)

    if output is None:
        output = device

    # Auto-calculate scroll shift if not specified
    if scroll_shift == 7:  # Default value
        scroll_shift = shift // 4

    click.echo(f"Remapping MIDI notes: {device}")
    click.echo(f"  Shift: {shift:+d} semitones")
    click.echo(f"  Scroll shift: {scroll_shift}")

    try:
        modifier = DrumRackModifier(device)
        modifier.remap_notes(shift=shift, scroll_shift=scroll_shift).save(output)

        click.secho(f"✓ Remapped: {output}", fg="green")

    except Exception as e:
        click.secho(f"Error: {e}", fg="red")
        sys.exit(1)


@drum_rack.command(name="unmap")
@click.argument("root", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--out",
    "out_dir",
    type=click.Path(file_okay=False),
    help="Output tree; every unmapped rack is written at its relative path under it",
)
@click.option("--dry-run", is_flag=True, help="Classify and report only; write nothing")
@click.option(
    "--report", "report_path", type=click.Path(dir_okay=False), help="Write a JSON report here"
)
@click.option(
    "--include-nested",
    is_flag=True,
    help="Also remove mappings owned by racks nested inside the pads (default: root rack only)",
)
@click.option(
    "--bake/--no-bake",
    default=True,
    help="Write the macro-driven value into each unmapped parameter (default: bake)",
)
@click.option("--overwrite", is_flag=True, help="Replace files that already exist under --out")
@click.option(
    "--copy-unchanged/--no-copy-unchanged",
    default=True,
    help=(
        "Copy every file that is not unmapped (other racks, .adv presets) into --out unchanged, "
        "so --out is a drop-in replacement for ROOT (default: copy)"
    ),
)
def drum_rack_unmap(
    root, out_dir, dry_run, report_path, include_nested, bake, overwrite, copy_unchanged
):
    """
    Remove every macro mapping from every Drum Rack under ROOT.

    Walks ROOT recursively. Root Drum Racks are unmapped: their KeyMidi blocks
    go, each unmapped parameter takes the value its macro was driving, and the
    rack's MacroDefaults reset to -1 (exactly what Live does). Macro names and
    positions stay. Instrument Racks that contain a Drum Rack are reported, not
    modified. Anything else is skipped and counted.

    ROOT is never written to: outputs mirror the tree under --out, and every
    file that is not unmapped is copied there unchanged, so --out can replace
    ROOT as a whole. Every unmapped file is re-read and verified against its
    original; a file that fails is listed and copied unchanged instead, and the
    run continues.

    Examples:

      adc drum-rack unmap "Looping Presets/Instruments/Ableton" --dry-run

      adc drum-rack unmap "Looping Presets/Instruments/Ableton" --out "Looping Presets/Instruments/Ableton-unmapped" --report unmap.json
    """
    if not dry_run and out_dir is None:
        click.secho("Error: --out is required unless --dry-run is given", fg="red")
        sys.exit(2)

    counter = {"n": 0}

    def progress(result: FileResult) -> None:
        counter["n"] += 1
        if dry_run:
            names = ", ".join(n for n in result.macro_names if not n.startswith("Macro "))
            nested = ""
            if result.nested_group_devices:
                nested = " nested=%s (%d nested-owned KeyMidi)" % (
                    ",".join("%s:%d" % kv for kv in sorted(result.nested_group_devices.items())),
                    result.key_midi_nested,
                )
            click.echo(
                "%-11s %-22s KeyMidi=%-5d %s%s  [%s]"
                % (
                    result.action,
                    result.root_class,
                    result.key_midi_total,
                    result.path,
                    nested,
                    names,
                )
            )
        elif result.action == "failed":
            click.secho("FAILED  %s: %s" % (result.path, "; ".join(result.failures)), fg="red")
        elif counter["n"] % 100 == 0:
            click.echo("  %d files..." % counter["n"])

    try:
        report = unmap_tree(
            root,
            out_dir,
            dry_run=dry_run,
            include_nested=include_nested,
            bake=bake,
            overwrite=overwrite,
            copy_unchanged=copy_unchanged,
            progress=progress,
        )
    except (ValueError, FileExistsError, FileNotFoundError) as e:
        click.secho("Error: %s" % e, fg="red")
        sys.exit(1)

    click.echo("")
    click.secho("Totals%s:" % (" (dry run)" if dry_run else ""), bold=True)
    for key, value in report.totals.items():
        click.echo("  %-32s %d" % (key, value))
    failed = [f for f in report.files if f.action == "failed"]
    if failed:
        click.secho(
            "\n%d file(s) failed verification and were not written:" % len(failed), fg="red"
        )
        for f in failed:
            click.echo("  %s: %s" % (f.path, "; ".join(f.failures)))
    unknown = [f for f in report.files if f.unknown_params]
    if unknown:
        click.secho(
            "\n%d file(s) kept stored values for parameters with no verified curve:" % len(unknown),
            fg="yellow",
        )
        for f in unknown[:20]:
            click.echo("  %s: %s" % (f.path, ", ".join(f.unknown_params)))
    if report_path:
        write_report(report, report_path)
        click.echo("\nReport written to %s" % report_path)
    if failed:
        sys.exit(1)


@drum_rack.command(name="hide-macros")
@click.argument("root", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--out",
    "out_dir",
    type=click.Path(file_okay=False),
    help="Output tree; every edited rack is written at its relative path under it",
)
@click.option("--in-place", is_flag=True, help="Rewrite the files under ROOT instead of --out")
@click.option("--dry-run", is_flag=True, help="Classify and report only; write nothing")
@click.option(
    "--report", "report_path", type=click.Path(dir_okay=False), help="Write a JSON report here"
)
@click.option("--overwrite", is_flag=True, help="Replace files that already exist under --out")
@click.option(
    "--copy-unchanged/--no-copy-unchanged",
    default=True,
    help=(
        "Copy every file that is not edited (Instrument Racks, .adv presets) into --out "
        "unchanged, so --out is a drop-in replacement for ROOT (default: copy)"
    ),
)
def drum_rack_hide_macros(root, out_dir, in_place, dry_run, report_path, overwrite, copy_unchanged):
    """
    Hide the macro panel and clear custom macro names on every Drum Rack under ROOT.

    Walks ROOT recursively. For each preset whose root device is a Drum Rack,
    the root's AreMacroControlsVisible becomes false and its MacroDisplayNames
    go back to "Macro 1".."Macro 16". Nothing else changes: macro values,
    positions, mappings and every nested rack are left exactly as they were.
    Instrument Rack presets are skipped and counted.

    Every edited file is re-read and verified against its original; a file that
    fails is listed and left as it was, and the run continues.

    Examples:

      adc drum-rack hide-macros "Looping Presets/Instruments/Ableton" --dry-run

      adc drum-rack hide-macros "Looping Presets/Instruments/Ableton" --in-place --report hide.json
    """
    if not dry_run and not in_place and out_dir is None:
        click.secho("Error: --out or --in-place is required unless --dry-run is given", fg="red")
        sys.exit(2)

    counter = {"n": 0}

    def progress(result: HideResult) -> None:
        counter["n"] += 1
        if dry_run and result.action == "dry-run":
            click.echo(
                "%-9s hidden=%-5s %s  [%s]"
                % (result.action, result.hidden, result.path, ", ".join(result.renamed))
            )
        elif result.action == "failed":
            click.secho("FAILED  %s: %s" % (result.path, "; ".join(result.failures)), fg="red")
        elif not dry_run and counter["n"] % 250 == 0:
            click.echo("  %d files..." % counter["n"])

    try:
        report = hide_macros_tree(
            root,
            out_dir,
            dry_run=dry_run,
            in_place=in_place,
            overwrite=overwrite,
            copy_unchanged=copy_unchanged,
            progress=progress,
        )
    except (ValueError, FileExistsError, FileNotFoundError) as e:
        click.secho("Error: %s" % e, fg="red")
        sys.exit(1)

    click.echo("")
    click.secho("Totals%s:" % (" (dry run)" if dry_run else ""), bold=True)
    for key, value in report.totals.items():
        click.echo("  %-32s %d" % (key, value))
    failed = [f for f in report.files if f.action == "failed"]
    if failed:
        click.secho("\n%d file(s) failed and were left as they were:" % len(failed), fg="red")
        for f in failed:
            click.echo("  %s: %s" % (f.path, "; ".join(f.failures)))
    if report_path:
        write_hide_report(report, report_path)
        click.echo("\nReport written to %s" % report_path)
    if failed:
        sys.exit(1)


@drum_rack.command(name="ungroup")
@click.argument("root", type=click.Path(exists=True))
@click.option(
    "--out",
    "out_dir",
    type=click.Path(),
    help="Output tree (or output .adg, for a single file); every edited rack is written under it",
)
@click.option("--in-place", is_flag=True, help="Rewrite the files under ROOT instead of --out")
@click.option("--dry-run", is_flag=True, help="Classify and report only; write nothing")
@click.option(
    "--report", "report_path", type=click.Path(dir_okay=False), help="Write a JSON report here"
)
@click.option("--overwrite", is_flag=True, help="Replace files that already exist under --out")
@click.option(
    "--copy-unchanged/--no-copy-unchanged",
    default=True,
    help=(
        "Copy every file that is not edited (Instrument Racks, .adv presets) into --out "
        "unchanged, so --out is a drop-in replacement for ROOT (default: copy)"
    ),
)
def drum_rack_ungroup(root, out_dir, in_place, dry_run, report_path, overwrite, copy_unchanged):
    """
    Dissolve the nested rack on every Drum Rack pad under ROOT.

    ROOT may be a single .adg or a directory to walk. On each pad whose device
    is a single-chain Instrument, Audio Effect or MIDI Effect Rack, the wrapper
    goes and its chain's devices move into the pad chain, in order - Live's own
    "Ungroup". The mappings that addressed the dissolved rack's macros go with
    it and each freed parameter's mapping range is restored; stored values are
    never touched, so the kit sounds the same.

    A pad is left alone, with a reason, when its rack is not a plain
    pass-through: more than one chain, a return chain, a partial key or velocity
    range, a non-unity chain mixer, or a nested Drum Rack. Mappings owned by a
    rack nested deeper are kept.

    Every edited file is re-read and verified against its original; a file that
    fails is listed and left as it was, and the run continues. With no --out and
    no --in-place, a single file is written beside itself as "NAME (ungrouped).adg".

    Examples:

      adc drum-rack ungroup "British Vintage.adg" --dry-run

      adc drum-rack ungroup "British Vintage.adg"

      adc drum-rack ungroup "Damage Close" --out "Damage Close-flat" --report ungroup.json
    """
    if not dry_run and not in_place and out_dir is None and Path(root).is_dir():
        click.secho("Error: --out or --in-place is required unless --dry-run is given", fg="red")
        sys.exit(2)

    counter = {"n": 0}

    def progress(result: UngroupResult) -> None:
        counter["n"] += 1
        if result.action == "failed":
            click.secho("FAILED  %s: %s" % (result.path, "; ".join(result.failures)), fg="red")
        elif dry_run or counter["n"] <= 1:
            click.echo(
                "%-9s %2d/%-2d pads  %4d mappings  %s"
                % (
                    result.action,
                    result.ungrouped,
                    result.pads,
                    result.key_midi_removed,
                    result.path,
                )
            )
        elif not dry_run and counter["n"] % 250 == 0:
            click.echo("  %d files..." % counter["n"])

    try:
        report = ungroup_tree(
            root,
            out_dir,
            dry_run=dry_run,
            in_place=in_place,
            overwrite=overwrite,
            copy_unchanged=copy_unchanged,
            progress=progress,
        )
    except (ValueError, FileExistsError, FileNotFoundError) as e:
        click.secho("Error: %s" % e, fg="red")
        sys.exit(1)

    click.echo("")
    click.secho("Totals%s:" % (" (dry run)" if dry_run else ""), bold=True)
    for key, value in report.totals.items():
        click.echo("  %-32s %d" % (key, value))
    if report.ranges_left:
        click.echo("")
        click.echo(
            "Mapping range left stored on %d parameter kind(s) (inert once unmapped):"
            % len(report.ranges_left)
        )
        for label in report.ranges_left:
            click.echo("  %s" % label)
    written = [f for f in report.files if f.output]
    if written and len(written) <= 5:
        click.echo("")
        for f in written:
            click.echo("Wrote %s" % f.output)
    failed = [f for f in report.files if f.action == "failed"]
    if failed:
        click.secho("\n%d file(s) failed and were left as they were:" % len(failed), fg="red")
        for f in failed:
            click.echo("  %s: %s" % (f.path, "; ".join(f.failures)))
    if report_path:
        write_ungroup_report(report, report_path)
        click.echo("\nReport written to %s" % report_path)
    if failed:
        sys.exit(1)


# ============================================================================
# SAMPLER COMMANDS
# ============================================================================


@main.group(name="sampler")
def sampler():
    """Create Multi-Sampler instruments."""
    pass


@sampler.command(name="create")
@click.argument("samples_dir", type=click.Path(exists=True, file_okay=False))
@click.option(
    "-o",
    "--output",
    type=click.Path(),
    help="Output ADG file path (default: output/<folder_name>_sampler.adg)",
)
@click.option(
    "-t",
    "--template",
    type=click.Path(exists=True),
    default="templates/sampler-rack.adg",
    help="Template ADG file to use",
)
@click.option(
    "--layout",
    type=click.Choice(["chromatic", "drum", "percussion"]),
    default="chromatic",
    help="Key mapping layout",
)
@click.option(
    "--max-samples",
    type=int,
    default=32,
    help="Maximum samples per instrument (default: 32)",
)
def sampler_create(samples_dir, output, template, layout, max_samples):
    """
    Create a Multi-Sampler instrument from audio samples.

    SAMPLES_DIR: Directory containing audio samples

    Layouts:
      - chromatic: Maps samples chromatically from C-2 upward
      - drum: 8 kicks, 8 snares, 8 hats, 8 perc (notes 0-31)
      - percussion: Maps samples chromatically from C1 (note 36)

    Examples:

      # Create chromatic sampler
      adc sampler create samples/ --layout chromatic

      # Create drum-style sampler
      adc sampler create samples/ --layout drum

      # Limit to 16 samples
      adc sampler create samples/ --max-samples 16
    """
    samples_dir = Path(samples_dir)
    template = Path(template)

    if not template.exists():
        click.secho(f"Error: Template not found: {template}", fg="red")
        click.echo("Please specify a valid template with --template")
        sys.exit(1)

    click.echo(f"Creating sampler from: {samples_dir}")
    click.echo(f"Layout: {layout}")
    click.echo(f"Max samples: {max_samples}")

    try:
        creator = SamplerCreator(template=template)
        result = creator.from_folder(
            samples_dir=samples_dir,
            output=output,
            layout=layout,
            samples_per_instrument=max_samples,
        )

        click.secho(f"✓ Created sampler: {result}", fg="green")
        click.echo(f"  File size: {result.stat().st_size / 1024:.1f} KB")

    except Exception as e:
        click.secho(f"Error: {e}", fg="red")
        sys.exit(1)


# ============================================================================
# SIMPLER COMMANDS
# ============================================================================


@main.group(name="simpler")
def simpler():
    """Create Simpler devices."""
    pass


@simpler.command(name="create")
@click.argument("samples_dir", type=click.Path(exists=True, file_okay=False))
@click.option(
    "-o",
    "--output-folder",
    type=click.Path(),
    help="Output folder for ADV files (default: output/<folder_name>_simplers)",
)
@click.option(
    "-t",
    "--template",
    type=click.Path(exists=True),
    default="templates/simpler-template.adv",
    help="Template ADV file to use",
)
@click.option(
    "--recursive/--no-recursive",
    default=False,
    help="Search subdirectories for samples",
)
def simpler_create(samples_dir, output_folder, template, recursive):
    """
    Create individual Simpler devices from audio samples.

    SAMPLES_DIR: Directory containing audio samples

    Creates one .adv file per sample. Each Simpler device spans the
    full keyboard range.

    Example:

      # Create Simpler for each sample
      adc simpler create samples/

      # Specify output folder
      adc simpler create samples/ -o my_simplers/
    """
    samples_dir = Path(samples_dir)
    template = Path(template)

    if not template.exists():
        click.secho(f"Error: Template not found: {template}", fg="red")
        click.echo("Please specify a valid template with --template")
        sys.exit(1)

    click.echo(f"Creating Simpler devices from: {samples_dir}")

    try:
        creator = SimplerCreator(template=template)
        created = creator.from_folder(
            samples_dir=samples_dir, output_folder=output_folder, recursive=recursive
        )

        click.secho(f"✓ Created {len(created)} Simpler devices", fg="green")
        if output_folder:
            click.echo(f"  Output: {output_folder}")
        else:
            click.echo(f"  Output: output/{samples_dir.name}_simplers/")

    except Exception as e:
        click.secho(f"Error: {e}", fg="red")
        sys.exit(1)


# ============================================================================
# UTILITY COMMANDS
# ============================================================================


@main.group(name="util")
def util():
    """Utility commands for ADG/ADV files."""
    pass


@util.command(name="decode")
@click.argument("file", type=click.Path(exists=True))
@click.option(
    "-o",
    "--output",
    type=click.Path(),
    help="Output XML file (default: <input>.xml)",
)
def util_decode(file, output):
    """
    Decode ADG/ADV file to XML.

    FILE: Path to .adg or .adv file

    Example:
      adc util decode MyRack.adg -o MyRack.xml
    """
    file_path = Path(file)

    if output is None:
        output = file_path.with_suffix(".xml")
    else:
        output = Path(output)

    click.echo(f"Decoding: {file_path}")

    try:
        xml_content = decode_adg(file_path)
        output.write_bytes(xml_content)

        click.secho(f"✓ Decoded to: {output}", fg="green")
        click.echo(f"  Size: {len(xml_content) / 1024:.1f} KB")

    except Exception as e:
        click.secho(f"Error: {e}", fg="red")
        sys.exit(1)


@util.command(name="encode")
@click.argument("file", type=click.Path(exists=True))
@click.option(
    "-o", "--output", type=click.Path(), help="Output ADG/ADV file (required)", required=True
)
def util_encode(file, output):
    """
    Encode XML file to ADG/ADV format.

    FILE: Path to XML file

    Example:
      adc util encode MyRack.xml -o MyRack.adg
    """
    file_path = Path(file)
    output = Path(output)

    click.echo(f"Encoding: {file_path}")

    try:
        xml_content = file_path.read_text(encoding="utf-8")
        encode_adg(xml_content, output)

        click.secho(f"✓ Encoded to: {output}", fg="green")
        click.echo(f"  Size: {output.stat().st_size / 1024:.1f} KB")

    except Exception as e:
        click.secho(f"Error: {e}", fg="red")
        sys.exit(1)


@util.command(name="info")
@click.argument("file", type=click.Path(exists=True))
def util_info(file):
    """
    Show information about ADG/ADV file.

    FILE: Path to .adg or .adv file

    Example:
      adc util info MyRack.adg
    """
    file_path = Path(file)

    click.echo(f"File: {file_path}")

    try:
        xml_content = decode_adg(file_path)

        # Basic stats
        click.echo(f"  Compressed size: {file_path.stat().st_size / 1024:.1f} KB")
        click.echo(f"  Uncompressed size: {len(xml_content) / 1024:.1f} KB")
        click.echo(f"  Compression ratio: {file_path.stat().st_size / len(xml_content):.1%}")

        # Detect device type
        xml_str = xml_content.decode("utf-8") if isinstance(xml_content, bytes) else xml_content
        if "DrumGroupDevice" in xml_str:
            click.echo(f"  Type: Drum Rack")
        elif "MultiSampler" in xml_str:
            click.echo(f"  Type: Multi-Sampler / Simpler")
        elif "InstrumentGroupDevice" in xml_str:
            click.echo(f"  Type: Instrument Rack")
        else:
            click.echo(f"  Type: Unknown")

        # Count samples. Drum racks and samplers write "<SampleRef Id=...>",
        # Simpler writes a bare "<SampleRef>" — match the open tag either way.
        sample_count = xml_str.count("<SampleRef")
        if sample_count > 0:
            click.echo(f"  Sample references: {sample_count}")

    except Exception as e:
        click.secho(f"Error: {e}", fg="red")
        sys.exit(1)


if __name__ == "__main__":
    main()
