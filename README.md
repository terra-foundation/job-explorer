
# 🚀 Job SERP Explorer

**Find jobs. Parse meaningfully. Apply strategically.**

Job SERP Explorer is an open-source tool for efficient, semi-automated job search. Instead of manually skimming dozens of job boards, this tool helps you **search, extract, rank, and organize** job listings — tailored to your preferences. You can even edit how job postings are triaged for you and evaluated, with an intuitive interface and editable prompt logic.

---

## 🔍 What It Solves

Manual job search is noisy, fragmented, and time-consuming. This tool lets you:

- Run intelligent searches (e.g. "Data Scientist" in "Remote" or "Germany")
- Parse job ads and extract structured data (title, company, visa info, etc.)
- Apply AI scoring with **custom rules & prompt templates**
- View tables of top-matching jobs and actionable application URLs
- Re-run, edit, and refine past searches anytime

---

## 📦 Live Demo

> 🔗 [Streamlit Cloud Demo](https://your-link.streamlit.app)  
> or  
> 💻 Run locally: see setup below

---

## 🛠 Quickstart: Run Locally

### 1. Clone and install

```bash
git clone https://github.com/yourname/jobserp-explorer.git
cd jobserp-explorer
pip install -e .
````

(Use a Python 3.9+ virtual environment)

### 2. Launch the app

```bash
streamlit run jobserp_explorer/app.py
```

Then open: [http://localhost:8501](http://localhost:8501)

---

## 🧠 Custom Prompts & Parsers

This tool gives you **full control** over what is extracted and how it's scored.

### Editable schema parser

* Navigate to `🔧 Schema Editor`
* Modify or extend what fields get extracted (e.g., visa info, remote policy, stack)

### Prompt customization

* Navigate to `✍️ Prompt Editor`
* Tailor the job evaluation criteria (e.g., mission alignment, tech fit, location)

You’re not locked into fixed logic — you define what “a good job” means for you.

---

## 🗂 Folder Structure

```
jobserp_explorer/
├── core/                      # CLI pipelines
├── data/                      # Run outputs
├── prompts/                  # Prompt templates
├── schemas/                  # Parsing schemas
├── app.py                    # Main Streamlit UI
└── ...
```

---

## 🤝 Contributing

We welcome contributions from job seekers, developers, and prompt engineers.

* 🧪 Check the **Issues** tab for `good-first-issue`
* 🧠 Suggest new schema fields or scoring prompts
* 🧼 Improve UI layout or add new data sources

### Local development

```bash
pip install -e ".[dev]"
pre-commit install
```


---

Made with ❤️ by matuteiglesias
🧭 *“Automate the boring. Apply where it counts.”*

