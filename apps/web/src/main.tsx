import React from 'react';
import ReactDOM from 'react-dom/client';
import { Download, FileVideo, Loader2, RefreshCcw, ShieldCheck, Sparkles, Wand2 } from 'lucide-react';
import './styles.css';

const DEFAULT_MODEL = 'accounts/fireworks/models/gpt-oss-120b';
const CUSTOM_MODEL = 'custom';

const FALLBACK_MODELS: ReadonlyArray<ModelOption> = [
  { value: 'accounts/fireworks/models/gpt-oss-120b', label: 'gpt-oss-120b (verified)', source: 'fallback' },
  { value: 'accounts/fireworks/models/gpt-oss-20b', label: 'gpt-oss-20b', source: 'fallback' },
];

type ModelOption = {
  value: string;
  label: string;
  source?: string;
  contextLength?: number | null;
};

type ApiModel = {
  id?: string;
  name?: string;
  display_name?: string;
  displayName?: string;
  context_length?: number | null;
  contextLength?: number | null;
  source?: string;
};

type ModelsResponse = {
  models: ApiModel[];
  source?: string;
  default_model?: string;
};

type CaptionItem = {
  text: string;
  source: string;
  accuracy_score: number;
  tone_score: number;
  hallucination_risk: number;
  notes: string;
  judge_source: string;
};

type CaptionResult = {
  project: string;
  mode: string;
  model?: string;
  vision_model?: string | null;
  request_id?: string;
  video: {
    filename: string;
    duration_seconds: number | null;
    fps: number | null;
    width: number | null;
    height: number | null;
  };
  warnings: string[];
  captions: Record<string, CaptionItem>;
  exports?: {
    json?: string;
    csv?: string;
  };
};

const styleLabels: Record<string, string> = {
  formal: 'Formal',
  sarcastic: 'Sarcastic',
  humorous_tech: 'Humorous Tech',
  humorous_non_tech: 'Humorous Non-Tech',
};

function shortModelName(model: string) {
  return model.split('/').filter(Boolean).pop() ?? model;
}

function formatModelSource(source: string): string {
  if (!source) return 'Fireworks catalog';
  if (source.startsWith('fallback:no_api_key')) return 'fallback presets · no API key';
  if (source.startsWith('fallback:')) return 'fallback presets · catalog unreachable';
  if (source === 'fallback') return 'fallback presets';
  if (source.startsWith('account:')) return 'Fireworks catalog';
  if (source.includes('inference/v1/models')) return 'Fireworks serverless catalog';
  if (source.includes('/accounts/')) return 'Fireworks account catalog';
  return source;
}

function normalizeApiModel(model: ApiModel): ModelOption | null {
  const rawValue = model.name ?? model.id;
  if (!rawValue) return null;

  const value = rawValue.startsWith('accounts/')
    ? rawValue
    : rawValue.startsWith('models/')
      ? `accounts/fireworks/${rawValue}`
      : rawValue.includes('/models/')
        ? rawValue
        : `accounts/fireworks/models/${rawValue}`;

  const rawLabel = model.display_name ?? model.displayName ?? shortModelName(value);
  const contextLength = model.context_length ?? model.contextLength ?? null;
  const label = contextLength
    ? `${rawLabel} · ${Math.round(contextLength / 1000)}k ctx`
    : rawLabel;

  return {
    value,
    label,
    source: model.source,
    contextLength,
  };
}

function mergeModelOptions(models: ModelOption[]) {
  const seen = new Set<string>();
  const merged: ModelOption[] = [];
  for (const model of models) {
    if (!model.value || seen.has(model.value)) continue;
    seen.add(model.value);
    merged.push(model);
  }
  return merged;
}

function ScoreBadge({ label, value }: { label: string; value: number }) {
  const tone = value >= 8 ? 'good' : value >= 6 ? 'warn' : 'bad';
  return <span className={`score score-${tone}`}>{label}: {value}/10</span>;
}

