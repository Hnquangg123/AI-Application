"""Assignment 05 - Build Resume Generation Using LLaMA 3 Locally.

THREE SAMPLE INPUTS
-------------------
1. Maya Chen - Software Engineer with Python, FastAPI, PostgreSQL, and AWS skills.
2. Daniel Martinez - Data Analyst with SQL, Python, Tableau, and Excel skills.
3. Aisha Rahman - Digital Marketing Specialist with SEO, content, analytics, and
   campaign-management skills.

The complete structured input records are stored in SAMPLE_PROFILES below. They are
processed automatically and do not require interactive data entry.

THREE REPRESENTATIVE SAMPLE OUTPUTS
-----------------------------------
These examples show the expected format. A live local model may choose different
wording while using the same supplied facts.

Sample output 1 - Maya Chen

    # Maya Chen
    **Software Engineer** | maya.chen@example.com | +1-555-0101 | Seattle, WA

    ## Professional Summary
    Software engineer experienced in Python services, cloud deployment, and reliable
    APIs, with a record of reducing response times and delivery effort.

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

Sample output 2 - Daniel Martinez

    # Daniel Martinez
    **Data Analyst** | daniel.martinez@example.com | +1-555-0102 | Austin, TX

    ## Professional Summary
    Data analyst who turns operational data into dashboards and recommendations using
    SQL, Python, Tableau, and advanced Excel.

    ## Skills
    SQL, Python, pandas, Tableau, Excel, Data Cleaning, Data Visualization

    ## Experience
    ### Data Analyst - Bright Retail Group (2021-Present)
    - Created Tableau dashboards used by 25 regional managers.
    - Automated weekly reporting with Python, saving approximately 6 hours per week.

    ## Projects
    ### Customer Retention Analysis
    - Analyzed purchase patterns and identified customer segments with elevated churn.

    ## Education
    B.B.A. Business Analytics - Texas State University, 2021

    ## Achievements
    Bright Retail Process Improvement Award, 2023

Sample output 3 - Aisha Rahman

    # Aisha Rahman
    **Digital Marketing Specialist** | aisha.rahman@example.com | +1-555-0103 | Chicago, IL

    ## Professional Summary
    Digital marketer experienced in SEO, content strategy, campaign analytics, and
    cross-channel optimization.

    ## Skills
    SEO, Google Analytics, Content Strategy, Email Marketing, Google Ads, HubSpot

    ## Experience
    ### Digital Marketing Specialist - Greenline Media (2022-Present)
    - Increased organic website traffic by 42% through content and technical SEO work.
    - Improved email click-through rate from 2.8% to 4.1% through audience segmentation.

    ## Projects
    ### Sustainable Living Campaign
    - Coordinated search, email, and social content for a three-month product campaign.

    ## Education
    B.A. Marketing - University of Illinois Chicago, 2022

    ## Achievements
    Google Analytics Certification, 2023
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable


LOGGER = logging.getLogger(__name__)

REQUIRED_HEADINGS = (
    "## Professional Summary",
    "## Skills",
    "## Experience",
    "## Projects",
    "## Education",
    "## Achievements",
)


class ModelConfigurationError(RuntimeError):
    """Raised when the local model cannot be configured or loaded."""


class ResumeGenerationError(RuntimeError):
    """Raised when the model does not return a usable resume."""


@dataclass(frozen=True)
class ResumeProfile:
    """Structured candidate information used to generate one resume."""

    full_name: str
    target_role: str
    email: str
    phone: str
    location: str
    skills: list[str]
    experience: list[dict[str, Any]]
    education: list[dict[str, str]]
    projects: list[dict[str, Any]]
    achievements: list[str]


SAMPLE_PROFILES = [
    ResumeProfile(
        full_name="Maya Chen",
        target_role="Software Engineer",
        email="maya.chen@example.com",
        phone="+1-555-0101",
        location="Seattle, WA",
        skills=["Python", "FastAPI", "PostgreSQL", "AWS", "Docker", "Git", "REST APIs"],
        experience=[
            {
                "role": "Software Engineer",
                "company": "Northstar Systems",
                "period": "2022-Present",
                "details": [
                    "Reduced API response time by 35% by profiling and optimizing Python services.",
                    "Automated AWS deployment steps, reducing release preparation by 4 hours.",
                ],
            }
        ],
        education=[
            {
                "degree": "B.S. Computer Science",
                "institution": "University of Washington",
                "year": "2022",
            }
        ],
        projects=[
            {
                "name": "Inventory Alert Service",
                "details": [
                    "Built a FastAPI and PostgreSQL service that notified staff about low inventory."
                ],
            }
        ],
        achievements=["Northstar Engineering Impact Award, 2024"],
    ),
    ResumeProfile(
        full_name="Daniel Martinez",
        target_role="Data Analyst",
        email="daniel.martinez@example.com",
        phone="+1-555-0102",
        location="Austin, TX",
        skills=[
            "SQL",
            "Python",
            "pandas",
            "Tableau",
            "Excel",
            "Data Cleaning",
            "Data Visualization",
        ],
        experience=[
            {
                "role": "Data Analyst",
                "company": "Bright Retail Group",
                "period": "2021-Present",
                "details": [
                    "Created Tableau dashboards used by 25 regional managers.",
                    "Automated weekly reporting with Python, saving approximately 6 hours per week.",
                ],
            }
        ],
        education=[
            {
                "degree": "B.B.A. Business Analytics",
                "institution": "Texas State University",
                "year": "2021",
            }
        ],
        projects=[
            {
                "name": "Customer Retention Analysis",
                "details": [
                    "Analyzed purchase patterns and identified customer segments with elevated churn."
                ],
            }
        ],
        achievements=["Bright Retail Process Improvement Award, 2023"],
    ),
    ResumeProfile(
        full_name="Aisha Rahman",
        target_role="Digital Marketing Specialist",
        email="aisha.rahman@example.com",
        phone="+1-555-0103",
        location="Chicago, IL",
        skills=[
            "SEO",
            "Google Analytics",
            "Content Strategy",
            "Email Marketing",
            "Google Ads",
            "HubSpot",
        ],
        experience=[
            {
                "role": "Digital Marketing Specialist",
                "company": "Greenline Media",
                "period": "2022-Present",
                "details": [
                    "Increased organic website traffic by 42% through content and technical SEO work.",
                    "Improved email click-through rate from 2.8% to 4.1% through audience segmentation.",
                ],
            }
        ],
        education=[
            {
                "degree": "B.A. Marketing",
                "institution": "University of Illinois Chicago",
                "year": "2022",
            }
        ],
        projects=[
            {
                "name": "Sustainable Living Campaign",
                "details": [
                    "Coordinated search, email, and social content for a three-month product campaign."
                ],
            }
        ],
        achievements=["Google Analytics Certification, 2023"],
    ),
]


class Llama3ResumeGenerator:
    """Object-oriented wrapper around a locally loaded LLaMA 3 GGUF model."""

    def __init__(
        self,
        model_path: str | os.PathLike[str],
        n_ctx: int = 4096,
        *,
        backend_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.model_path = Path(model_path).expanduser().resolve()
        self.n_ctx = n_ctx
        self._validate_model_path()

        if isinstance(n_ctx, bool) or not isinstance(n_ctx, int) or n_ctx < 2048:
            raise ModelConfigurationError("n_ctx must be an integer of at least 2048.")

        if backend_factory is None:
            try:
                from llama_cpp import Llama
            except ImportError as exc:
                raise ModelConfigurationError(
                    "llama-cpp-python is not installed. Run: "
                    "python -m pip install llama-cpp-python"
                ) from exc
            backend_factory = Llama

        try:
            self._llm = backend_factory(
                model_path=str(self.model_path),
                n_ctx=n_ctx,
                n_gpu_layers=0,
                chat_format="llama-3",
                verbose=False,
            )
        except Exception as exc:
            raise ModelConfigurationError(
                f"Failed to load the local LLaMA 3 model: {exc}"
            ) from exc

    def _validate_model_path(self) -> None:
        if not self.model_path.exists():
            raise ModelConfigurationError(
                f"Model file was not found: {self.model_path}"
            )
        if not self.model_path.is_file():
            raise ModelConfigurationError(
                f"Model path is not a file: {self.model_path}"
            )
        if self.model_path.suffix.lower() != ".gguf":
            raise ModelConfigurationError("The local model must be a .gguf file.")

    def build_prompt(self, profile: ResumeProfile) -> list[dict[str, str]]:
        """Build LLaMA 3 chat messages from one structured candidate profile."""
        profile_json = json.dumps(asdict(profile), indent=2, ensure_ascii=False)
        return [
            {
                "role": "system",
                "content": (
                    "You are a professional resume writer. Create concise, ATS-friendly "
                    "Markdown resumes. Use only facts supplied by the user. Never invent "
                    "employers, dates, qualifications, metrics, technologies, or awards. "
                    "Use measurable achievement bullets only when the supplied facts include "
                    "measurements. Return the resume only, without commentary or code fences."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Create a tailored resume for the candidate below. Start with '# Full Name' "
                    "and a contact line. Use exactly these section headings in this order:\n"
                    "## Professional Summary\n"
                    "## Skills\n"
                    "## Experience\n"
                    "## Projects\n"
                    "## Education\n"
                    "## Achievements\n\n"
                    "Candidate data:\n" + profile_json
                ),
            },
        ]

    def generate_resume(self, profile: ResumeProfile) -> str:
        """Generate and validate one Markdown resume."""
        try:
            response = self._llm.create_chat_completion(
                messages=self.build_prompt(profile),
                temperature=0.2,
                max_tokens=1200,
            )
        except Exception as exc:
            raise ResumeGenerationError(
                f"Local model generation failed for {profile.full_name}: {exc}"
            ) from exc

        resume = self._extract_content(response)
        self._validate_resume(resume, profile)
        return resume

    @staticmethod
    def _extract_content(response: Any) -> str:
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ResumeGenerationError(
                "The model response did not contain choices[0].message.content."
            ) from exc

        if not isinstance(content, str) or not content.strip():
            raise ResumeGenerationError("The model returned an empty resume.")

        content = content.strip()
        if content.startswith("```markdown"):
            content = content[len("```markdown") :].lstrip()
        elif content.startswith("```"):
            content = content[3:].lstrip()
        if content.endswith("```"):
            content = content[:-3].rstrip()
        return content

    @staticmethod
    def _validate_resume(resume: str, profile: ResumeProfile) -> None:
        if profile.full_name.casefold() not in resume.casefold():
            raise ResumeGenerationError(
                "The generated resume does not contain the candidate's name."
            )

        missing_headings = [
            heading for heading in REQUIRED_HEADINGS if heading not in resume
        ]
        if missing_headings:
            raise ResumeGenerationError(
                "The generated resume is missing required heading(s): "
                + ", ".join(missing_headings)
            )

    def generate_batch(self, profiles: list[ResumeProfile]) -> list[dict[str, Any]]:
        """Generate every resume and continue after individual failures."""
        results: list[dict[str, Any]] = []

        for index, profile in enumerate(profiles, start=1):
            LOGGER.info(
                "Generating resume for %s (%d of %d)",
                profile.full_name,
                index,
                len(profiles),
            )
            try:
                resume = self.generate_resume(profile)
                results.append(
                    {
                        "candidate": profile.full_name,
                        "target_role": profile.target_role,
                        "status": "success",
                        "resume": resume,
                    }
                )
            except Exception as exc:
                LOGGER.error("Could not generate %s's resume: %s", profile.full_name, exc)
                results.append(
                    {
                        "candidate": profile.full_name,
                        "target_role": profile.target_role,
                        "status": "error",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )

        return results


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def print_results(results: list[dict[str, Any]]) -> None:
    """Print generated resumes and a concise batch summary."""
    print("\nGENERATED RESUMES")
    print("=" * 72)
    for index, result in enumerate(results, start=1):
        print(
            f"\nResume {index}: {result['candidate']} - {result['target_role']} "
            f"[{result['status'].upper()}]"
        )
        print("-" * 72)
        if result["status"] == "success":
            print(result["resume"])
        else:
            print(result["error"])

    successes = sum(result["status"] == "success" for result in results)
    failures = len(results) - successes
    print("\n" + "=" * 72)
    print(
        f"Summary: {len(results)} processed, "
        f"{successes} succeeded, {failures} failed."
    )


def main() -> int:
    """Load the local model and automatically process all sample profiles."""
    configure_logging()
    model_path = os.getenv("LLAMA_MODEL_PATH", "").strip()
    if not model_path:
        LOGGER.error("LLAMA_MODEL_PATH is not configured.")
        LOGGER.error("Set it to a local instruction-tuned LLaMA 3 .gguf file.")
        return 1

    try:
        generator = Llama3ResumeGenerator(model_path=model_path)
    except ModelConfigurationError as exc:
        LOGGER.error("Model configuration error: %s", exc)
        return 1

    results = generator.generate_batch(SAMPLE_PROFILES)
    print_results(results)
    return 0 if all(result["status"] == "success" for result in results) else 2


if __name__ == "__main__":
    sys.exit(main())
