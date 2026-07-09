from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.core.config import AppConfig
from src.core.pipeline import VidTonePipeline


st.set_page_config(
    page_title="VidTone Agent",
    page_icon="🎬",
    layout="wide",
)


@st.cache_resource(show_spinner=False)
def load_config() -> AppConfig:
    config = AppConfig.from_env()
    config.ensure_dirs()
    return config


def save_upload(uploaded_file: Any, upload_dir: Path) -> Path:
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(uploaded_file.name).name
    output_path = upload_dir / safe_name
    output_path.write_bytes(uploaded_file.getbuffer())
    return output_path


def captions_to_table(result: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for style, item in result.get("captions", {}).items():
        rows.append(
            {
                "style": style,
                "caption": item.get("text", ""),
                "accuracy": item.get("accuracy_score", ""),
                "tone": item.get("tone_score", ""),
                "hallucination_risk": item.get("hallucination_risk", ""),
                "source": item.get("source", ""),
                "judge": item.get("judge_source", ""),
                "notes": item.get("notes", ""),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    config = load_config()

    st.title("🎬 VidTone Agent")
    st.caption("Multi-style video captioning with self-judging AI for AMD Developer Hackathon ACT II.")

    mode_label = "MOCK MODE" if not config.can_call_fireworks else "FIREWORKS MODE"
    st.info(
        f"Current mode: **{mode_label}**. "
        "Set `USE_MOCK=false`, `FIREWORKS_API_KEY`, and `FIREWORKS_MODEL` to call the real model."
    )

    with st.sidebar:
        st.header("Pipeline")
        st.write("1. Upload short video")
        st.write("2. Extract metadata/keyframes")
        st.write("3. Generate 4 caption styles")
        st.write("4. Judge accuracy + tone")
        st.write("5. Export JSON/CSV")
        st.divider()
        st.write("Target styles")
        st.code("formal\nsarcastic\nhumorous-tech\nhumorous-non-tech")

    uploaded_file = st.file_uploader(
        "Upload a short video",
        type=["mp4", "mov", "avi", "mkv", "webm"],
    )

    if uploaded_file is None:
        st.warning("Upload a video to start. Mock mode works without any API key.")
        return

    video_path = save_upload(uploaded_file, config.upload_dir)

    left, right = st.columns([1, 1])
    with left:
        st.subheader("Video preview")
        st.video(str(video_path))
    with right:
        st.subheader("Run")
        st.write(f"Saved to `{video_path}`")
        run_button = st.button("Generate captions", type="primary", use_container_width=True)

    if not run_button:
        return

    with st.spinner("Running VidTone pipeline..."):
        pipeline = VidTonePipeline(config)
        result = pipeline.run(video_path)

    st.success("Captions generated.")

    video = result.get("video", {})
    metric_cols = st.columns(4)
    metric_cols[0].metric("Duration", f"{video.get('duration_seconds') or 'unknown'}s")
    metric_cols[1].metric("FPS", video.get("fps") or "unknown")
    metric_cols[2].metric("Resolution", f"{video.get('width') or '?'}x{video.get('height') or '?'}")
    metric_cols[3].metric("Keyframes", len(result.get("keyframes", [])))

    warnings = result.get("warnings", [])
    if warnings:
        with st.expander("Warnings", expanded=True):
            for warning in warnings:
                st.warning(warning)

    st.subheader("Caption results")
    table = captions_to_table(result)
    st.dataframe(table, use_container_width=True, hide_index=True)

    st.subheader("Exports")
    json_text = json.dumps(result, indent=2, ensure_ascii=False)
    st.download_button(
        "Download JSON",
        data=json_text,
        file_name=f"{video_path.stem}_vidtone.json",
        mime="application/json",
    )
    st.download_button(
        "Download CSV",
        data=table.to_csv(index=False),
        file_name=f"{video_path.stem}_vidtone.csv",
        mime="text/csv",
    )

    with st.expander("Video context sent to caption agents"):
        st.code(result.get("video_context", ""))


if __name__ == "__main__":
    main()
