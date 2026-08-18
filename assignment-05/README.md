# Assignment 05 - Local LLaMA 3 Resume Generator

## Description

This project is an AI-powered resume generator that runs LLaMA 3 locally through `llama-cpp-python`. It converts structured candidate information into professional, ATS-friendly Markdown resumes while keeping personal data on the user's computer.

The solution follows an object-oriented design and processes three predefined candidate profiles automatically. It does not request manual console input.

## Features

- Runs an instruction-tuned LLaMA 3 GGUF model locally.
- Generates resumes tailored to a candidate's target role.
- Uses structured candidate data for skills, experience, education, projects, and achievements.
- Produces consistent Markdown sections suitable for an ATS-friendly resume.
- Instructs the model to use only supplied facts and avoid inventing qualifications.
- Processes three sample candidates in one sequential batch.
- Continues processing after an individual candidate fails.
- Validates model responses before accepting them.
- Provides clear errors for missing models, invalid paths, empty responses, and missing resume sections.

## Project Structure

```text
assignment-05/
|-- assignment05_llama3_resume_generator.py
`-- README.md
```

The entire application is contained in `assignment05_llama3_resume_generator.py`, as required by the assignment.

## Requirements

- Python 3.10 or newer
- `llama-cpp-python`
- A local instruction-tuned LLaMA 3 model in GGUF format
- Sufficient memory for the selected model and quantization

The model is not included in this repository because GGUF files are large and may have separate license terms.

## Installation

### 1. Clone or download the project

```bash
git clone <your-repository-url>
cd assignment-05
```

### 2. Create a virtual environment

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Bash or zsh:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install the dependency

```bash
python -m pip install --upgrade pip
python -m pip install llama-cpp-python
```

For platform-specific CPU, CUDA, Metal, or Vulkan installation options, refer to the [official llama-cpp-python installation documentation](https://github.com/abetlen/llama-cpp-python#installation).

## Model Setup

Download a compatible instruction-tuned LLaMA 3 GGUF model from a trusted model provider after reviewing and accepting its license. A quantized model such as Q4 may require less memory than a full-precision model.

Set `LLAMA_MODEL_PATH` to the downloaded `.gguf` file.

PowerShell:

```powershell
$env:LLAMA_MODEL_PATH = "C:\models\Meta-Llama-3-8B-Instruct-Q4_K_M.gguf"
```

Bash or zsh:

```bash
export LLAMA_MODEL_PATH="/models/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf"
```

The application validates that the configured path exists, refers to a file, and ends with `.gguf` before loading the model.

## Usage

Run the application after activating the virtual environment and configuring the model path:

```bash
python assignment05_llama3_resume_generator.py
```

The program loads the model once, processes all three sample profiles, prints each resume, and displays a final summary:

```text
Summary: 3 processed, 3 succeeded, 0 failed.
```

The exact resume wording can vary between model runs.

## Sample Inputs

The application automatically processes these three fictional candidates:

| Candidate | Target role | Selected skills |
|---|---|---|
| Maya Chen | Software Engineer | Python, FastAPI, PostgreSQL, AWS, Docker |
| Daniel Martinez | Data Analyst | SQL, Python, pandas, Tableau, Excel |
| Aisha Rahman | Digital Marketing Specialist | SEO, Google Analytics, content strategy, email marketing |

Each input also includes contact information, employment history, education, one project, and an achievement. The complete input records are defined in `SAMPLE_PROFILES`.

## Representative Output

The following shortened example demonstrates the generated Markdown format:

```markdown
# Maya Chen
**Software Engineer** | maya.chen@example.com | +1-555-0101 | Seattle, WA

## Professional Summary
Software engineer experienced in Python services, cloud deployment, and reliable APIs.

## Skills
Python, FastAPI, PostgreSQL, AWS, Docker, Git, REST APIs

## Experience
### Software Engineer - Northstar Systems (2022-Present)
- Reduced API response time by 35% by profiling and optimizing Python services.
- Automated AWS deployment steps, reducing release preparation by 4 hours.

## Projects
### Inventory Alert Service
- Built a FastAPI and PostgreSQL service that notified staff about low inventory.

## Education
B.S. Computer Science - University of Washington, 2022

## Achievements
Northstar Engineering Impact Award, 2024
```

Three complete representative outputs are also included in the Python module documentation. They are examples rather than captured live responses because a GGUF model is not distributed with the project.

## Design

### `ResumeProfile`

A frozen dataclass that stores one candidate's target role, contact details, skills, work experience, education, projects, and achievements.

### `Llama3ResumeGenerator`

An object-oriented wrapper responsible for:

1. Validating the model path.
2. Loading LLaMA 3 with a 4096-token context window.
3. Building role-aware chat prompts from structured candidate data.
4. Calling `create_chat_completion()`.
5. Extracting and validating the generated resume.
6. Processing a list of candidates without stopping after an individual failure.

### Prompt engineering

The prompt tells the model to:

- Produce an ATS-friendly Markdown resume.
- Use only information present in the candidate profile.
- Avoid fabricated qualifications, dates, employers, metrics, or awards.
- Use measurable bullets only when measurements exist in the source data.
- Return the required sections in a fixed order.

## Output Validation

A generated resume is accepted only when it:

- Is a non-empty string.
- Contains the candidate's name.
- Contains all required headings:
  - Professional Summary
  - Skills
  - Experience
  - Projects
  - Education
  - Achievements

Markdown code fences are removed when a model adds them despite the prompt.

## Error Handling

The application handles:

- Missing `LLAMA_MODEL_PATH`
- Missing or invalid model files
- Non-GGUF model paths
- Missing `llama-cpp-python` installation
- Model-loading failures
- Local inference failures
- Empty or malformed model responses
- Missing required resume sections

An error for one candidate is recorded and logged without preventing later profiles from being processed.

Exit codes:

| Code | Meaning |
|---:|---|
| `0` | All resumes were generated successfully |
| `1` | Configuration or model-loading failure |
| `2` | Batch completed with one or more failed resumes |

## Privacy and Offline Operation

Candidate data and inference remain local when the GGUF model has already been downloaded. The application does not call a hosted AI API, upload resume information, or automatically download files.

## Troubleshooting

### `LLAMA_MODEL_PATH is not configured`

Set the environment variable to the full path of a local `.gguf` file, then run the application from the same terminal session.

### `llama-cpp-python is not installed`

Activate the intended virtual environment and run:

```bash
python -m pip install llama-cpp-python
```

### Model loading is slow or memory is insufficient

Use a smaller quantized GGUF model, close memory-intensive applications, or follow the official installation instructions for supported hardware acceleration.

### Generated resume is rejected for missing headings

Run the generation again or use a LLaMA 3 Instruct GGUF with a compatible chat template. The validation intentionally rejects incomplete output.

## Limitations

- Output quality depends on the selected model and quantization.
- CPU generation can be slow on systems without hardware acceleration.
- The application produces Markdown text rather than PDF or Word documents.
- Generated resumes should be reviewed by a person before professional use.

## Project Status

The assignment implementation is complete. Syntax, prompt construction, batch behavior, output validation, and error paths were verified with an injected fake model backend. Live inference requires the user to provide a compatible LLaMA 3 GGUF model.
