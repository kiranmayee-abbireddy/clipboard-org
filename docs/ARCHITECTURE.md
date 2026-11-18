# ClipBox System Architecture

Technical reference manual describing the process model, concurrency, storage engine, security pipeline, and packaging of the ClipBox Windows clipboard manager.

---

## 1. High-Level Process Model

ClipBox operates as a hybrid desktop utility combining native Win32 system services with a modern web rendering shell:

```
+-------------------------------------------------------------------+
|                           ClipBox Process                         |
|                                                                   |
|   +--------------------------+     +--------------------------+   |
|   |   Win32 Message Pump     |     |   PyWebView Main Window  |   |
|   |   (Background Listener)  |     |   (Edge WebView2 Shell)  |   |
|   +------------+-------------+     +------------+-------------+   |
|                |                                |                 |
|     WM_CLIPBOARDUPDATE                  JS API Bridge             |
|                v                                v                 |
|   +--------------------------+     +--------------------------+   |
|   |   Categorizer & Parser   |     |   Frontend UI Controller |   |
|   |   (Regex Token Heuristics)     |   (750ms Version Poller) |   |
|   +------------+-------------+     +------------+-------------+   |
|                |                                |                 |
|                +---------------+----------------+                 |
|                                |                                  |
|                                v                                  |
|                +-------------------------------+                  |
|                |    SQLite WAL Database Engine |                  |
|                |    (clipboard_data.db)        |                  |
|                +-------------------------------+                  |
|                                ^                                  |
|                                | (Optional Master Key)            |
|                +---------------+---------------+                  |
|                |  Fernet Cryptographic Layer   |                  |
|                |  (AES-128-CBC + HMAC-SHA256)  |                  |
|                +-------------------------------+                  |
+-------------------------------------------------------------------+
```

---

## 2. Core Subsystems

### 2.1 Native Windows Clipboard Listener (`src/backend/clipboard_service.py`)
- **Event-Driven Messaging**: Replaces high-CPU polling loops by registering a dedicated hidden Win32 window (`HWND`) with the Windows Clipboard listener chain via `AddClipboardFormatListener`.
- **Message Dispatching**: Reacts directly to `WM_CLIPBOARDUPDATE` messages delivered by the Windows subsystem.
- **Deduplication & Lock Handling**: Implements retry logic (`OpenClipboard`, `GetClipboardData`, `CloseClipboard`) to prevent crashes when competing applications hold transient clipboard locks.

### 2.2 Storage Engine (`src/backend/database.py`)
- **Engine**: SQLite 3 with Write-Ahead Logging (`PRAGMA journal_mode = WAL`).
- **Disk I/O Tuning**: `PRAGMA synchronous = NORMAL` provides fast commits without disk thrashing.
- **Table Schema**:
  - `clips` (`id`, `content`, `category`, `timestamp`, `is_pinned`, `is_encrypted`)
  - `categories` (`id`, `name`, `color`, `icon`)
- **Indexing**: Composite indexing on `(is_pinned DESC, timestamp DESC)` and `category` ensures sub-millisecond query execution even with thousands of historical records.
- **Automated Compaction**: Retains the most recent 1,000 unpinned items, auto-pruning expired entries upon database initialization.

### 2.3 Cryptographic Security (`src/backend/crypto_handler.py`)
- **Key Derivation**: Passphrases are expanded into cryptographic keys using PBKDF2 HMAC-SHA256 with 100,000 iterations and a persistent 16-byte random salt.
- **Symmetric Cipher**: Uses Fernet symmetric encryption (AES-128 in CBC mode paired with an authenticated HMAC-SHA256 signature).
- **Zero-Knowledge Inactive Memory**: Sensitive records remain encrypted on disk in `clipboard_data.db`; plain text is decrypted only on-demand during active user inspection.

### 2.4 Regex Categorization Engine (`src/backend/categorizer.py`)
Clips are automatically categorized on capture through deterministic heuristics:
- **Token / Secret**: API keys (Anthropic, OpenAI, GitHub, AWS tokens) and credentials (`is_encrypted` candidate).
- **URL**: Web links (`http://`, `https://`, domain patterns).
- **Email**: Standard RFC 5322 email patterns.
- **Phone**: Phone numbers with country prefixes (`+91`, `+1`) and strict numeric separation.
- **Code**: Programming syntax indicators (functions, control structures, class declarations, braces).
- **Text**: Fallback category for general prose and notes.

### 2.5 Modern Frontend Bridge (`src/api.py` & `src/frontend/js/app.js`)
- **Zero Heavy GUI Dependencies**: Completely decoupled from PyQt6 (~150MB bloat removed).
- **Shell**: Microsoft Edge WebView2 via PyWebView (`pywebview>=5.0.0`).
- **Versioned Polling**: Uses a lightweight monotonic version counter (`get_version()`) polling every 750ms. DOM re-rendering occurs only when clipboard state increments, eliminating visual flicker and saving GPU cycles.

---

## 3. Directory Structure

```
clipbox/
├── docs/
│   └── ARCHITECTURE.md          # Architectural and technical documentation
├── installer/
│   └── clipbox_setup.iss        # Inno Setup 6 compilation script
├── landing/
│   ├── base.css                 # Foundation resets and typography
│   ├── tokens.css               # Hallmark Rim design tokens
│   ├── style.css                # Component styling and responsive media queries
│   ├── index.html               # Main landing page
│   └── downloads/               # Compiled Inno Setup installer package
├── src/
│   ├── api.py                   # PyWebView JavaScript-Python communication bridge
│   ├── main.py                  # Application entry point and window lifecycle
│   ├── backend/
│   │   ├── categorizer.py       # Regex token and category heuristic engine
│   │   ├── clipboard_service.py # Win32 message loop listener
│   │   ├── crypto_handler.py    # PBKDF2 & Fernet AES encryption
│   │   └── database.py          # SQLite WAL storage manager
│   └── frontend/
│       ├── index.html           # Desktop application UI template
│       ├── css/                 # Desktop UI styles and themes
│       └── js/                  # App controller, theme switcher, and event bridge
├── tests/
│   └── test_backend.py          # Unit and integration test suite
├── ClipBox.spec                 # PyInstaller standalone build configuration
├── LICENSE                      # MIT Open Source License
├── README.md                    # Primary user manual and overview
└── setup.py                     # Python package configuration
```

---

## 4. Build & Distribution

- **Executable Packaging**: PyInstaller compiles the Python runtime, PyWin32 bindings, and web assets into a clean binary in `dist/ClipBox.exe`.
- **Windows Installer**: Inno Setup 6 packages `dist/ClipBox.exe` into `ClipBox-Setup-v1.2.0.exe` for per-user installation (`{autopf}\ClipBox`), desktop shortcuts, and Start Menu integration without requiring administrative privileges.
