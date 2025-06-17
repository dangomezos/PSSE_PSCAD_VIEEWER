# PSSE_PSCAD_VIEWER

**PSSE_PSCAD_VIEWER** is a desktop application developed in Python that enables fast and interactive visualization of simulation results from **PSS®E (.out)** and **PSCAD (.csv)** files. Its graphical user interface is designed to simplify the analysis and comparison of dynamic simulations in power systems.

---

## 🚀 Main Features

- 📂 **Load simulation files**: `.out` (PSSE) and `.csv` (PSCAD)
- 📊 **Visualize dynamic variables** with interactive plots
- 🔍 **Select variables dynamically** per tab or file
- 🗂️ **Multi-tab interface** for managing multiple plots simultaneously
- ♻️ **Auto-refresh plots** when files are reloaded or updated
- 💾 **Save/load templates** to preserve and reuse graph configurations
- 🎨 **Customize plot appearance**: colors, line styles, variable labels

---

## 📦 Requirements

Python 3.9.13

Install dependencies:

```bash
pip install -r requirements.txt

dyntools from PSSE 35 and 34 is also required

Some .out files generated from PSSE v34 need to be opened with Python 2.7.
lector_out_legacy.py opens the v34 out a return the read data.