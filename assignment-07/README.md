# Assignment 07 - Hugging Face Text-to-Speech Inference

This project downloads a pretrained text-to-speech (TTS) model from the Hugging
Face Hub and uses it to convert English text into a playable WAV audio file.

## Objectives

- Load a public pretrained TTS model from Hugging Face.
- Tokenize an English sentence and perform inference with PyTorch.
- Convert the generated waveform into a standard audio file.
- Provide a reproducible command-line workflow and preview result.

## Model

The project uses
[`facebook/mms-tts-eng`](https://huggingface.co/facebook/mms-tts-eng), an English
VITS checkpoint from Meta's Massively Multilingual Speech project. The model is
downloaded automatically on the first run and then reused from the local Hugging
Face cache. Its model card lists the license as CC BY-NC 4.0.

## Project files

| File | Description |
| --- | --- |
| `tts_inference.py` | Complete, commented model loading and inference code |
| `requirements.txt` | Python dependencies required to run the assignment |
| `output.wav` | Generated preview audio using the default sentence |
| `README.md` | Setup, usage, implementation notes, and results |

[Download or play the generated preview audio](output.wav).

## Requirements

- Python 3.10 or later
- Internet access for the first run so the model can be downloaded
- At least 1.5 GB of free space for Python packages and the model cache

## Installation

Create and activate a virtual environment from the project directory.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Usage

Run inference with the assignment's default sentence:

```bash
python tts_inference.py
```

The default command saves `output.wav` beside the Python script. It speaks:

> Hello! Welcome to Assignment Seven. This audio was generated with a Hugging
> Face text-to-speech model.

Provide different English text with `--text`:

```bash
python tts_inference.py --text "Artificial intelligence can generate speech from text."
```

Choose a different output location with `--output`:

```bash
python tts_inference.py --text "This is another example." --output samples/example.wav
```

After successful inference, the script prints the selected model, input text,
absolute output path, sample rate, and generated audio duration.

## Implementation flow

1. Set a fixed PyTorch seed for reproducible VITS output.
2. Download and load `facebook/mms-tts-eng` with `AutoTokenizer` and `VitsModel`.
3. Tokenize the input English text into PyTorch tensors.
4. Generate a waveform using inference mode, without calculating gradients.
5. Remove the batch dimension and validate that every sample is finite.
6. Normalize the waveform with headroom and encode it as mono 16-bit PCM.
7. Save the audio using the sampling rate provided by the model configuration.

## Challenges and solutions

- **First-run download:** the model is approximately 145 MB and requires an
  internet connection once; later runs use Hugging Face's cache.
- **Non-deterministic inference:** VITS uses stochastic duration prediction, so
  the script fixes the random seed to `42`.
- **Tensor shape:** the model returns a batched tensor; the script converts it
  into the one-dimensional waveform expected by a mono WAV file.
- **Audio compatibility:** floating-point predictions are normalized and
  encoded as 16-bit PCM so the preview works in common audio players.

## Expected result

The included default `output.wav` is a non-empty, mono, 16-bit PCM file sampled
at 16,000 Hz. Its verified duration is 6.46 seconds (103,424 audio frames). The
script also prints these result details after each generation.

## Submission checklist

- [x] A single `.py` file contains the complete inference workflow.
- [x] The code includes comments explaining each step and challenges handled.
- [x] A generated preview audio file is included beside the script.
- [x] The README explains installation, execution, model choice, and results.
- [x] The optional Hugging Face Spaces deployment is intentionally out of scope.
