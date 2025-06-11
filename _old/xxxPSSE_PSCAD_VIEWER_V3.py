# GUI lógica (Python)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, 
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTabWidget, QFileDialog, QMessageBox, QInputDialog, QSizePolicy)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import sys, os
import psse35
import dyntools as dy
import pandas as pd

# Simulación de lectura de canales desde archivo .out
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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

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
                if filepath.endswith('.out'):
                    item = QTreeWidgetItem([os.path.basename(filepath)])
                    item.setToolTip(0, filepath)
                    self.addTopLevelItem(item)
        event.accept()

class PlotCanvas(QWidget):
    def __init__(self, get_file_list_callback, ax, canvas):
        super().__init__()
        self.get_file_list_callback = get_file_list_callback
        self.ax = ax
        self.canvas = canvas
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        plot_area = QWidget()
        canvas_container = QVBoxLayout()
        canvas_container.setContentsMargins(0, 0, 0, 0)
        canvas_container.setSpacing(0)
        canvas_container.addWidget(self.canvas)
        plot_area.setLayout(canvas_container)
        layout.addWidget(plot_area, stretch=1)

        # Crear botones antes de usarlos
        self.btn_add_channel = QPushButton("+")
        self.btn_add_channel.setFixedSize(25, 25)
        self.btn_add_channel.setToolTip("Agregar canal")
        self.btn_add_channel.clicked.connect(self.add_channel)

        self.btn_reset_zoom = QPushButton("🔄")
        self.btn_reset_zoom.setFixedSize(25, 25)
        self.btn_reset_zoom.setToolTip("Restablecer zoom")
        self.btn_reset_zoom.clicked.connect(self.reset_zoom)

        self.btn_clear = QPushButton("✕")
        self.btn_clear.setFixedSize(25, 25)
        self.btn_clear.setToolTip("Limpiar gráfica")
        self.btn_clear.clicked.connect(self.clear_plot)

        controls_layout = QVBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(5)
        controls_layout.addWidget(self.btn_add_channel)
        controls_layout.addWidget(self.btn_reset_zoom)
        controls_layout.addWidget(self.btn_clear)

        btn_widget = QWidget()
        btn_widget.setLayout(controls_layout)
        btn_widget.setFixedWidth(35)

        layout.addWidget(btn_widget, alignment=Qt.AlignTop)

        self.canvas.mpl_connect("pick_event", self.on_pick_legend)
        self.canvas.mpl_connect("scroll_event", self.on_scroll)
        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_drag)
        self.canvas.mpl_connect("button_press_event", self.on_mouse_press)
        self.canvas.mpl_connect("button_release_event", self.on_mouse_release)
        self._last_mouse_pos = None

    def add_channel(self):
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

        chnfobj = dy.CHNF(file)
        data = chnfobj.get_data()
        time = data[2]['time']
        ch_id = data[1]
        ch_data = data[2]

        for key, name in ch_id.items():
            if name == channel:
                values = ch_data[key]
                self.ax.plot(time, values, label=channel)
                break

        self.ax.set_title("Channel plot")
        self.ax.legend().set_picker(True)
        self.canvas.draw()

    def reset_zoom(self):
        self.ax.autoscale()
        self.canvas.draw()

    def clear_plot(self):
        self.ax.clear()
        self.ax.set_title("")
        self.canvas.draw()

    def on_mouse_press(self, event):
        if event.button == 1:
            self._drag_start = (event.x, event.y)
            self._drag_xlim = self.ax.get_xlim()
            self._drag_ylim = self.ax.get_ylim()

    def on_mouse_release(self, event):
        if event.button == 1:
            self._drag_start = None

    def on_mouse_drag(self, event):
        if hasattr(self, '_drag_start') and self._drag_start and event.button == 1:
            dx = event.x - self._drag_start[0]
            dy = event.y - self._drag_start[1]

            ax = self.ax
            x0, x1 = self._drag_xlim
            y0, y1 = self._drag_ylim

            scale_x = (x1 - x0) / self.canvas.width()
            scale_y = (y1 - y0) / self.canvas.height()

            ax.set_xlim(x0 - dx * scale_x, x1 - dx * scale_x)
            ax.set_ylim(y0 + dy * scale_y, y1 + dy * scale_y)
            self.canvas.draw()
            return

        if event.button == 3 and event.xdata and event.ydata:
            if not self._last_mouse_pos:
                self._last_mouse_pos = (event.x, event.y)
                return

            dx = event.x - self._last_mouse_pos[0]
            dy = event.y - self._last_mouse_pos[1]
            ax = self.ax

            if abs(dx) > abs(dy):
                factor = 1.1 if dx < 0 else 0.9
                xlim = ax.get_xlim()
                center = (xlim[0] + xlim[1]) / 2
                width = (xlim[1] - xlim[0]) * factor
                ax.set_xlim(center - width / 2, center + width / 2)
            else:
                factor = 1.1 if dy > 0 else 0.9
                ylim = ax.get_ylim()
                center = (ylim[0] + ylim[1]) / 2
                height = (ylim[1] - ylim[0]) * factor
                ax.set_ylim(center - height / 2, center + height / 2)

            self.canvas.draw()
            self._last_mouse_pos = (event.x, event.y)
        else:
            self._last_mouse_pos = None

    def on_scroll(self, event):
        base_scale = 1.2
        ax = self.ax
        x_min, x_max = ax.get_xlim()
        y_min, y_max = ax.get_ylim()
        xdata = event.xdata
        ydata = event.ydata

        if event.button == 'up':
            scale_factor = 1 / base_scale
        elif event.button == 'down':
            scale_factor = base_scale
        else:
            scale_factor = 1

        new_width = (x_max - x_min) * scale_factor
        new_height = (y_max - y_min) * scale_factor
        relx = (xdata - x_min) / (x_max - x_min)
        rely = (ydata - y_min) / (y_max - y_min)

        ax.set_xlim([xdata - new_width * relx, xdata + new_width * (1 - relx)])
        ax.set_ylim([ydata - new_height * rely, ydata + new_height * (1 - rely)])
        self.canvas.draw()

    def on_pick_legend(self, event):
        legend_line = event.artist
        label = legend_line.get_label()
        for line in self.ax.get_lines():
            if line.get_label() == label:
                visible = not line.get_visible()
                line.set_visible(visible)
                legend_line.set_alpha(1.0 if visible else 0.2)
        self.canvas.draw()

