# Assignment 12 - Satellite Image Cloud Detection

This project automatically classifies three satellite and Earth-observation images as **Cloudy** or **Clear** with GPT-4o-mini. It uses a multimodal prompt through LangChain's `ChatOpenAI`, prints every prediction to the console, and does not require manual input.

The solution follows the assignment's inference-based approach while replacing `AzureChatOpenAI` with `ChatOpenAI` and the provided OpenAI-compatible gateway.

## Architecture

```text
Three fixed NASA image URLs
            |
            v
Multimodal message (text + image URL)
            |
            v
ChatOpenAI + GPT-4o-mini
            |
            v
Structured CloudDetectionResult
            |
            v
Prediction and confidence in the console
```

Each image is sent directly as an `image_url` content block. The model returns a Pydantic-validated result containing one of the two allowed labels and a confidence value from 0 to 100.

## Project files

- `assignment_12.py` - the complete application and the only Python source file.
- `requirements.txt` - required Python packages.
- `.env.example` - safe configuration template with placeholder credentials.
- `.gitignore` - prevents secrets and generated Python files from being committed.

## Requirements

- Python 3.10 or newer.
- An OpenAI-compatible API key with access to `GPT-4o-mini`.
- Internet access for the API gateway and the three NASA image URLs.

## Setup

### Windows PowerShell

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Create the local environment file:

```powershell
Copy-Item .env.example .env
```

### macOS or Linux

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies and create the environment file:

```bash
python -m pip install -r requirements.txt
cp .env.example .env
```

## Configuration

Edit `.env` and replace only the API-key placeholder:

```dotenv
OPENAI_API_KEY=your-openai-compatible-api-key
OPENAI_ENDPOINT=https://aiportalapi.stu-platform.live/jpe
OPENAI_MODEL=GPT-4o-mini
```

Environment variables:

| Variable | Required | Description |
| --- | --- | --- |
| `OPENAI_API_KEY` | Yes | Secret key for the OpenAI-compatible gateway. |
| `OPENAI_ENDPOINT` | Yes | Exact gateway base URL. |
| `OPENAI_MODEL` | No | Model identifier; defaults to `GPT-4o-mini`. |

The fresh-inference endpoint is `/jpe`. It is passed to `ChatOpenAI` exactly as supplied because the gateway already defines the API base path. The application does **not** append `/v1`. The cached `/jpe/v2` route is intentionally not used so each image receives a fresh inference request.

## Run

```powershell
python assignment_12.py
```

No `input()` prompt is used. The program automatically processes the three URLs in `IMAGE_URLS`.

Representative output:

```text
Satellite Cloud Detection - processing 3 images

[1/3] Image: https://example.com/satellite-image-1.jpg
Prediction: Cloudy
Confidence: 92.4%

[2/3] Image: https://example.com/satellite-image-2.jpg
Prediction: Clear
Confidence: 88.0%

[3/3] Image: https://example.com/satellite-image-3.jpg
Prediction: Cloudy
Confidence: 95.5%

Completed: 3 succeeded, 0 failed.
```

Predictions vary because they come from live model inference. The confidence percentage is the model's self-reported confidence, not a statistically calibrated accuracy measurement.

## Step-by-step solution

1. Load `.env` and validate the API key, endpoint, and optional model name.
2. Initialize `ChatOpenAI` with the exact custom gateway base URL and deterministic temperature.
3. Attach a Pydantic schema that restricts the label to `Cloudy` or `Clear` and confidence to the range 0-100.
4. Iterate through the fixed list of three NASA image URLs without asking for user input.
5. Build one multimodal message per image containing the classification instruction and the remote image URL.
6. Invoke GPT-4o-mini and validate the structured response.
7. Print the prediction and confidence, or a sanitized error, then continue to the next image.
8. Exit with a nonzero status if configuration fails or any image cannot be classified.

## Multimodal and structured output references

- [LangChain ChatOpenAI integration](https://docs.langchain.com/oss/python/integrations/chat/openai) documents installation, custom `base_url` configuration, structured output, and image inputs.
- [LangChain multimodal messages](https://docs.langchain.com/oss/python/langchain/messages#multimodal) describes portable content blocks for image data.
- [OpenAI images and vision](https://developers.openai.com/api/docs/guides/images-vision) documents URL-based image inputs.
- [GPT-4o-mini model](https://developers.openai.com/api/docs/models/gpt-4o-mini) lists image input and structured output support.

## Error handling

- Missing or invalid configuration stops the program before any model request.
- A failure for one image is reported without stopping the remaining images.
- Error messages show only the exception type and never print the API key or raw response body.
- The final summary reports how many classifications succeeded and failed.

## Security

- Never hardcode an API key in `assignment_12.py` or `README.md`.
- Store the active key only in `.env`, which is ignored by Git.
- Commit `.env.example`, which contains placeholders only.
- Revoke and replace any key that has been pasted into chat, logs, screenshots, or other shared locations.

## Knowledge and experience gained

- How to pass text and remote images together in a multimodal LLM message.
- How to use `ChatOpenAI` with an OpenAI-compatible gateway instead of an Azure-specific client.
- How structured output and Pydantic validation constrain model responses to an application contract.
- Why an LLM confidence value should not be treated as calibrated model accuracy.
- How automatic URL inputs make a console demonstration repeatable.
- How environment variables and `.gitignore` prevent credentials from entering source control.
- How per-image exception handling keeps a batch workflow running when one request fails.

## Assignment checklist

- [x] Accepts satellite imagery in JPEG format through URLs.
- [x] Uses GPT-4o-mini for multimodal inference.
- [x] Returns only `Cloudy` or `Clear` as the prediction label.
- [x] Displays a confidence percentage.
- [x] Contains exactly three fixed mock image URLs.
- [x] Processes the list automatically with no `input()` call.
- [x] Prints progress, predictions, confidence, errors, and a final summary in the console.
- [x] Keeps all application code in one `.py` file.
- [x] Documents the complete solution step by step.
- [x] Includes LangChain documentation for passing images to an LLM.
- [x] Describes knowledge and experience gained from the exercise.
