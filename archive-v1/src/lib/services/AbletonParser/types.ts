export interface AbletonTrack {
  id: string;
  name: string;
  type: 'audio' | 'midi' | 'return' | 'master' | 'group';
  hasArrangementClips: boolean;
  shouldRemove: boolean;
}

export interface AbletonSetAnalysis {
  totalTracks: number;
  tracksToKeep: AbletonTrack[];
  tracksToRemove: AbletonTrack[];
}

export interface AbletonParserError {
  code: 'INVALID_XML' | 'NO_TRACKS' | 'PARSE_ERROR';
  message: string;
  details?: unknown;
}

export interface TrackRemovalCriteria {
  removeEmptyArrangementTracks: boolean;
  removeMidiTracks: boolean;
} 