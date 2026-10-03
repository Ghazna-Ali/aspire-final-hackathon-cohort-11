# 🎯 CareerOps AI — Career Assistant AI

CareerOps AI is a multi-agent career assistant built with **Python, Streamlit, and CrewAI**.

Upload your CV, provide a job description, choose an analysis type, and receive a focused AI-generated career report that can be downloaded as a branded PDF.

The application uses **Google Gemini models exclusively** through CrewAI.

---

## 📌 Features

* 📄 CV upload and text extraction
* 📝 Job description input
* 🤖 Seven specialized career agents
* 🎯 Job Match Score
* 🧩 Skill Gap Detector
* ✉️ Cover Letter Generation
* 🗺️ Career Roadmap
* 🛡️ Job Legitimacy Check
* 🏭 Company Check
* 🔀 Similar Roles
* 📚 Insight Archive
* 📄 Branded PDF reports
* 🔄 Automatic retry for temporary API failures
* 🌙 Dark Streamlit interface
* ⚙️ Gemini model selector
* 🔐 API key validation
* 🧠 Single-agent execution per analysis

---

## 🤖 Core Agents

| Agent                | Purpose                                                                       |
| -------------------- | ----------------------------------------------------------------------------- |
| 🧭 Manager           | Career goals, strengths, gaps, and next steps                                 |
| 💼 Job Analyst       | Job requirements, skills, tools, certifications, and keywords                 |
| 📄 CV Analyst        | CV vs job comparison, matches, gaps, and improvements                         |
| 🏢 Research Agent    | Company and opportunity analysis from provided text                           |
| ✍️ Application Agent | Application strategy, CV improvements, and cover-letter guidance              |
| 🎤 Interview Agent   | Technical, behavioral, situational, and job-specific preparation              |
| 🔎 Critic Agent      | Reviews weaknesses, missing evidence, inconsistencies, and unsupported claims |

---

## ✨ Feature Tasks

Feature tasks reuse the existing agents rather than creating additional agents.

| Feature                    | Existing Agent    |
| -------------------------- | ----------------- |
| 🎯 Job Match Score         | CV Analyst        |
| 🧩 Skill Gap Detector      | CV Analyst        |
| ✉️ Cover Letter Generation | Application Agent |
| 🗺️ Career Roadmap         | Manager           |
| 🛡️ Job Legitimacy Check   | Research Agent    |
| 🏭 Company Check           | Research Agent    |
| 🔀 Similar Roles           | Manager           |

---

## 🧮 Job Match Score

The Job Match Score uses four categories:

| Category                     | Weight |
| ---------------------------- | -----: |
| Technical Skills             |    40% |
| Experience and Projects      |    30% |
| Education and Certifications |    10% |
| Keywords and Soft Skills     |    20% |

When all four category scores are available, the application recalculates the overall percentage using these weights.

---

## 🔄 How It Works

```text
CV
 │
 ▼
Job Description
 │
 ▼
Selected Analysis
 │
 ▼
Existing Career Agent
 │
 ▼
Single-Agent CrewAI Execution
 │
 ▼
Google Gemini
 │
 ▼
Markdown Result
 │
 ├──► Insight Archive
 │
 └──► PDF Report
```

Only the selected agent runs for each request.

---

## 🏗️ Architecture

```text
┌──────────────────────────────┐
│       Streamlit UI           │
│            app.py            │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│      Model Selector          │
│        model_ui.py           │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│      Model Manager           │
│     model_manager.py         │
│                              │
│   Google Gemini only         │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│       CrewAI Agent           │
│                              │
│ Manager / Job Analyst /      │
│ CV Analyst / Research /      │
│ Application / Interview /    │
│ Critic                       │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│       Google Gemini          │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│      Markdown Result         │
└──────────────┬───────────────┘
               │
        ┌──────┴──────┐
        ▼             ▼
   Insight Archive   PDF Report
```

---

## 📂 Project Structure

```text
career-assistant-ai/
│
├── app.py
├── agents.py
├── tasks.py
├── features.py
├── model_manager.py
├── model_ui.py
├── report.py
├── tools.py
├── memory.py
├── requirements.txt
├── README.md
│
├── .env.example
├── .gitignore
│
└── .streamlit/
    └── secrets.toml
```

### File Responsibilities

