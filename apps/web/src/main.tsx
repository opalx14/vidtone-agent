import React from 'react';
import ReactDOM from 'react-dom/client';
import { Download, FileVideo, Loader2, ShieldCheck, Sparkles, Wand2 } from 'lucide-react';
import './styles.css';

const DEFAULT_MODEL = 'accounts/fireworks/models/gpt-oss-120b';

const MODEL_PRESETS: ReadonlyArray<{ value: string; label: string }> = [
  { value: 'accounts/fireworks/models/gpt-oss-120b', label: 'gpt-oss-120b (verified)' },
  { value: 'accounts/fireworks/models/gpt-oss-20b', label: 'gpt-oss-20b' },
  { value: 'custom', label: 'Custom Fireworks slug…' },
];

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

function ScoreBadge({ label, value }: { label: string; value: number }) {
  const tone = value >= 8 ? 'good' : value >= 6 ? 'warn' : 'bad';
  return <span className={`score score-${tone}`}>{label}: {value}/10</span>;
}

function App() {
  const [file, setFile] = React.useState<File | null>(null);
  const [useMock, setUseMock] = React.useState(false);
  const [modelPreset, setModelPreset] = React.useState<string>(DEFAULT_MODEL);
  const [customModel, setCustomModel] = React.useState<string>('');
  const [isRunning, setIsRunning] = React.useState(false);
  const [result, setResult] = React.useState<CaptionResult | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const selectedModel = modelPreset === 'custom' ? customModel.trim() : modelPreset;

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
          <label htmlFor="model-preset">Model</label>
          <select
            id="model-preset"
            value={modelPreset}
            onChange={(event) => setModelPreset(event.target.value)}
            disabled={isRunning}
          >
            {MODEL_PRESETS.map((preset) => (
              <option key={preset.value} value={preset.value}>{preset.label}</option>
            ))}
          </select>
          {modelPreset === 'custom' && (
            <input
              type="text"
              placeholder="accounts/fireworks/models/..."
              value={customModel}
              onChange={(event) => setCustomModel(event.target.value)}
              disabled={isRunning}
              spellCheck={false}
              autoComplete="off"
            />
          )}
          <p className="hint">Model access depends on your Fireworks account.</p>
        </div>

        <div className="controls">
          <label className="toggle">
            <input type="checkbox" checked={useMock} onChange={(event) => setUseMock(event.target.checked)} disabled={isRunning} />
            Mock mode
          </label>
          <button className="primary" onClick={runCaption} disabled={!file || isRunning}>
            {isRunning ? <Loader2 className="spin" size={18} /> : <Wand2 size={18} />}
            {isRunning ? 'Running pipeline...' : 'Generate captions'}
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
