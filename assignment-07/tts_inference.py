"""Generate English speech with a pretrained Hugging Face VITS model.

Challenges handled in this assignment:
- The model is downloaded from Hugging Face on the first run, so internet access is
  required once and the files are then reused from the local Hugging Face cache.
- VITS inference is stochastic, so a fixed PyTorch seed is used for reproducibility.
- The model returns a batched floating-point tensor, which must be converted to a
  one-dimensional, mono, 16-bit PCM waveform before it is saved as a WAV file.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
from scipy.io import wavfile
from transformers import AutoTokenizer, VitsModel


MODEL_ID = "facebook/mms-tts-eng"
DEFAULT_TEXT = (
    "Hello! Welcome to Assignment Seven. This audio was generated with a "
    "Hugging Face text-to-speech model."
)
DEFAULT_OUTPUT = Path(__file__).resolve().with_name("output.wav")
RANDOM_SEED = 42


def parse_arguments() -> argparse.Namespace:
    """Parse optional text and output-path overrides from the command line."""
    parser = argparse.ArgumentParser(
        description="Generate English speech with facebook/mms-tts-eng."
    )
    parser.add_argument(
        "--text",
        default=DEFAULT_TEXT,
        help="English text to synthesize.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Destination WAV path (default: output.wav beside this script).",
    )
    arguments = parser.parse_args()

    if not arguments.text.strip():
        parser.error("--text must contain at least one non-whitespace character")

    return arguments


def synthesize_speech(text: str, output_path: Path) -> tuple[int, float]:
    """Synthesize *text*, save it to *output_path*, and return rate and duration."""
    # Step 1: Fix the random seed because VITS uses stochastic duration prediction.
    torch.manual_seed(RANDOM_SEED)

    # Step 2: Clone/download and load the pretrained model and matching tokenizer.
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = VitsModel.from_pretrained(MODEL_ID)
    model.eval()

    # Step 3: Convert the input sentence into model-ready PyTorch tensors.
    inputs = tokenizer(text, return_tensors="pt")

    # Step 4: Run inference without gradients because the model is not being trained.
    with torch.inference_mode():
        waveform_tensor = model(**inputs).waveform

    # Step 5: Remove the single-item batch dimension and validate the waveform.
    waveform = waveform_tensor.squeeze().detach().cpu().float().numpy()
    if waveform.ndim != 1 or waveform.size == 0:
        raise RuntimeError(f"Expected a non-empty mono waveform, got {waveform.shape}")
    if not np.isfinite(waveform).all():
        raise RuntimeError("The generated waveform contains non-finite samples")

    peak_amplitude = float(np.max(np.abs(waveform)))
    if peak_amplitude == 0.0:
        raise RuntimeError("The generated waveform is silent")

    # Step 6: Normalize with headroom, convert to 16-bit PCM, and save as WAV.
    normalized_waveform = np.clip(waveform / peak_amplitude, -1.0, 1.0)
    pcm16_waveform = np.round(
        normalized_waveform * 0.95 * np.iinfo(np.int16).max
    ).astype(np.int16)

    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = int(model.config.sampling_rate)
    wavfile.write(output_path, sample_rate, pcm16_waveform)

    # Step 7: Calculate the duration so the successful result can be inspected.
    duration_seconds = pcm16_waveform.size / sample_rate
    return sample_rate, duration_seconds


def main() -> None:
    """Run text-to-speech inference and print a concise result summary."""
    arguments = parse_arguments()
    output_path = arguments.output.expanduser().resolve()
    sample_rate, duration_seconds = synthesize_speech(arguments.text, output_path)

    print(f"Model: {MODEL_ID}")
    print(f"Text: {arguments.text}")
    print(f"Output: {output_path}")
    print(f"Sample rate: {sample_rate} Hz")
    print(f"Duration: {duration_seconds:.2f} seconds")


if __name__ == "__main__":
    main()
