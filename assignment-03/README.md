# Assignment 03 - AI-Powered Meeting Summarizer

A command-line Python application that sends meeting transcripts to Azure OpenAI and prints concise summaries containing key points, decisions, and action items.

The program follows the assignment requirement to use a single application `.py` file and an automatic dummy input list. It processes five embedded meetings without calling Python's interactive `input()` function.

## Features

- Connects to an Azure OpenAI deployment through the official `openai` Python package.
- Reads the endpoint, API key, and deployment name from environment variables.
- Automatically summarizes five sample meetings: three Vietnamese and two English.
- Keeps each summary in the transcript's primary language.
- Requests three consistent sections: `Key Points`, `Decisions`, and `Action Items`.
- Reports missing configuration, missing dependencies, API failures, and empty model responses clearly.
- Never stores an Azure API key in source control.

## Project structure

```text
assignment-03/
|-- meeting_summarizer.py  # Complete application and five dummy transcripts
|-- requirements.txt       # Python dependency
|-- .gitignore             # Local environments, caches, and secret files
`-- README.md               # Setup, usage, and example outputs
```

## Requirements

- Python 3.10 or newer
- An Azure OpenAI resource
- An Azure OpenAI model deployment, such as a GPT-4o mini deployment
- The resource endpoint, API key, and deployment name

The application uses Azure OpenAI API version `2024-07-01-preview`, as specified in the assignment.

## Installation

### 1. Create a virtual environment

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Bash (macOS/Linux):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install the dependency

```bash
python -m pip install -r requirements.txt
```

## Azure configuration

Set all three variables in the terminal used to run the application. Replace the placeholder values with settings from your Azure OpenAI resource. `AZURE_DEPLOYMENT_NAME` must be the Azure deployment name, not only the underlying model family name.

PowerShell:

```powershell
$env:AZURE_OPENAI_ENDPOINT = "https://YOUR-RESOURCE.openai.azure.com/"
$env:AZURE_OPENAI_API_KEY = "YOUR-AZURE-OPENAI-KEY"
$env:AZURE_DEPLOYMENT_NAME = "YOUR-DEPLOYMENT-NAME"
```

Bash (macOS/Linux):

```bash
export AZURE_OPENAI_ENDPOINT="https://YOUR-RESOURCE.openai.azure.com/"
export AZURE_OPENAI_API_KEY="YOUR-AZURE-OPENAI-KEY"
export AZURE_DEPLOYMENT_NAME="YOUR-DEPLOYMENT-NAME"
```

Do not paste real credentials into `meeting_summarizer.py`, `README.md`, commits, screenshots, or logs. Environment files are ignored by Git, but this application intentionally reads the operating-system environment directly.

## Usage

Run the application after installing the dependency and setting the variables:

```bash
python meeting_summarizer.py
```

No command-line arguments or manual input are needed. The application automatically sends all five embedded transcripts to Azure OpenAI. Its console output follows this shape:

```text
Azure OpenAI Meeting Summarizer - processing 5 samples
========================================================================

[1/5] AI Chatbot Project Sync (Vietnamese)
------------------------------------------------------------------------
Key Points
- ...

Decisions
- ...

Action Items
- ...

...

========================================================================
Completed 5 of 5 meeting summaries.
```

## Five sample transcripts and illustrative outputs

The following summaries are **illustrative expected outputs** written for documentation because Azure credentials are not stored in this repository. Actual wording may vary slightly between runs. To regenerate real outputs, configure Azure as shown above, run the program, and capture its terminal output.

### Sample 1 - AI Chatbot Project Sync (Vietnamese)

Transcript:

```text
[10:02 - Họp đồng bộ dự án AI chatbot]
Anna: Chào mọi người, hôm nay mình cập nhật tiến độ dự án AI chatbot.
Minh: Backend đã xong phần xử lý intent, còn API đang được kiểm thử.
Trang: Frontend gặp lỗi khi hiển thị gợi ý từ chatbot. Mình sẽ sửa trong hôm nay.
Anna: Mọi người nhớ cập nhật tiến độ lên Jira trước 16:00. Có blocker nào không?
Minh: Không có blocker lớn.
Trang: Mình cần quyền truy cập môi trường dev từ đội DevOps.
Anna: Mình sẽ nhờ Huy cấp quyền cho Trang trước buổi trưa.
```

Illustrative summary:

```text
Key Points
- Backend đã hoàn thành xử lý intent và đang kiểm thử API.
- Frontend gặp lỗi hiển thị gợi ý và đang thiếu quyền truy cập môi trường dev.

