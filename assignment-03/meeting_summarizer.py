"""Automatically summarize five sample meetings with Azure OpenAI.

Assignment 03 requires a single Python application file, automatic dummy
inputs, and no interactive console reads. Configure the three Azure
environment variables documented in README.md, then run this file.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Final


API_VERSION: Final = "2024-07-01-preview"
TEMPERATURE: Final = 0.3
MAX_TOKENS: Final = 500

REQUIRED_ENVIRONMENT_VARIABLES: Final = (
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
    "AZURE_DEPLOYMENT_NAME",
)

# The assignment asks for a dummy input list that runs automatically. Each
# meeting is intentionally short enough to fit in one Chat Completions request.
SAMPLE_MEETINGS: Final = [
    {
        "title": "AI Chatbot Project Sync",
        "language": "Vietnamese",
        "transcript": """[10:02 - Họp đồng bộ dự án AI chatbot]
Anna: Chào mọi người, hôm nay mình cập nhật tiến độ dự án AI chatbot.
Minh: Backend đã xong phần xử lý intent, còn API đang được kiểm thử.
Trang: Frontend gặp lỗi khi hiển thị gợi ý từ chatbot. Mình sẽ sửa trong hôm nay.
Anna: Mọi người nhớ cập nhật tiến độ lên Jira trước 16:00. Có blocker nào không?
Minh: Không có blocker lớn.
Trang: Mình cần quyền truy cập môi trường dev từ đội DevOps.
Anna: Mình sẽ nhờ Huy cấp quyền cho Trang trước buổi trưa.""",
    },
    {
        "title": "Mobile App Release Planning",
        "language": "English",
        "transcript": """[09:00 - Mobile App Release Planning]
Maya: Version 2.4 is feature-complete, but two checkout defects are still open.
Ethan: The payment timeout fix is ready for review. The coupon issue needs one more day.
Liam: Regression testing can start tomorrow morning if both builds reach QA tonight.
Maya: We will move the release from Thursday to Friday to protect the test window.
Ethan: I will deliver the payment build by 3 PM and the coupon build by 6 PM.
Liam: I will publish the final test report by Thursday at noon.""",
    },
    {
        "title": "Kế hoạch đào tạo nhân viên mới",
        "language": "Vietnamese",
        "transcript": """[14:00 - Họp kế hoạch đào tạo nhân viên mới]
Lan: Tháng sau có 12 nhân viên mới, cần hoàn thành chương trình hội nhập trong tuần đầu.
Phúc: Phòng IT có thể chuẩn bị laptop và tài khoản trước ngày 28.
Hương: Mình đề xuất hai buổi đào tạo trực tiếp và một khóa bảo mật trực tuyến.
Lan: Đồng ý. Buổi giới thiệu công ty sẽ diễn ra sáng thứ Hai, đào tạo nghiệp vụ vào thứ Tư.
Phúc: Mình sẽ gửi danh sách thiết bị cho Lan trước thứ Sáu tuần này.
Hương: Mình phụ trách tài liệu và theo dõi việc hoàn thành khóa bảo mật.""",
    },
    {
        "title": "Customer Onboarding Improvement",
        "language": "English",
        "transcript": """[15:30 - Customer Onboarding Review]
Sofia: New customers currently wait an average of four days for account activation.
Noah: Most delays happen while we verify incomplete company documents.
Priya: We can add a document checklist to the welcome email and validate files at upload time.
Sofia: Let us pilot both changes with the next 20 customers and target a two-day activation time.
Noah: I will define the required-document rules by Tuesday.
Priya: I will update the email and upload form by Friday. Sofia will review pilot results in two weeks.""",
    },
    {
        "title": "Đánh giá chiến dịch marketing quý III",
        "language": "Vietnamese",
        "transcript": """[11:00 - Đánh giá chiến dịch marketing quý III]
