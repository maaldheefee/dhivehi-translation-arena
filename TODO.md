# TODO

## High Priority
- [ ] **User Management**: Add user management features to the app.
  Currently, runing the manage_users.py script inside the container results in the following error:

    --- Remove User ---
    Enter username to remove: John
    Are you sure you want to remove user 'John'? (y/n): y
    /bin/sh: 1: uv: not found
    Error running command: Command 'uv run --python 3.13 flask remove-user John' returned non-zero exit status 127.

  This kind of user management is okay for now, but we should document it.

- [ ] **UI Polish & Translation**: Polish the entire UI. Translate any untranslated bits to Dhivehi/English as appropriate.
- [ ] **Rating Tips**: Add qualitative tips for rating stars to guide users:
    - **Trash**: Illegible, glitch characters, or wrong meaning.
    - **1 Star**: Understandable but with some errors.
    - **2 Stars**: Correct meaning, but needs some editing.
    - **3 Stars**: Excellent translation, no further editing required.

## Backlog / Improvements
- [ ] **Database Concurrency**: Identify whether the current SQLite DB is suitable for multiple access (e.g., prod and dev containers running simultaneously).
- [ ] **Refactoring**: Refactor the entire app for better architecture, code quality, and consistency.

## Completed
- [x] **User Management**: Implemented `flask add-user`, `flask remove-user` CLI commands, and `manage_users.py` script.
- [x] **LLM Integration**: Added Gemini 3 Pro and Claude Opus 4.5 via OpenRouter. Implemented model presets (temperature, reasoning budget).
- [x] **Environment Config**: Used ENV variables for paths and secrets. Updated Docker and Justfile for dev/prod parity.
- [x] **CI/CD**: Added GitHub Action for Docker build and volume mounts in `compose.yml`.
- [x] **Frontend Model Selection**: Limit display to 6 models max, prioritizing those with fewer usage data points.
- [x] **Stats Improvements**: Added "Projected Cost (100k words)" and "Bang for Buck" metrics to stats page.
- [x] **Error Handling**: Improved LLM error handling (timeouts, max tokens). Allowed voting on successful responses even if some models fail.
- [x] **Cleanup**: Removed native Gemini Client in favor of unified OpenRouter client.