Decisions
- Toàn đội cập nhật tiến độ lên Jira trước 16:00.

Action Items
- Trang sửa lỗi hiển thị gợi ý trong hôm nay.
- Anna nhờ Huy cấp quyền môi trường dev cho Trang trước buổi trưa.
```

### Sample 2 - Mobile App Release Planning (English)

Transcript:

```text
[09:00 - Mobile App Release Planning]
Maya: Version 2.4 is feature-complete, but two checkout defects are still open.
Ethan: The payment timeout fix is ready for review. The coupon issue needs one more day.
Liam: Regression testing can start tomorrow morning if both builds reach QA tonight.
Maya: We will move the release from Thursday to Friday to protect the test window.
Ethan: I will deliver the payment build by 3 PM and the coupon build by 6 PM.
Liam: I will publish the final test report by Thursday at noon.
```

Illustrative summary:

```text
Key Points
- Version 2.4 is feature-complete, with payment-timeout and coupon defects remaining.
- Regression testing can begin tomorrow if both corrected builds reach QA tonight.

Decisions
- The release moves from Thursday to Friday to preserve the regression-test window.

Action Items
- Ethan delivers the payment build by 3 PM and coupon build by 6 PM.
- Liam publishes the final test report by Thursday at noon.
```

### Sample 3 - Kế hoạch đào tạo nhân viên mới (Vietnamese)

Transcript:

```text
[14:00 - Họp kế hoạch đào tạo nhân viên mới]
Lan: Tháng sau có 12 nhân viên mới, cần hoàn thành chương trình hội nhập trong tuần đầu.
Phúc: Phòng IT có thể chuẩn bị laptop và tài khoản trước ngày 28.
Hương: Mình đề xuất hai buổi đào tạo trực tiếp và một khóa bảo mật trực tuyến.
Lan: Đồng ý. Buổi giới thiệu công ty sẽ diễn ra sáng thứ Hai, đào tạo nghiệp vụ vào thứ Tư.
Phúc: Mình sẽ gửi danh sách thiết bị cho Lan trước thứ Sáu tuần này.
Hương: Mình phụ trách tài liệu và theo dõi việc hoàn thành khóa bảo mật.
```

Illustrative summary:

```text
Key Points
- Có 12 nhân viên mới cần hoàn thành hội nhập trong tuần đầu của tháng sau.
- IT có thể chuẩn bị laptop và tài khoản trước ngày 28.

Decisions
- Tổ chức giới thiệu công ty sáng thứ Hai, đào tạo nghiệp vụ thứ Tư và một khóa bảo mật trực tuyến.

Action Items
- Phúc gửi danh sách thiết bị cho Lan trước thứ Sáu và chuẩn bị thiết bị trước ngày 28.
- Hương chuẩn bị tài liệu và theo dõi việc hoàn thành khóa bảo mật.
```

### Sample 4 - Customer Onboarding Improvement (English)

Transcript:

```text
[15:30 - Customer Onboarding Review]
Sofia: New customers currently wait an average of four days for account activation.
Noah: Most delays happen while we verify incomplete company documents.
Priya: We can add a document checklist to the welcome email and validate files at upload time.
Sofia: Let us pilot both changes with the next 20 customers and target a two-day activation time.
Noah: I will define the required-document rules by Tuesday.
Priya: I will update the email and upload form by Friday. Sofia will review pilot results in two weeks.
```

Illustrative summary:

```text
Key Points
- Account activation currently averages four days because company documents are often incomplete.
- A checklist and upload-time validation could reduce delays.

