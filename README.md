# Dhivehi Translation Arena

A blind testing platform for comparing Arabic to Dhivehi translations across different LLM models:
- Gemini 2.0 Flash 
- Gemini 2.0 Pro Experimental
- Sonnet 3.7 (via OpenRoute API)

## Features

- Blind testing of translations from Arabic to Dhivehi
- Voting system to select the best translation
- Pre-selected test queries and custom query input
- Cost tracking for API calls
- Storage of translations and votes for later analysis

## Setup

1. Clone this repository
2. Set up your environment variables in a `.env` file:
   ```
   GEMINI_API_KEY=your_gemini_api_key
   OPENROUTE_API_KEY=your_openroute_api_key
   ```
3. Install dependencies using uv:
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -e .
   ```
4. Run the application:
   ```bash
   flask run
   ```

## Data Storage

All translations and votes are stored in a SQLite database located in the `data` directory.

## License

MIT
