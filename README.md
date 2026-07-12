<br/>
<div align="center">
<a href="https://github.com/SarJ2004/WhatsMyNote">
<img src="https://raw.githubusercontent.com/SarJ2004/WhatsMyNote/main/docs/assets/logo.png" alt="Logo" width="80" height="80">
</a>
<h3 align="center">WhatsMyNote</h3>
<p align="center">
An intelligent, fully conversational financial memory system. Control your lending, borrowing, expenses, income, and transfers through pure natural language via CLI.
<br/>
<br/>
<a href="https://pypi.org/project/whatsmynote/">View on PyPI</a>
·
<a href="https://github.com/SarJ2004/WhatsMyNote/issues">Report Bug</a>
·
<a href="https://github.com/SarJ2004/WhatsMyNote/issues">Request Feature</a>
</p>

[![PyPI Version](https://img.shields.io/pypi/v/whatsmynote.svg)](https://pypi.org/project/whatsmynote/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Versions](https://img.shields.io/pypi/pyversions/whatsmynote.svg)](https://pypi.org/project/whatsmynote/)
[![Forks](https://img.shields.io/github/forks/SarJ2004/WhatsMyNote.svg?style=social)](https://github.com/SarJ2004/WhatsMyNote/network/members)
[![Stars](https://img.shields.io/github/stars/SarJ2004/WhatsMyNote.svg?style=social)](https://github.com/SarJ2004/WhatsMyNote/stargazers)
</div>

---

## 📑 Table of Contents
- [About The Project](#-about-the-project)
  - [Built With](#-built-with)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Usage](#-usage)
- [Local Development](#-local-development)
- [Roadmap](#-roadmap)
- [License](#-license)

---

## 🌟 About The Project

Tracking finances shouldn't require complex spreadsheets or clunky UIs. WhatsMyNote brings the power of state-of-the-art Large Language Models (LLMs) directly to your terminal. Just type what happened naturally, and the AI will extract the financial intent, validate it, and persist it to a database securely.

### 🏗 Built With
- **Python** for core logic
- **LangGraph & LangChain** for robust stateful intent routing and HITL (Human-in-the-Loop) flows
- **Pydantic** for extraction validation
- **SQLAlchemy & PostgreSQL** for data persistence
- **Groq LLMs (Llama 3)** for lightning-fast, high-quality inference
- **Supabase** for secure Authentication

---

## 🚀 Getting Started

### Prerequisites
You need Python 3.11 or higher installed on your machine.

### Installation

The recommended way to install WhatsMyNote is directly from PyPI.

```bash
pip install whatsmynote
```

That's it!

---

## 💡 Usage

After installing, simply type `whatsmynote` in your terminal to start the conversational interface!

```bash
whatsmynote
```

On your very first run, it will automatically prompt you for your `GROQ_API_KEY` and securely save it. It will also help you set up your initial budgets and accounts.

**Example Commands you can type:**
- *"I spent $15 on coffee today"*
- *"My friend John borrowed $50 from me"*
- *"Show me my expenses for this month"*
- *"Transfer $100 from Checking to Savings"*

---

## 🛠 Local Development (For Contributors)

If you'd like to contribute to the codebase or run the backend completely locally, you'll need `uv` installed.

1. Clone the repo:
   ```bash
   git clone https://github.com/SarJ2004/WhatsMyNote.git
   ```
2. Set up your environment variables:
   ```bash
   cp .env.sample .env
   ```
   *Fill in your database and API keys in `.env`.*
3. Install all dependencies (including backend AI and DB libraries):
   ```bash
   uv sync
   ```
4. Run the app:
   ```bash
   python whatsmynote/app/chat.py
   ```

---

## 🗺 Roadmap

See the [open issues](https://github.com/SarJ2004/WhatsMyNote/issues) for a list of proposed features and known issues.
See [CHANGELOG.md](CHANGELOG.md) for version history.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
