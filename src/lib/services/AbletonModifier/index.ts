import { XMLParser, XMLBuilder } from 'fast-xml-parser';
import type { AbletonParserError } from '../AbletonParser/types';

export class AbletonModifierService {
  private parser: XMLParser;
  private builder: XMLBuilder;

  constructor() {
    this.parser = new XMLParser({
      ignoreAttributes: false,
      attributeNamePrefix: '',
      parseAttributeValue: true,
      preserveOrder: true
    });

    this.builder = new XMLBuilder({
      ignoreAttributes: false,
      attributeNamePrefix: '',
      format: true
    });
  }

  public removeUnwantedTracks(xmlContent: string): string | AbletonParserError {
    try {
      const parsed = this.parser.parse(xmlContent);
      
      if (!parsed.find((item: any) => item.Ableton)) {
        return {
          code: 'INVALID_XML',
          message: 'Invalid Ableton file structure'
        };
      }

      const abletonNode = parsed.find((item: any) => item.Ableton);
      const liveSet = abletonNode.Ableton.find((item: any) => item.LiveSet);
      const tracks = liveSet.LiveSet.find((item: any) => item.Tracks);

      if (!tracks || !tracks.Tracks) {
        return {
          code: 'NO_TRACKS',
          message: 'No tracks found in the Ableton set'
        };
      }

      // Filter out MIDI tracks and tracks without arrangement clips
      const filteredTracks = tracks.Tracks.filter((track: any) => {
        // Keep if it's not a MIDI track
        if (track.MidiTrack) return false;

        // If it's an audio track, check for arrangement clips
        if (track.AudioTrack) {
          const hasArrangementClips = track.AudioTrack.ArrangementClips && 
            Object.keys(track.AudioTrack.ArrangementClips).length > 0;
          return hasArrangementClips;
        }

        // Keep all other track types (Return, Master, Group)
        return true;
      });

      tracks.Tracks = filteredTracks;

      // Rebuild the XML
      return '<?xml version="1.0" encoding="UTF-8"?>\n' + this.builder.build(parsed);
    } catch (error) {
      return {
        code: 'PARSE_ERROR',
        message: 'Failed to modify Ableton set',
        details: error
      };
    }
  }
} 