function App() {
  const [file, setFile] = React.useState<File | null>(null);
  const [useMock, setUseMock] = React.useState(false);
  const [modelPreset, setModelPreset] = React.useState<string>(DEFAULT_MODEL);
  const [customModel, setCustomModel] = React.useState<string>('');
  const [modelOptions, setModelOptions] = React.useState<ModelOption[]>([...FALLBACK_MODELS]);
  const [modelSource, setModelSource] = React.useState<string>('fallback');
  const [isLoadingModels, setIsLoadingModels] = React.useState(false);
  const [modelLoadError, setModelLoadError] = React.useState<string | null>(null);
  const [isRunning, setIsRunning] = React.useState(false);
  const [result, setResult] = React.useState<CaptionResult | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const selectedModel = modelPreset === CUSTOM_MODEL ? customModel.trim() : modelPreset;

  async function loadModels() {
    setIsLoadingModels(true);
    setModelLoadError(null);
    try {
      const response = await fetch('/api/models');
      if (!response.ok) {
        throw new Error(`Model API failed with ${response.status}`);
      }
      const payload = (await response.json()) as ModelsResponse;
      const loadedModels = (payload.models ?? [])
        .map(normalizeApiModel)
        .filter((model): model is ModelOption => model !== null);
      const mergedModels = mergeModelOptions([...loadedModels, ...FALLBACK_MODELS]);
      setModelOptions(mergedModels.length > 0 ? mergedModels : [...FALLBACK_MODELS]);
      setModelSource(payload.source ?? 'api');

      const defaultModel = payload.default_model || DEFAULT_MODEL;
      if (defaultModel && modelPreset === DEFAULT_MODEL && mergedModels.some((item) => item.value === defaultModel)) {
        setModelPreset(defaultModel);
      }
    } catch (err) {
      setModelOptions([...FALLBACK_MODELS]);
      setModelSource('fallback');
      setModelLoadError(err instanceof Error ? err.message : 'Could not load Fireworks models');
    } finally {
      setIsLoadingModels(false);
    }
  }

  React.useEffect(() => {
    void loadModels();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function runCaption() {
    if (!file) {
      setError('Choose a video first.');
      return;
    }

    const formData = new FormData();
    formData.append('video', file);
    formData.append('use_mock', String(useMock));
    if (selectedModel) {
      formData.append('model', selectedModel);
    }

    setIsRunning(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch('/api/caption', {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail ?? `API failed with ${response.status}`);
      }
      setResult((await response.json()) as CaptionResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <main className="shell">
      <section className="hero">
        <div className="eyebrow"><Sparkles size={16} /> AI caption QA copilot</div>
        <h1>Turn one short video into platform-ready captions.</h1>
        <p>Upload a clip, generate four caption tones, then let the Judge Agent score accuracy, tone match, and hallucination risk.</p>
      </section>

      <section className="panel upload-panel">
        <div className="upload-copy">
          <FileVideo size={28} />
          <div>
            <h2>Video input</h2>
            <p>Use the generated sample video or upload your own MP4/MOV clip.</p>
          </div>
        </div>

        <label className="dropzone">
          <input type="file" accept="video/mp4,video/quicktime,video/webm,video/x-matroska,video/x-msvideo" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
          <span>{file ? file.name : 'Click to choose a video'}</span>
        </label>

        {file && <video className="preview" src={URL.createObjectURL(file)} controls />}

        <div className="model-selector">
          <div className="model-selector-header">
            <label htmlFor="model-preset" className="model-selector-label">Model</label>
            <button
              className="link-button"
              type="button"
              onClick={() => void loadModels()}
              disabled={isRunning || isLoadingModels}
              aria-label="Reload Fireworks model list"
            >
              {isLoadingModels ? <Loader2 className="spin" size={13} /> : <RefreshCcw size={13} />}
              <span>{isLoadingModels ? 'Loading' : 'Reload'}</span>
            </button>
          </div>

          <div className="select-wrap">
            <select
              id="model-preset"
              value={modelPreset}
              onChange={(event) => setModelPreset(event.target.value)}
              disabled={isRunning || isLoadingModels}
            >
              {modelOptions.map((model) => (
                <option key={model.value} value={model.value}>{model.label}</option>
              ))}
              <option value={CUSTOM_MODEL}>Custom Fireworks slug…</option>
            </select>
          </div>

          {modelPreset === CUSTOM_MODEL && (
            <input
              className="model-custom-input"
              type="text"
              placeholder="accounts/fireworks/models/…"
              value={customModel}
              onChange={(event) => setCustomModel(event.target.value)}
              disabled={isRunning}
              spellCheck={false}
              autoComplete="off"
            />
          )}

          <div className={`model-selector-status ${modelLoadError ? 'is-error' : 'is-ok'}`}>
            <span className="model-status-dot" aria-hidden="true" />
            {modelLoadError ? (
              <span className="model-status-text">
                Fallback presets active · {modelLoadError}
              </span>
            ) : (
              <>
                <span className="model-status-text">
                  {modelOptions.length} model{modelOptions.length === 1 ? '' : 's'} · {formatModelSource(modelSource)}
                </span>
                <span className="model-status-sep" aria-hidden="true">·</span>
                <span className="model-status-hint">Access depends on your Fireworks account</span>
              </>
            )}
          </div>
        </div>

        <div className="controls">
          <label className="toggle">
            <input type="checkbox" checked={useMock} onChange={(event) => setUseMock(event.target.checked)} disabled={isRunning} />
            <span>Mock mode</span>
          </label>
          <button className="primary" onClick={runCaption} disabled={!file || isRunning}>
            {isRunning ? <Loader2 className="spin" size={18} /> : <Wand2 size={18} />}
            <span>{isRunning ? 'Running pipeline…' : 'Generate captions'}</span>
          </button>
        </div>
      </section>

      {error && <section className="error">{error}</section>}

      {result && (
        <section className="results">
          <div className="result-header">
            <div>
              <div className="eyebrow"><ShieldCheck size={16} /> Judge Agent result</div>
              <h2>{result.video.filename}</h2>
              <p>Duration: {result.video.duration_seconds ?? 'unknown'}s · Mode: {result.mode}{result.model ? ` · Model: ${result.model}` : ''}</p>
            </div>
            <div className="export-actions">
              {result.exports?.json && <a href={`/api/export?path=${encodeURIComponent(result.exports.json)}`}><Download size={16} /> JSON</a>}
              {result.exports?.csv && <a href={`/api/export?path=${encodeURIComponent(result.exports.csv)}`}><Download size={16} /> CSV</a>}
            </div>
          </div>

          {result.warnings.length > 0 && <div className="warning-box">{result.warnings.map((warning) => <p key={warning}>{warning}</p>)}</div>}

          <div className="caption-grid">
            {Object.entries(result.captions).map(([style, item]) => (
              <article className="caption-card" key={style}>
                <h3>{styleLabels[style] ?? style}</h3>
                <p className="caption-text">{item.text}</p>
                <div className="scores">
                  <ScoreBadge label="Accuracy" value={item.accuracy_score} />
                  <ScoreBadge label="Tone" value={item.tone_score} />
                  <ScoreBadge label="Risk" value={item.hallucination_risk} />
                </div>
                <p className="notes">{item.notes}</p>
              </article>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
