# GUI lógica (Python)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, 
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTabWidget, QFileDialog, QMessageBox, QInputDialog, 
    QDialog, QFormLayout, QLineEdit, QListWidget, QListWidgetItem, QDialogButtonBox, QColorDialog, QCheckBox)
from PyQt5.QtGui import QColor

from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import sys, os
import psse35
import dyntools as dy
import pandas as pd
import subprocess
import json

# Simulación de lectura de canales desde archivo .out

def get_channel_data_from_out(filepath, channel_name):
    
    try:
        chnfobj = dy.CHNF(filepath)
        short_title, ch_id, ch_data = chnfobj.get_data()
        time = ch_data['time']
        for key, name in ch_id.items():
            if name == channel_name:
                return time, ch_data[key]
    except Exception as e:
        print(f"[WARN] Falló dyntools moderno: {e}")
        print("[INFO] Intentando con Python 2.7 para extraer datos...")

        # import subprocess, json
        result = subprocess.run(
            ['C:/Python27/python.exe', 'lector_out_legacy.py', filepath, channel_name],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            parsed = json.loads(result.stdout)
            return parsed["time"], parsed["valores"]
        else:
            print(f"[ERROR] Fallback falló: {result.stderr}")
            return [], []


def get_channels_from_out(filepath):
    channels = []
    try:
        chnfobj = dy.CHNF(filepath)
        _, ch_id_dict, _ = chnfobj.get_data()
        channels = list(ch_id_dict.values())
    except Exception as e:
        print(f"[WARN] Falló lectura con dyntools moderno: {e}")
        print("[INFO] Intentando fallback con Python 2.7...")

        # Fallback: ejecuta script de lectura en Python 2.7
        try:
            result = subprocess.run(
                ['C:/Python27/python.exe', 'lector_out_legacy.py', filepath],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                parsed = json.loads(result.stdout)
                channels = parsed.get("canales", {}).values()
                print("[INFO] Lectura con Python 2.7 exitosa.")
            else:
                print(f"[ERROR] Python 2.7 falló: {result.stderr}")
        except Exception as ex:
            print(f"[ERROR] Fallback Python 2.7 no ejecutado correctamente: {ex}")
    
    return list(channels)

def get_channels_from_csv(filepath):
    try:
        df = pd.read_csv(filepath)
        return list(df.columns[1:])  # Ignora la primera columna (tiempo)
    except Exception as e:
        print(f"Error leyendo CSV: {e}")
        return []

def get_time_and_data_from_csv(filepath, column, init_time = 2):
    try:
        df = pd.read_csv(filepath)
        df = df[df.iloc[:, 0] >= init_time].copy()
        df.iloc[:, 0] -= init_time
        return df.iloc[:, 0], df[column]  # Primera columna es tiempo
    except Exception as e:
        print(f"Error leyendo datos de CSV: {e}")
        return [], []

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
                if (filepath.endswith('.out')) or (filepath.endswith('.csv')):
                    item = QTreeWidgetItem([os.path.basename(filepath)])
                    item.setToolTip(0, filepath)
                    self.addTopLevelItem(item)
        event.accept()

class PlotCanvas(QWidget):
    def __init__(self, get_file_list_callback):
        super().__init__()
        self.get_file_list_callback = get_file_list_callback
        layout = QHBoxLayout(self)

        self.canvas = FigureCanvas(Figure(figsize=(5, 3)))
        self.canvas.setFocusPolicy(Qt.ClickFocus)
        self.canvas.setFocus()
        self.ax = self.canvas.figure.add_subplot(111)

        canvas_container = QVBoxLayout()
        canvas_container.addWidget(self.canvas)
        canvas_widget = QWidget()
        canvas_widget.setLayout(canvas_container)

        layout.addWidget(canvas_widget)

        self.btn_add_channel = QPushButton("+")
        self.btn_add_channel.setFixedSize(25, 25)
        self.btn_add_channel.setToolTip("Agregar canal")
        self.btn_add_channel.clicked.connect(self.add_channel)

        self.btn_edit_title = QPushButton("🖉")
        self.btn_edit_title.setFixedSize(25, 25)
        self.btn_edit_title.setToolTip("Editar título")
        self.btn_edit_title.clicked.connect(self.edit_title)

        self.btn_reset_zoom = QPushButton("🔄")
        self.btn_reset_zoom.setFixedSize(25, 25)
        self.btn_reset_zoom.setToolTip("Restablecer zoom")
        self.btn_reset_zoom.clicked.connect(self.reset_zoom)

        self.btn_clear = QPushButton("✕")
        self.btn_clear.setFixedSize(25, 25)
        self.btn_clear.setToolTip("Limpiar gráfica")
        self.btn_clear.clicked.connect(self.clear_plot)

        btn_container = QVBoxLayout()
        btn_container.setContentsMargins(0, 20, 0, 0)
        btn_container.setSpacing(0)
        btn_container.addWidget(self.btn_add_channel, alignment=Qt.AlignTop | Qt.AlignHCenter)
        btn_container.addWidget(self.btn_edit_title, alignment=Qt.AlignTop | Qt.AlignHCenter)
        btn_container.addWidget(self.btn_reset_zoom, alignment=Qt.AlignTop | Qt.AlignHCenter)
        btn_container.addWidget(self.btn_clear, alignment=Qt.AlignTop | Qt.AlignHCenter)

        btn_widget = QWidget()
        btn_widget.setLayout(btn_container)
        btn_widget.setFixedWidth(30)

        layout.addWidget(btn_widget)

    def add_channel(self):
        if not self.get_file_list_callback:
            return
        files = self.get_file_list_callback()
        if not files:
            QMessageBox.information(self, "Sin archivos", "No hay archivos cargados.")
            return

        file, ok = QInputDialog.getItem(self, "Seleccionar archivo", "Archivo:", files, 0, False)
        if not ok:
            return

        if file.endswith(".out"):
            channels = get_channels_from_out(file)
        elif file.endswith(".csv"):
            channels = get_channels_from_csv(file)
        else:
            QMessageBox.warning(self, "Archivo inválido", "El archivo debe ser .out o .csv")
            return

        channel, ok = QInputDialog.getItem(self, "Seleccionar canal", "Canal:", channels, 0, False)
        if not ok:
            return

        new_label, ok = QInputDialog.getText(self, "Etiqueta de canal", f"Etiqueta para '{channel}':", text=channel)
        if not ok:
            return

        if file.endswith(".out"):
            time, values = get_channel_data_from_out(file, channel)
            if not time or not values:
                QMessageBox.warning(self, "Error", "No se pudieron extraer datos del canal.")
                return
            self.ax.plot(time, values, label=new_label)
            self.ax.set_xlabel('(s)', horizontalalignment='right', x=1.0)
        else:
            init_time, ok = QInputDialog.getDouble(self, "Tiempo de inicialización", "Ignorar tiempo menor a:", 0.0, 0)
            if not ok:
                return
            time, values = get_time_and_data_from_csv(file, channel, init_time = init_time)
            self.ax.plot(time, values, label=new_label)
            self.ax.set_xlabel('(s)', horizontalalignment='right', x=1.0)

        # self.ax.set_title("Channel plot")
        self.ax.legend().set_picker(True)
        self.canvas.mpl_connect("pick_event", self.on_pick_legend)
        self.canvas.mpl_connect("scroll_event", self.on_scroll)
        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_drag)
        self.canvas.mpl_connect("button_press_event", self.on_mouse_press)
        self.canvas.mpl_connect("button_release_event", self.on_mouse_release)
        self._last_mouse_pos = None
        self.canvas.draw()

    def edit_title(self):
        current_title = self.ax.get_title()
        current_xlabel = self.ax.get_xlabel()
        current_ylabel = self.ax.get_ylabel()
        lines = self.ax.get_lines()
        current_labels = [line.get_label() for line in lines]
        current_colors = [line.get_color() for line in lines]
        grid_enabled = self.ax.xaxis._major_tick_kw.get('gridOn', False) and self.ax.yaxis._major_tick_kw.get('gridOn', False)

        dialog = EditLabelsDialog(current_title, current_xlabel, current_ylabel, current_labels, current_colors, grid_enabled, self)
        if dialog.exec_():
            new_title, new_xlabel, new_ylabel, new_labels, new_colors, grid_enabled = dialog.get_data()
            self.ax.set_title(new_title)
            self.ax.set_xlabel(new_xlabel, horizontalalignment='right', x=1.0)
            self.ax.set_ylabel(new_ylabel)
            self.ax.grid(grid_enabled)

            for line, new_label, new_color in zip(lines, new_labels, new_colors):
                line.set_label(new_label)
                line.set_color(new_color)

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
        button_layout = QHBoxLayout()
        self.btn_add_plot = QPushButton("Agregar gráfico")
        self.btn_add_plot.clicked.connect(self.add_plot_canvas)
        self.btn_close = QPushButton("Cerrar pestaña")
        self.btn_close.clicked.connect(self.close_tab)
        button_layout.addWidget(self.btn_add_plot)
        button_layout.addWidget(self.btn_close)

        self.layout.addLayout(button_layout)

    def add_plot_canvas(self):
        plot_canvas = PlotCanvas(self.get_file_list_callback)
        self.layout.addWidget(plot_canvas)

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
    
class EditLabelsDialog(QDialog):
    def __init__(self, current_title, current_xlabel, current_ylabel, line_labels, line_colors, grid_enabled=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar etiquetas del gráfico")

        self.title_edit = QLineEdit(current_title)
        self.xlabel_edit = QLineEdit(current_xlabel if current_xlabel else "(s)")
        self.ylabel_edit = QLineEdit(current_ylabel)

        self.legends_list = QListWidget()
        self.color_map = {}

        for label, color in zip(line_labels, line_colors):
            item = QListWidgetItem(label)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            item.setBackground(QColor(color))
            self.legends_list.addItem(item)
            self.color_map[label] = color

        self.legends_list.itemDoubleClicked.connect(self.change_color)

        self.grid_checkbox = QCheckBox("Mostrar grilla")
        self.grid_checkbox.setChecked(bool(grid_enabled))

        layout = QFormLayout(self)
        layout.addRow("Título del gráfico:", self.title_edit)
        layout.addRow("Etiqueta eje X:", self.xlabel_edit)
        layout.addRow("Etiqueta eje Y:", self.ylabel_edit)

        list_container = QHBoxLayout()
        list_widget = QWidget()
        list_widget.setLayout(list_container)
        list_container.addWidget(self.legends_list)
        layout.addRow("Leyendas (doble clic para cambiar color):", list_widget)
        
        layout.addRow(self.grid_checkbox)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def change_color(self, item):
        current_color = item.background().color()
        new_color = QColorDialog.getColor(current_color, self, "Seleccionar color")
        if new_color.isValid():
            item.setBackground(new_color)

    def get_data(self):
        labels = [self.legends_list.item(i).text() for i in range(self.legends_list.count())]
        colors = [self.legends_list.item(i).background().color().name() for i in range(self.legends_list.count())]
        return self.title_edit.text(), self.xlabel_edit.text(), self.ylabel_edit.text(), labels, colors, self.grid_checkbox.isChecked()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PSSE/PSCAD ViEEwer")
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