Quân: Quảng cáo tìm kiếm vượt mục tiêu chuyển đổi 18%, nhưng chi phí mạng xã hội tăng cao.
Mai: Video ngắn có tương tác tốt nhất, đặc biệt với nhóm khách hàng từ 20 đến 30 tuổi.
Dũng: Email mang lại doanh thu ổn định và tỷ lệ hủy đăng ký vẫn dưới 1%.
Quân: Quý tới chúng ta sẽ chuyển 15% ngân sách mạng xã hội sang video ngắn và email.
Mai: Mình sẽ hoàn thiện kế hoạch nội dung video trước ngày 5 tháng sau.
Dũng: Mình sẽ chuẩn bị thử nghiệm A/B cho ba tiêu đề email và báo cáo sau hai tuần.""",
    },
]


class ConfigurationError(RuntimeError):
    """Raised when the application cannot be configured safely."""


class EmptySummaryError(RuntimeError):
    """Raised when Azure OpenAI returns no usable summary text."""


def load_configuration() -> dict[str, str]:
    """Read required Azure settings and report every missing variable."""

    configuration = {
        name: os.getenv(name, "").strip()
        for name in REQUIRED_ENVIRONMENT_VARIABLES
    }
    missing = [name for name, value in configuration.items() if not value]

    if missing:
        missing_list = ", ".join(missing)
        raise ConfigurationError(
            f"Missing required environment variable(s): {missing_list}. "
            "See README.md for setup instructions."
        )

    return configuration


def create_azure_client(configuration: dict[str, str]) -> Any:
    """Create the Azure client after configuration has been validated."""

    try:
        from openai import AzureOpenAI
    except ModuleNotFoundError as error:
        raise ConfigurationError(
            "The 'openai' package is not installed. "
            "Run: python -m pip install -r requirements.txt"
        ) from error

    return AzureOpenAI(
        api_version=API_VERSION,
        azure_endpoint=configuration["AZURE_OPENAI_ENDPOINT"],
        api_key=configuration["AZURE_OPENAI_API_KEY"],
    )


def build_summary_prompt(transcript: str) -> str:
    """Build a consistent prompt for a structured meeting summary."""

    return f"""Summarize the meeting transcript below.

Requirements:
- Write the summary in the transcript's primary language.
- Be concise and factual. Do not invent missing information.
- Use exactly these three section headings: Key Points, Decisions, Action Items.
- Use bullet points under each heading.
- For each action item, include its owner and deadline when stated.
- If a section has no information, write one bullet saying "None identified" in the transcript's language.

Meeting transcript:
{transcript}"""


def summarize_meeting(client: Any, deployment_name: str, transcript: str) -> str:
    """Send one transcript to Azure OpenAI and return its summary text."""

    response = client.chat.completions.create(
        model=deployment_name,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant specialized in accurate, "
                    "concise meeting summaries."
                ),
            },
            {"role": "user", "content": build_summary_prompt(transcript)},
        ],
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )

    if not response.choices:
        raise EmptySummaryError("Azure OpenAI returned no completion choices.")

    summary = response.choices[0].message.content
    if not summary or not summary.strip():
        raise EmptySummaryError("Azure OpenAI returned an empty summary.")

    return summary.strip()


def process_sample_meetings(
    client: Any,
    deployment_name: str,
    meetings: list[dict[str, str]] = SAMPLE_MEETINGS,
) -> None:
    """Summarize and display every meeting in the automatic dummy list."""

    total = len(meetings)
    print(f"Azure OpenAI Meeting Summarizer - processing {total} samples")
    print("=" * 72)

    for index, meeting in enumerate(meetings, start=1):
        print(f"\n[{index}/{total}] {meeting['title']} ({meeting['language']})")
        print("-" * 72)
        summary = summarize_meeting(
            client=client,
            deployment_name=deployment_name,
            transcript=meeting["transcript"],
        )
        print(summary)

    print("\n" + "=" * 72)
    print(f"Completed {total} of {total} meeting summaries.")


def main() -> int:
    """Validate configuration, create the client, and run all samples."""

    try:
        configuration = load_configuration()
        client = create_azure_client(configuration)
        process_sample_meetings(
            client=client,
            deployment_name=configuration["AZURE_DEPLOYMENT_NAME"],
        )
    except (ConfigurationError, EmptySummaryError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    except Exception as error:  # Azure SDK errors vary by HTTP failure type.
        print(
            "ERROR: Azure OpenAI could not summarize the meetings. "
            "Check the endpoint, API key, deployment name, network, and quota.",
            file=sys.stderr,
        )
        print(f"Details: {type(error).__name__}: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
