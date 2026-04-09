# End-to-End Testing with Playwright

ClimWeb uses [Playwright](https://playwright.dev/python/) via **pytest-playwright** for end-to-end (E2E) browser testing. Playwright is **free and open-source**, supports Chromium, Firefox, and WebKit, and integrates seamlessly with the existing `pytest` test suite.

---

## Why Playwright?

| Criterion | Playwright |
|-----------|-----------|
| Cost | Free & open-source (Apache 2.0) |
| Language | Python (via `pytest-playwright`) |
| Browsers | Chromium, Firefox, WebKit |
| Headless | Yes (default) |
| CI-friendly | Yes |
| Django integration | Via `conftest.py` fixture |

---

## Installation

### 1. Install Python dependencies

The `playwright` and `pytest-playwright` packages are listed in
`climweb/requirements/dev.in`.  Install them inside your virtual environment:

```bash
pip install -r climweb/requirements/dev.txt
```

### 2. Install browser binaries

Playwright downloads its own browser binaries.  Run this **once** after
installing the Python package:

```bash
playwright install
```

To install only Chromium (smallest download):

```bash
playwright install chromium
```

---

## Running the E2E tests

### Prerequisites

Before running the tests make sure:

1. The database is created and migrations have been applied:
   ```bash
   python climweb/src/climweb/manage.py migrate
   ```
2. The required environment variables are set (copy `.env.dev.sample` to `.env`
   and fill in the values).

### Run all E2E tests

```bash
pytest climweb/src/climweb/e2e_tests/ -v
```

The `conftest.py` fixture automatically starts a Django development server on
`http://127.0.0.1:8001` before the tests run and shuts it down afterwards.

### Run with a visible browser (headed mode)

```bash
pytest climweb/src/climweb/e2e_tests/ --headed
```

### Run against a specific browser

```bash
# Chromium (default)
pytest climweb/src/climweb/e2e_tests/ --browser chromium

# Firefox
pytest climweb/src/climweb/e2e_tests/ --browser firefox

# WebKit (Safari engine)
pytest climweb/src/climweb/e2e_tests/ --browser webkit
```

### Run against an already-running server

If you already have the development server running (e.g. via `docker compose`),
you can skip the auto-start fixture by setting the `SKIP_SERVER_FIXTURE`
environment variable and pointing the tests at the correct URL:

```bash
SKIP_SERVER_FIXTURE=1 pytest climweb/src/climweb/e2e_tests/ \
    --base-url http://localhost:8000
```

---

## Test structure

```
climweb/src/climweb/e2e_tests/
├── __init__.py
├── conftest.py      # Session-scoped Django server fixture
└── test_home.py     # Sample home-page and admin smoke tests
```

### Adding new tests

Create a new file `test_<feature>.py` inside `e2e_tests/` and use the
`page` fixture provided by `pytest-playwright`:

```python
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.playwright
def test_news_page_loads(page: Page):
    page.goto("http://127.0.0.1:8001/news/")
    expect(page.locator("h1")).to_be_visible()
```

---

## Configuration

Playwright settings are controlled via [`pytest.ini`](../../../../pytest.ini)
at the project root:

```ini
[pytest]
addopts = -s
markers =
    playwright: mark test as a Playwright end-to-end test

playwright_base_url = http://127.0.0.1:8001
playwright_headless = true
playwright_slow_mo = 100
```

| Option | Description |
|--------|-------------|
| `playwright_base_url` | Base URL used by `page.goto("/path")` shortcuts |
| `playwright_headless` | Run browsers without a visible window |
| `playwright_slow_mo` | Add a delay (ms) between actions for easier debugging |

---

## CI integration

Add the following steps to your CI pipeline (GitHub Actions example):

```yaml
- name: Install Python dependencies
  run: pip install -r climweb/requirements/dev.txt

- name: Install Playwright browsers
  run: playwright install --with-deps chromium

- name: Run E2E tests
  run: pytest climweb/src/climweb/e2e_tests/ -v
  env:
    DJANGO_SETTINGS_MODULE: climweb.config.settings.dev
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
```