| File               | Responsibility                                         |
| ------------------ | ------------------------------------------------------ |
| `app.py`           | Streamlit UI, state, panels, execution, results        |
| `agents.py`        | Seven CrewAI career agents                             |
| `tasks.py`         | Core agent task definitions                            |
| `features.py`      | Additional feature tasks                               |
| `model_manager.py` | Gemini model catalog, API validation, and LLM creation |
| `model_ui.py`      | Gemini model selector                                  |
| `report.py`        | Branded PDF generation                                 |
| `tools.py`         | CV extraction and supporting tools                     |
| `memory.py`        | Career session data                                    |
| `requirements.txt` | Python dependencies                                    |

---

## 🤖 Supported Models

The application currently supports Google Gemini models only.

| Model                 | Provider |
| --------------------- | -------- |
| Gemini 3.8 Flash      | Google   |
| Gemini 3.5 Flash-Lite | Google   |
| Gemini 2.5 Flash      | Google   |

The models are configured in:

```text
model_manager.py
```

---

## 🔐 API Key Configuration

The application requires a Google Gemini API key.

Get a key from:

https://aistudio.google.com/apikey

### Streamlit Secrets

Create:

```text
.streamlit/secrets.toml
```

and add:

```toml
GEMINI_API_KEY = "your_gemini_api_key"
```

### Environment Variable

Alternatively:

```env
GEMINI_API_KEY=your_gemini_api_key
```

Never commit API keys to GitHub.

---

## 💻 Installation

### 1. Clone

```bash
git clone https://github.com/Ghazna-Ali/career-assistant-ai.git
cd career-assistant-ai
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

### Windows

```bash
venv\Scripts\activate
```

### Linux / macOS

```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Gemini

Add your Gemini API key to Streamlit Secrets:

```toml
GEMINI_API_KEY = "your_gemini_api_key"
```

### 5. Run

```bash
streamlit run app.py
```

---

## 🖥️ Using the Application

### Step 1 — Configure Gemini

Open the Settings panel and select an available Gemini model.

A green indicator means the Gemini API key is valid.

### Step 2 — Add your CV

Upload your CV or provide the CV text.

### Step 3 — Add the job description

Paste the complete job description.

### Step 4 — Select an analysis

Choose an agent or feature task.

### Step 5 — Run

Click the Run button.

Only the selected agent and task are executed.

### Step 6 — Review

The generated report appears in the main workspace.

### Step 7 — Save

Download the generated PDF report or use the text fallback when PDF generation is unavailable.

---

## 📄 PDF Reports

Reports are generated using ReportLab.

They include:

* Report title
* Agent name
* Analysis type
* Generation timestamp
* Career request
* Job Match Score card when applicable
* Headings
* Lists
* Tables
* Markdown formatting
* Page numbers
* AI guidance disclaimer

---

## 🔒 Privacy and Security

* CV and job-description data are stored in the Streamlit session.
* The application does not use a database.
* Uploaded files are processed temporarily.
* API keys should only be stored in Streamlit Secrets or environment variables.
* Never commit API keys to GitHub.
* Information submitted for AI processing is sent to Google Gemini.

Do not submit information that you do not want processed by the selected AI service.

---

## ⚠️ Limitations

* AI-generated results should be reviewed before being used in a job application.
* Scanned/image-only PDFs may not produce usable text.
* DOCX parsing is limited by the current CV extraction implementation.
* Session data is cleared when the Streamlit session is reset.
* The Research Agent currently analyzes the text supplied by the user rather than performing live company research.
* Gemini API availability and usage limits depend on the user's Google AI Studio account.

---

## 🛠️ Troubleshooting

### Missing Gemini API key

Make sure:

```text
GEMINI_API_KEY
```

is configured in Streamlit Secrets or the environment.

### Invalid Gemini API key

Verify the key through Google AI Studio and make sure it has access to the selected model.

### Dependency errors

Run:

```bash
pip install -r requirements.txt
```

again.

### Application does not start

Check the terminal output for missing dependencies, Python compatibility issues, or configuration errors.

---

## 🚀 Deployment

The application can be deployed on Streamlit Community Cloud.

1. Push the repository to GitHub.
2. Create a Streamlit application.
3. Select `app.py` as the entry point.
4. Open **Settings → Secrets**.
5. Add:

```toml
GEMINI_API_KEY = "your_gemini_api_key"
```

6. Deploy.

No Groq or Cerebras credentials are required.

---

## 🔮 Roadmap

* DOCX CV parsing
* OCR for scanned CVs
* Live company research
* DOCX report export
* Persistent user profiles
* Application tracking
* Interactive interview simulation
* Multi-language support

---

## 📜 License

Refer to the repository's license configuration for licensing information.
