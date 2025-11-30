import { writable } from 'svelte/store';
import type { AbletonSetAnalysis } from './types';

interface State {
  analysis: AbletonSetAnalysis | null;
  loading: boolean;
  error: string | null;
}

const initial: State = {
  analysis: null,
  loading: false,
  error: null
};

function createAbletonAnalysisStore() {
  const { subscribe, set, update } = writable(initial);

  return {
    subscribe,
    reset: () => set(initial),
    setAnalysis: (analysis: AbletonSetAnalysis) => 
      update(s => ({ ...s, analysis, error: null })),
    setLoading: (loading: boolean) => 
      update(s => ({ ...s, loading })),
    setError: (error: string) => 
      update(s => ({ ...s, error, analysis: null }))
  };
}

export const abletonAnalysisStore = createAbletonAnalysisStore(); 