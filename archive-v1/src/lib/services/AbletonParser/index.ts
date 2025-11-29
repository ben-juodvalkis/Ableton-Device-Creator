import { XMLParser } from 'fast-xml-parser';
import type { AbletonSetAnalysis, AbletonTrack, AbletonParserError } from './types';

export class AbletonParserService {
  private parser: XMLParser;

  constructor() {
    this.parser = new XMLParser({
      ignoreAttributes: false,
      attributeNamePrefix: '',
      parseAttributeValue: true
    });
  }

  public analyzeSet(xmlContent: string): AbletonSetAnalysis | AbletonParserError {
    try {
      const parsed = this.parser.parse(xmlContent);
      
      if (!parsed.Ableton?.LiveSet?.Tracks) {
        return {
          code: 'NO_TRACKS',
          message: 'No tracks found in the Ableton set'
        };
      }

      const tracks = this.extractTracks(parsed.Ableton.LiveSet.Tracks);
      const tracksWithClips: AbletonTrack[] = [];
      const tracksWithoutClips: AbletonTrack[] = [];

      tracks.forEach(track => {
        if (track.hasClips) {
          tracksWithClips.push(track);
        } else {
          tracksWithoutClips.push(track);
        }
      });

      return {
        totalTracks: tracks.length,
        tracksWithClips,
        tracksWithoutClips
      };
    } catch (error) {
      return {
        code: 'PARSE_ERROR',
        message: 'Failed to parse Ableton set',
        details: error
      };
    }
  }

  private extractTracks(tracksData: any): AbletonTrack[] {
    const tracks: AbletonTrack[] = [];
    
    // Handle both single track and multiple tracks cases
    const tracksList = Array.isArray(tracksData) ? tracksData : [tracksData];

    for (const trackContainer of tracksList) {
      // Check for different track types
      for (const trackType of ['AudioTrack', 'MidiTrack', 'ReturnTrack', 'MasterTrack', 'GroupTrack']) {
        const track = trackContainer[trackType];
        if (track) {
          const hasClips = this.checkForClips(track);
          tracks.push({
            id: track.Id?.toString() || '',
            name: this.extractTrackName(track),
            type: this.getTrackType(trackType),
            hasClips
          });
        }
      }
    }

    return tracks;
  }

  private checkForClips(track: any): boolean {
    // Check Arrangement View clips
    if (track.ArrangementClips && Object.keys(track.ArrangementClips).length > 0) {
      return true;
    }
    
    // Check Session View clips
    if (track.DeviceChain?.MainSequencer?.ClipSlotList?.ClipSlot) {
      const clipSlots = Array.isArray(track.DeviceChain.MainSequencer.ClipSlotList.ClipSlot) 
        ? track.DeviceChain.MainSequencer.ClipSlotList.ClipSlot
        : [track.DeviceChain.MainSequencer.ClipSlotList.ClipSlot];
      
      return clipSlots.some(slot => slot.ClipSlot && Object.keys(slot.ClipSlot).length > 0);
    }

    return false;
  }

  private extractTrackName(track: any): string {
    return track.Name?.EffectiveName?.Value || track.Name?.UserName?.Value || 'Unnamed Track';
  }

  private getTrackType(trackType: string): AbletonTrack['type'] {
    const typeMap: Record<string, AbletonTrack['type']> = {
      'AudioTrack': 'audio',
      'MidiTrack': 'midi',
      'ReturnTrack': 'return',
      'MasterTrack': 'master',
      'GroupTrack': 'group'
    };
    return typeMap[trackType] || 'audio';
  }
} 