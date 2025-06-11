# GUI lógica (Python)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, 
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTabWidget, QFileDialog, QMessageBox, QInputDialog)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import sys, os
import psse35
import dyntools as dy
import pandas as pd

# Simulación de lectura de canales desde archivo .out (para demostración)
def get_channels_from_out(filepath):
    channels = []
    try:
        chnfobj = dy.CHNF(filepath)
        _, ch_id_dict, _ = chnfobj.get_data()
        channels = list(ch_id_dict.values())
    except Exception as e:
        print(f"Error leyendo canales con dyntools desde {filepath}: {e}")
    return channels

from PyQt5.QtWidgets import QSplitter, QLabel
class DropTreeWidget(QTreeWidget):
    def __init__(self, parent=None, accept_csv=False):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.accept_csv = accept_csv

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                filepath = url.toLocalFile()
                if (filepath.endswith('.out')) or (filepath.endswith('.csv')):
                    item = QTreeWidgetItem([os.path.basename(filepath)])
                    item.setToolTip(0, filepath)
                    self.addTopLevelItem(item)
        event.accept()

class PlotTab(QWidget):
    def close_tab(self):
        if self.close_callback:
            self.close_callback(self)
    def __init__(self, parent=None, close_callback=None, get_file_list_callback=None):
        super().__init__(parent)
        self.close_callback = close_callback
        self.get_file_list_callback = get_file_list_callback
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(10, 5, 10, 5)
        button_layout = QHBoxLayout()
        self.btn_add = QPushButton("Agregar gráfico")
        self.btn_add.clicked.connect(self.add_plot)
        self.btn_close = QPushButton("Cerrar pestaña")
        self.btn_close.clicked.connect(self.close_tab)
        button_layout.addWidget(self.btn_add)
        button_layout.addWidget(self.btn_close)

        self.layout.addLayout(button_layout)
        


    def add_plot(self):
        if not self.get_file_list_callback:
            return
        files = self.get_file_list_callback()
        if not files:
            QMessageBox.information(self, "Sin archivos", "No hay archivos .out cargados.")
            return

        file, ok = QInputDialog.getItem(self, "Seleccionar archivo .out", "Archivo:", files, 0, False)
        if not ok:
            return

        channels = get_channels_from_out(file)
        channel, ok = QInputDialog.getItem(self, "Seleccionar canal", "Canal:", channels, 0, False)
        if not ok:
            return

        canvas = FigureCanvas(Figure(figsize=(5, 3)))
        ax = canvas.figure.add_subplot(111)
        chnfobj = dy.CHNF(file)
        data = chnfobj.get_data()
        # time = data[0]
        ch_id = data[1]
        ch_data = data[2]
        time = data[2]['time']
        
        # print(f'El tiempo es: {time}')


        # Buscar el canal seleccionado
        for key, name in ch_id.items():
            if name == channel:
                values = ch_data[key]
                ax.plot(time, values, label=channel)
                # break
                ax.set_title(channel)
                ax.legend()
                self.layout.addWidget(canvas)
                break

# === NUEVA CLASE PARA DIVISIÓN DE ÁRBOLES ===
class DualDropWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        label_psse = QLabel("Archivos .out PSSE")
        self.tree_psse = DropTreeWidget()
        self.tree_psse.setHeaderLabel("PSSE")

        label_pscad = QLabel("Archivos .csv PSCAD")
        self.tree_pscad = DropTreeWidget()
        self.tree_pscad.setHeaderLabel("PSCAD")

        layout.addWidget(label_psse)
        layout.addWidget(self.tree_psse)
        layout.addWidget(label_pscad)
        layout.addWidget(self.tree_pscad)

    def get_all_files(self):
        files = []
        for tree in [self.tree_psse, self.tree_pscad]:
            for i in range(tree.topLevelItemCount()):
                item = tree.topLevelItem(i)
                files.append(item.toolTip(0))
        return files
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PSSE .out Visualizador")
        self.resize(1200, 700)

        # Panel izquierdo: archivos divididos
        self.dual_tree = DualDropWidget()

        # Zona de pestañas
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(False)

        # Botón para agregar nueva pestaña
        self.btn_new_tab = QPushButton("+ Nueva pestaña")
        self.btn_new_tab.clicked.connect(self.add_new_tab)

        top_layout = QVBoxLayout()
        top_layout.addWidget(self.btn_new_tab)
        top_layout.addWidget(self.tabs)

        tabs_widget = QWidget()
        tabs_widget.setLayout(top_layout)

        # Diseño principal
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(self.dual_tree, 2)
        layout.addWidget(tabs_widget, 8)

        self.setCentralWidget(central)

        # Agrega la primera pestaña
        self.add_new_tab()

    def get_loaded_files(self):
        return self.dual_tree.get_all_files()

    def add_new_tab(self):
        tab = PlotTab(close_callback=self.remove_tab, get_file_list_callback=self.get_loaded_files)
        index = self.tabs.addTab(tab, f"Gráfico {self.tabs.count() + 1}")
        self.tabs.setCurrentIndex(index)

    def remove_tab(self, tab_widget):
        index = self.tabs.indexOf(tab_widget)
        if index != -1:
            self.tabs.removeTab(index)
            
    def add_new_tab(self):
        tab = PlotTab(close_callback=self.remove_tab, get_file_list_callback=self.get_loaded_files)
        index = self.tabs.addTab(tab, f"Gráfico {self.tabs.count() + 1}")
        self.tabs.setCurrentIndex(index)

    def remove_tab(self, tab_widget):
        index = self.tabs.indexOf(tab_widget)
        if index != -1:
            self.tabs.removeTab(index)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

