# Quick Testing Guide

## Option 1: Using Poetry (Recommended)

Poetry automatically manages virtual environments - no need to manually create one!

### Install Poetry

**Method A: Using Homebrew (Easiest on macOS)**
```bash
brew install poetry
```

**Method B: Using pip (If Homebrew fails)**
```bash
pip3 install poetry
```

**Method C: Official Installer (If SSL issues occur)**
```bash
# First, install certificates (if needed)
/Applications/Python\ 3.12/Install\ Certificates.command

# Then try again
curl -sSL https://install.python-poetry.org | python3 -
```

If you get SSL errors, use Method A or B instead!

### Test Your Project

```bash
# 1. Install dependencies (creates venv automatically)
poetry install

# 2. Run tests
poetry run pytest

# 3. Initialize config
poetry run humancheck init

# 4. Start the platform
poetry run humancheck start
```

That's it! Poetry handles everything.

---

## Option 2: Using pip + venv (If you prefer)

```bash
# 1. Create virtual environment
python3 -m venv venv

# 2. Activate it
source venv/bin/activate

# 3. Install in editable mode
pip install -e .

# 4. Install dev dependencies
pip install pytest pytest-asyncio black ruff mypy

# 5. Run tests
pytest

# 6. Test CLI
humancheck init
humancheck start
```

---

## Quick Test Commands

Once set up (either method):

```bash
# Run tests
poetry run pytest  # or: pytest (if venv activated)

# Check status
poetry run humancheck status  # or: humancheck status

# Start platform
poetry run humancheck start  # or: humancheck start

# Test API (in another terminal)
curl http://localhost:8000/docs
```

