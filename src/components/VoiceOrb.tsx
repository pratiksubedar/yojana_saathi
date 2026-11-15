import React from 'react';
import { Mic, Square, Play, RotateCcw, Volume2, AlertCircle } from 'lucide-react';
import { Language } from '../types';
import { t } from '../data/translations';

export type VoiceOrbState = 'idle' | 'listening' | 'processing' | 'speaking' | 'paused' | 'error';

interface VoiceOrbProps {
  state: VoiceOrbState;
  onClick: () => void;
  transcript?: string;
  interimTranscript?: string;
  errorMessage?: string | null;
  language: Language;
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  onStopSpeaking?: () => void;
  onReplay?: () => void;
  className?: string;
}

export const VoiceOrb: React.FC<VoiceOrbProps> = ({
  state,
  onClick,
  transcript = '',
  interimTranscript = '',
  errorMessage,
  language,
  size = 'lg',
  disabled = false,
  onStopSpeaking,
  onReplay,
  className = '',
}) => {
  const sizeClasses = {
    sm: 'w-20 h-20 text-sm',
    md: 'w-32 h-32 text-base',
    lg: 'w-40 h-40 sm:w-48 sm:h-48 text-lg',
  }[size];

  const getStatusText = () => {
    switch (state) {
      case 'listening':
        return t('listeningLabel', language) || 'Listening... Speak now';
      case 'processing':
        return t('processingLabel', language) || 'Thinking & verifying...';
      case 'speaking':
        return t('speakingLabel', language) || 'Assistant is speaking';
      case 'paused':
        return 'Paused';
      case 'error':
        return errorMessage || 'Tap to try again';
      case 'idle':
      default:
        return t('speakToFind', language) || 'Tap to Speak';
    }
  };

  return (
    <div className={`flex flex-col items-center justify-center select-none ${className}`}>
      {/* Outer Ripple / Breathing Container */}
      <div className="relative flex items-center justify-center p-4">
        {/* Animated Background Rings for Speaking / Listening */}
        {state === 'speaking' && (
          <div className="absolute inset-0 rounded-full bg-forest/15 animate-orb-ripple pointer-events-none" />
        )}
        {state === 'listening' && (
          <>
            <div className="absolute -inset-2 rounded-full bg-forest/20 animate-ping opacity-30 pointer-events-none" />
            <div className="absolute -inset-5 rounded-full border-2 border-forest/30 animate-pulse pointer-events-none" />
          </>
        )}
        {state === 'processing' && (
          <div className="absolute -inset-2 rounded-full border-2 border-forest/30 border-t-forest animate-orb-spin pointer-events-none" />
        )}

        {/* Central Interactive Orb Button */}
        <button
          type="button"
          onClick={onClick}
          disabled={disabled}
          aria-label={getStatusText()}
          className={`
            ${sizeClasses}
            rounded-full flex flex-col items-center justify-center relative
            transition-all duration-300 focus:outline-none focus-visible:ring-4 focus-visible:ring-forest/40
            ${disabled ? 'opacity-50 cursor-not-allowed' : 'active:scale-95 cursor-pointer'}
            ${
              state === 'idle'
                ? 'bg-gradient-to-br from-forest to-forest-deep text-surface shadow-orb hover:shadow-orb-active animate-orb-breathe'
                : ''
            }
            ${
              state === 'listening'
                ? 'bg-gradient-to-br from-forest to-forest-deep text-surface ring-8 ring-forest/20 shadow-orb-active'
                : ''
            }
            ${
              state === 'processing'
                ? 'bg-surface text-forest border-2 border-forest/40 shadow-orb'
                : ''
            }
            ${
              state === 'speaking'
                ? 'bg-gradient-to-br from-forest to-forest-deep text-surface shadow-orb-active ring-4 ring-forest/30'
                : ''
            }
            ${
              state === 'paused'
                ? 'bg-surface text-maybe border-2 border-maybe shadow-card'
                : ''
            }
            ${
              state === 'error'
                ? 'bg-ineligible-bg text-ineligible border-2 border-ineligible shadow-card'
                : ''
            }
          `}
        >
          {/* Visual Elements by State */}
          {state === 'idle' && (
            <div className="flex flex-col items-center justify-center">
              <Mic className={size === 'sm' ? 'w-7 h-7 text-surface' : 'w-10 h-10 sm:w-12 sm:h-12 text-surface'} />
              {size !== 'sm' && (
                <span className="text-xs sm:text-sm font-semibold tracking-wide text-surface/90 mt-1">
                  {t('speakToFind', language)}
                </span>
              )}
            </div>
          )}

          {state === 'listening' && (
            <div className="flex flex-col items-center justify-center gap-2">
              {/* 5-Bar Waveform */}
              <div className="flex items-center gap-1.5 h-10 px-2">
                <span className="w-1.5 bg-surface rounded-full h-4 animate-wave-bar-1" />
                <span className="w-1.5 bg-surface rounded-full h-8 animate-wave-bar-2" />
                <span className="w-1.5 bg-surface rounded-full h-10 animate-wave-bar-3" />
                <span className="w-1.5 bg-surface rounded-full h-7 animate-wave-bar-4" />
                <span className="w-1.5 bg-surface rounded-full h-5 animate-wave-bar-5" />
              </div>
              <span className="text-[11px] sm:text-xs font-bold text-surface/90 uppercase tracking-wider">
                {t('listeningLabel', language)}
              </span>
            </div>
          )}

          {state === 'processing' && (
            <div className="flex flex-col items-center justify-center gap-2.5">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 bg-forest rounded-full animate-bounce [animation-delay:-0.3s]" />
                <span className="w-2.5 h-2.5 bg-forest rounded-full animate-bounce [animation-delay:-0.15s]" />
                <span className="w-2.5 h-2.5 bg-forest rounded-full animate-bounce" />
              </div>
              <span className="text-[11px] sm:text-xs font-bold text-forest">
                {t('processingLabel', language)}
              </span>
            </div>
          )}

          {state === 'speaking' && (
            <div className="flex flex-col items-center justify-center gap-2">
              <Volume2 className="w-10 h-10 text-surface animate-pulse" />
              <span className="text-[11px] sm:text-xs font-bold text-surface uppercase tracking-wider">
                {t('speakingLabel', language)}
              </span>
            </div>
          )}

          {state === 'paused' && (
            <div className="flex flex-col items-center justify-center gap-2">
              <Play className="w-10 h-10 text-maybe ml-1" />
              <span className="text-xs font-bold text-maybe">Resume</span>
            </div>
          )}

          {state === 'error' && (
            <div className="flex flex-col items-center justify-center gap-1.5 p-2 text-center">
              <AlertCircle className="w-8 h-8 text-ineligible" />
              <span className="text-[11px] font-bold text-ineligible">
                Retry
              </span>
            </div>
          )}
        </button>
      </div>

      {/* Live Spoken Transcript Stream (Voice-First Requirement) */}
      {(transcript || interimTranscript) && (
        <div className="max-w-md w-full mx-auto px-4 mt-3 text-center">
          <div className="inline-block p-3 rounded-2xl bg-surface border border-sand shadow-sm max-w-full">
            <p className="text-sm text-ink font-medium leading-relaxed break-words">
              {transcript}
              {interimTranscript && (
                <span className="text-ink-light italic ml-1 opacity-80">{interimTranscript}</span>
              )}
            </p>
          </div>
        </div>
      )}

      {/* Speaking Active Controls: Stop / Replay */}
      {state === 'speaking' && (
        <div className="flex items-center gap-3 mt-4">
          {onStopSpeaking && (
            <button
              type="button"
              onClick={onStopSpeaking}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-surface border border-sand hover:bg-sand/40 text-ink text-xs font-semibold shadow-sm transition-colors"
            >
              <Square className="w-3.5 h-3.5 text-ineligible" />
              <span>{t('stopAudio', language)}</span>
            </button>
          )}
          {onReplay && (
            <button
              type="button"
              onClick={onReplay}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-surface border border-sand hover:bg-sand/40 text-ink text-xs font-semibold shadow-sm transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5 text-forest" />
              <span>{t('replayResponse', language)}</span>
            </button>
          )}
        </div>
      )}

      {/* Status Caption */}
      {state !== 'speaking' && !transcript && !interimTranscript && (
        <p className="text-xs sm:text-sm font-medium text-ink-muted mt-2 text-center">
          {getStatusText()}
        </p>
      )}
    </div>
  );
};

