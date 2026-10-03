# Career Assistant AI

An AI-powered career assistant designed to help users explore career opportunities, improve their resumes, prepare for interviews, and receive personalized career guidance using Google's Gemini models.

## Features

* **AI Career Guidance:** Get personalized career advice and recommendations.
* **Resume Assistance:** Analyze resumes and identify areas for improvement.
* **Interview Preparation:** Practice interview questions and receive AI-generated feedback.
* **Career Exploration:** Explore potential career paths based on skills and interests.
* **Multi-Agent Architecture:** Uses CrewAI to coordinate specialized AI agents.
* **Gemini Integration:** Powered by Google's Gemini models through CrewAI.
* **Interactive Interface:** Streamlit-based user interface.

## Tech Stack

* **Python**
* **Streamlit** — User interface
* **CrewAI** — Multi-agent orchestration
* **Google Gemini** — Large language models
* **LiteLLM** — LLM integration
* **Python-dotenv** — Environment configuration

## Supported Models

The application supports the following Gemini models, subject to availability in your Google AI Studio account:

| Model                 | Provider |
| --------------------- | -------- |
| Gemini 3.8 Flash      | Google   |
| Gemini 3.5 Flash-Lite | Google   |
| Gemini 2.5 Flash      | Google   |

The available models are managed through `model_manager.py`, which handles model configuration, API key validation, and LLM initialization.

## Project Structure

```text
career-assistant-ai/
│
├── app.py
├── agents.py
├── tasks.py
├── model_manager.py
├── model_ui.py
├── features.py
├── requirements.txt
├── .env.example
├── .gitignore
│
└── .streamlit/
    └── secrets.toml
```

*The structure above is indicative; retain any additional files and directories present in your repository.*

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Ghazna-Ali/career-assistant-ai.git
cd career-assistant-ai
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it:

**Windows**

```bash
venv\Scripts\activate
```

**Linux / macOS**

```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the Gemini API key

Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey).

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key
```

Alternatively, configure Streamlit Secrets by creating `.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "your_gemini_api_key"
```

Never commit API keys or other sensitive credentials to GitHub.

### 5. Run the application

```bash
streamlit run app.py
```

Open the local URL provided by Streamlit in your browser.

## Configuration

The application uses `model_manager.py` to:

* Manage the supported Gemini model catalog.
* Validate the Gemini API key.
* Select an available model.
* Initialize CrewAI LLM instances.
* Configure agents with the selected model.

Only Gemini models are configured as supported LLM options.

## Environment Variables

| Variable         | Description           |
| ---------------- | --------------------- |
| `GEMINI_API_KEY` | Google Gemini API key |

## Security

* Store API keys in environment variables or Streamlit Secrets.
* Do not expose API keys in frontend code.
* Keep `.env` and `secrets.toml` out of version control.
* Rotate credentials if they are accidentally exposed.

## Troubleshooting

**Missing Gemini API key**

Ensure that `GEMINI_API_KEY` is correctly configured in your `.env` file or Streamlit Secrets.

**Invalid API key**

Verify your key in Google AI Studio and ensure that the relevant model is available to your account.

**Dependency issues**

Install the project's dependencies again:

```bash
pip install -r requirements.txt
```

**Application fails to start**

Check the terminal output for missing dependencies, configuration errors, or Python version incompatibilities.

## Contributing

1. Fork the repository.
2. Create a feature branch.
3. Make your changes.
4. Test your changes locally.
5. Submit a pull request.

## License

Refer to the repository's license file for licensing terms.
