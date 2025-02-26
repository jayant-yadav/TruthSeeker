export interface TranscriptionResult {
    text: string;
    timestamp: string;
    audio_duration: number;
    method: string;
}

export interface StreamingResult {
    text: string;
    is_final: boolean;
}

export interface TranscriptionConfig {
    model_checkpoint: string;
    method: string;
    save_transcript: boolean;
    chunk_size_ms: number;
    overlap_ms: number;
}

export const LOCAL_MODEL_CHECKPOINTS = ['medium.en', 'large-v3', 'large-v2', 'large-v3-turbo', 'large-v3-turbo-q5_0'] as const;
export const OPENAI_MODEL_CHECKPOINTS = ['whisper-1'] as const;
export const TRANSCRIPTION_METHODS = ['local_whisper', 'openai_whisper'] as const;