Decisions
- Pilot both improvements with the next 20 customers and target two-day activation.

Action Items
- Noah defines required-document rules by Tuesday.
- Priya updates the welcome email and upload form by Friday.
- Sofia reviews pilot results in two weeks.
```

### Sample 5 - Đánh giá chiến dịch marketing quý III (Vietnamese)

Transcript:

```text
[11:00 - Đánh giá chiến dịch marketing quý III]
Quân: Quảng cáo tìm kiếm vượt mục tiêu chuyển đổi 18%, nhưng chi phí mạng xã hội tăng cao.
Mai: Video ngắn có tương tác tốt nhất, đặc biệt với nhóm khách hàng từ 20 đến 30 tuổi.
Dũng: Email mang lại doanh thu ổn định và tỷ lệ hủy đăng ký vẫn dưới 1%.
Quân: Quý tới chúng ta sẽ chuyển 15% ngân sách mạng xã hội sang video ngắn và email.
Mai: Mình sẽ hoàn thiện kế hoạch nội dung video trước ngày 5 tháng sau.
Dũng: Mình sẽ chuẩn bị thử nghiệm A/B cho ba tiêu đề email và báo cáo sau hai tuần.
```

Illustrative summary:

```text
Key Points
- Quảng cáo tìm kiếm vượt mục tiêu chuyển đổi 18%, trong khi chi phí mạng xã hội tăng.
- Video ngắn có tương tác tốt nhất và email tiếp tục tạo doanh thu ổn định.

Decisions
- Chuyển 15% ngân sách mạng xã hội quý tới sang video ngắn và email.

Action Items
- Mai hoàn thiện kế hoạch nội dung video trước ngày 5 tháng sau.
- Dũng thử nghiệm A/B ba tiêu đề email và báo cáo sau hai tuần.
```

## How the application works

1. `load_configuration()` reads and validates the three required environment variables.
2. `create_azure_client()` initializes `AzureOpenAI` with the assignment's API version.
3. `process_sample_meetings()` loops over the five automatic dummy inputs.
4. `summarize_meeting()` sends each transcript to Chat Completions with low temperature for consistent summaries.
5. The returned summary is validated and printed before the next meeting is processed.

The application intentionally sends each sample as one request. Transcript chunking, file upload, a web interface, and interactive terminal prompts are outside this assignment's submission scope.

## Troubleshooting

### Missing environment variables

```text
ERROR: Missing required environment variable(s): ... See README.md for setup instructions.
```

Set every variable in the same terminal session, then run the program again.

### The `openai` package is missing

```bash
python -m pip install -r requirements.txt
```

### Authentication, deployment, or quota error

- Confirm that the endpoint belongs to the same Azure resource as the API key.
- Confirm that `AZURE_DEPLOYMENT_NAME` exactly matches the deployment name in Azure.
- Confirm that the deployed model supports Chat Completions.
- Check network access, Azure quota, and resource status.

## Assignment submission checklist

- [x] Azure OpenAI GPT integration using `AzureOpenAI`
- [x] Endpoint, API key, and deployment name loaded from environment variables
- [x] One clearly commented Python application file
- [x] Automatic dummy input list with five meetings
- [x] No interactive `input()` calls
- [x] Key points, decisions, and action items requested for every summary
- [x] Simple command-line interface for displaying results
- [x] Five transcript and illustrative-output examples documented in the README
- [x] Installation, configuration, usage, security, and troubleshooting documentation

## Notes

- Model responses are nondeterministic, so exact wording can differ even with `temperature=0.3`.
- Each run makes five Azure OpenAI requests and may consume quota.
- The program stops with a nonzero exit code if configuration, dependency loading, an API request, or summary validation fails.
