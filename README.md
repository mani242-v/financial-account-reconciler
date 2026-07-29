# Financial Account Reconciler ⚖️

A full-stack web application that compares Child Account financial attribution files with Parent Account benchmark data using fuzzy matching, highlights differences, and generates reconciled Word reports per account/sector.

## 🚀 Features

- **Excel Parsing & Processing**: Built with `pandas` and `openpyxl` to handle multi-header financial reports and sector groupings.
- **Fuzzy Matching**: Powered by `rapidfuzz` to match company names across portfolio and benchmark files even with minor typos or naming differences.
- **Interactive Diff Table**: Filter, search, and visually inspect field-by-field differences (weights, returns, contributions).
- **Word Report Generation**: Uses `python-docx` to populate custom `.docx` templates (`{{PLACEHOLDERS}}`) and produce downloadable reports per account/sector.
- **Job History & Storage**: SQLite database managed via `SQLAlchemy` ORM tracks every reconciliation run.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy, SQLite, Pandas, OpenPyXL, RapidFuzz, Python-Docx, Pytest
- **Frontend**: React 18, TypeScript, Vite, Axios, React Dropzone, Vanilla CSS

---

## 📦 Getting Started

### 1. Backend Setup

```bash
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
# source venv/bin/activate

pip install -r requirements.txt
python create_sample_data.py   # Generates sample Excel files
uvicorn main:app --reload --port 8000
```

Backend API will be running at `http://localhost:8000` (Interactive docs: `http://localhost:8000/docs`).

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend application will be running at `http://localhost:5173`.

---

## 🧪 Running Tests

```bash
cd backend
pytest tests/ -v
```

---

## 📄 License

MIT
