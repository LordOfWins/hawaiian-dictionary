# 🌺 Hawaiian-English AI Dictionary

An AI-powered bilingual dictionary web app for Hawaiian and English,
built with Streamlit, Google Sheets, and the Gemini API.

Designed for a high school anthropology project exploring Hawaiian
language and culture.

---

## Features

- **Bidirectional lookup** — Hawaiian → English and English → Hawaiian
- **AI-powered responses** — Uses Google Gemini for contextual definitions,
  usage examples, and cultural notes
- **Cultural sensitivity** — Automatic disclaimers for sacred or
  culturally significant terms
- **Content filtering** — Blocked pattern detection prevents off-topic queries
  before any AI call (zero cost)
- **Password-protected access** — Simple authentication gate configurable
  via Google Sheets
- **Fully dynamic configuration** — System prompt, word categories, blocked
  patterns, and app settings are all managed in Google Sheets (no redeployment
  needed to update)
- **Streaming responses** — Real-time token-by-token output from Gemini

---

## Architecture

```
Google Sheets (4 sheets)
  ├── system_prompt      → AI behavior instructions
  ├── word_categories    → Cultural disclaimers per word
  ├── blocked_patterns   → Off-topic rejection rules
  └── config             → Password, model, app settings
        ↓
  sheets_loader.py (cached, 5-min TTL)
        ↓
  app.py (Streamlit UI)
    ├── auth.py          → Password gate
    ├── matcher.py       → Block check + disclaimer detection
    └── gemini_client.py → Gemini API streaming
```

---

## Google Sheets Structure

The app reads from a single Google Spreadsheet with 4 worksheets:

### `system_prompt`
| Column A        |
|-----------------|
| system_prompt   |
| (prompt text)   |

Row 1 is the header. Row 2 contains the full system prompt.

### `word_categories`
| word   | category | disclaimer_en                          |
|--------|----------|----------------------------------------|
| kapu   | sacred   | This term has deep cultural significance... |

### `blocked_patterns`
| pattern       | response_en                              |
|---------------|------------------------------------------|
| translate my  | This dictionary looks up individual words... |

### `config`
| key                | value                              |
|--------------------|------------------------------------|
| password           | your-password-here                 |
| model              | gemini-2.0-flash                   |
| language           | en                                 |
| max_tokens         | 1024                               |
| cache_ttl_seconds  | 300                                |
| app_title          | Hawaiian-English Dictionary        |
| app_subtitle       | A tool for high school anthropology |

---

## Setup

### Prerequisites

- Python 3.11+
- A Google Cloud Platform (GCP) project with the Google Sheets API enabled
- A GCP Service Account with read access to the spreadsheet
- A Gemini API key

### Local Development

1. **Clone the repository**

   ```bash
   git clone https://github.com/LordOfWins/hawaiian-dictionary.git
   cd hawaiian-dictionary
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # macOS/Linux
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure secrets**

   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```

   Edit `.streamlit/secrets.toml` and fill in:
   - `SPREADSHEET_URL` — your Google Sheets URL
   - `GEMINI_API_KEY` — your Gemini API key
   - `[gcp_service_account]` — paste your full service account JSON contents

5. **Share the spreadsheet**

   Share the Google Spreadsheet with your service account email
   (`client_email` from the JSON key) as a **Viewer**.

6. **Run the app**

   ```bash
   streamlit run app.py
   ```

---

## Deployment (Streamlit Community Cloud)

1. Push all code to GitHub (ensure `secrets.toml` is NOT committed)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Set the main file path to `app.py`
5. In the app settings, paste the contents of your `secrets.toml`
   into the Secrets text area
6. Deploy

---

## File Structure

```
hawaiian-dictionary/
├── .streamlit/
│   ├── config.toml              # Theme configuration
│   └── secrets.toml.example     # Secrets template (safe to commit)
├── app.py                       # Streamlit entry point
├── auth.py                      # Password authentication
├── gemini_client.py             # Gemini API client (streaming)
├── matcher.py                   # Blocked pattern + disclaimer matching
├── sheets_loader.py             # Google Sheets data loader (cached)
├── requirements.txt             # Python dependencies
├── .gitignore                   # Git ignore rules
└── README.md                    # This file
```

---

## Configuration

All runtime settings are managed in the `config` sheet of Google Sheets.
Changes take effect after the cache expires (default: 5 minutes) or when
the app is restarted.

| Key               | Description                        | Default                            |
|-------------------|------------------------------------|------------------------------------|
| password          | Access password (empty = no auth)  | —                                  |
| model             | Gemini model identifier            | gemini-2.0-flash                   |
| language          | Response language code              | en                                 |
| max_tokens        | Maximum output tokens              | 1024                               |
| cache_ttl_seconds | Sheets cache duration (seconds)    | 300                                |
| app_title         | App header title                   | Hawaiian-English Dictionary        |
| app_subtitle      | App header subtitle                | —                                  |

---

## Data Sources

This dictionary draws on the Hawaiian linguistic tradition established by
Mary Kawena Pukui and Samuel H. Elbert. The AI is instructed to provide
definitions, usage examples, and cultural context consistent with
standard Hawaiian lexicography.

---

## License

This project was built as an educational tool for a high school
anthropology project. All rights reserved by the project owner.
```

---