class PlotTab(QWidget):
    def __init__(self, parent=None, close_callback=None, get_file_list_callback=None):
        super().__init__(parent)
        self.close_callback = close_callback
        self.get_file_list_callback = get_file_list_callback
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(10, 5, 10, 5)
        self.figure = Figure(figsize=(5, 3), constrained_layout=True)
        self.subplot_count = 0

        button_layout = QHBoxLayout()
        self.btn_add_plot = QPushButton("Agregar gráfico")
        self.btn_add_plot.clicked.connect(self.add_plot_canvas)
        self.btn_close = QPushButton("Cerrar pestaña")
        self.btn_close.clicked.connect(self.close_tab)
        button_layout.addWidget(self.btn_add_plot)
        button_layout.addWidget(self.btn_close)

        self.layout.addLayout(button_layout)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas_container = QVBoxLayout()
        self.canvas_container.setContentsMargins(0, 0, 0, 0)
        self.canvas_container.setSpacing(0)
        self.canvas_container.addWidget(self.canvas)
        canvas_widget = QWidget()
        canvas_widget.setLayout(self.canvas_container)
        canvas_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.layout.addWidget(canvas_widget)

    def add_plot_canvas(self):
        self.subplot_count += 1
        ax = self.figure.add_subplot(self.subplot_count, 1, self.subplot_count)
        plot_controls = PlotCanvas(self.get_file_list_callback, ax, self.canvas)
        self.layout.addWidget(plot_controls, alignment=Qt.AlignTop)

    def close_tab(self):
        if self.close_callback:
            self.close_callback(self)

class DualDropWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        label_psse = QLabel("Archivos .out PSSE")
        self.tree_psse = DropTreeWidget()
        self.tree_psse.setHeaderLabel("PSSE")

        label_pscad = QLabel("Archivos .out PSCAD")
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

        self.dual_tree = DualDropWidget()

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(False)

        self.btn_new_tab = QPushButton("+ Nueva pestaña")
        self.btn_new_tab.clicked.connect(self.add_new_tab)

        top_layout = QVBoxLayout()
        top_layout.addWidget(self.btn_new_tab)
        top_layout.addWidget(self.tabs)

        tabs_widget = QWidget()
        tabs_widget.setLayout(top_layout)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(self.dual_tree, 2)
        layout.addWidget(tabs_widget, 8)

        self.setCentralWidget(central)

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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())