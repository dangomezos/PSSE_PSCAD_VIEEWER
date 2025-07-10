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


pip install -r requirements.txt

dyntools from PSSE 35 and 34 is also required, for this the default instalation of PSSE must be used
C:\Program Files\PTI\PSSE35\

Some .out files generated from PSSE v34 need to be opened with Python 2.7.
lector_out_legacy.py opens the v34 out a return the read data.

## 🛠 Built With
PyQt5: GUI framework

matplotlib: plotting library

pandas: CSV data processing

dyntools (from PSSE): to read .out files

json: to store and load templates

os, sys, subprocess: system utilities


## 🧪 Supported File Formats
.out files from PSSE (via dyntools)

.csv files from PSCAD with structured headers (first row = variable names)


## 📌 How to Use
Run PSSE_PSCAD_VIEWER.py

Drag and drop a .out or .csv file in the main window

Select variables to plot in the "+" buton

Customize appearance as needed

Save your template for future reuse


## 📝 License
This project is licensed under the MIT License – see the LICENSE file for details.
