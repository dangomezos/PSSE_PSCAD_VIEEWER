# GUI lógica (Python)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem, 
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTabWidget, QFileDialog, QMessageBox, QInputDialog, 
    QDialog, QFormLayout, QLineEdit, QListWidget, QListWidgetItem, QDialogButtonBox, QColorDialog, QCheckBox, QStatusBar, QDoubleSpinBox)
from PyQt5.QtGui import QColor, QIcon

from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import os
import sys, os
import psse35
import dyntools as dy
import pandas as pd
import subprocess
import json


__version__ = "1.0.0"

# Simulación de lectura de canales desde archivo .out
def get_channel_data_from_out(filepath, channel_name):
    # Read .OUT and extract time and data for a specific column
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
    # Read .OUT and extract time and data for a specific column
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
    # Read CSV and extract time and data for a specific column
    try:
        df = pd.read_csv(filepath)
        return list(df.columns[1:])  # Ignora la primera columna (tiempo)
    except Exception as e:
        print(f"Error leyendo CSV: {e}")
        return []

def get_time_and_data_from_csv(filepath, column, init_time = 2):
    # Read CSV and extract time and data for a specific column
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
        # Allow dragging files into the tree
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        # Allow dragging files over the tree
        event.accept()

    def dropEvent(self, event):
        # drop files into the tree
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                filepath = url.toLocalFile()
                if (filepath.endswith('.out')) or (filepath.endswith('.csv')):
                    item = QTreeWidgetItem([os.path.basename(filepath)])
                    item.setToolTip(0, filepath)
                    self.addTopLevelItem(item)
        event.accept()

class PlotCanvas(QWidget):
    def __init__(self, get_file_list_callback, status_callback=None, parent_tab=None):
        super().__init__()
        self.get_file_list_callback = get_file_list_callback
        self.status_callback = status_callback
        self.parent_tab = parent_tab
        layout = QHBoxLayout(self)
        layout.setSpacing(2)  # Reduce espacio entre canvas y botones
        layout.setContentsMargins(0, 0, 0, 0)  # Elimina márgenes alrededor del layout
        self.synchronizing = False

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
        self.btn_edit_title.setToolTip("Editar gráfico")
        self.btn_edit_title.clicked.connect(self.edit_title)

        self.btn_reset_zoom = QPushButton("🔄")
        self.btn_reset_zoom.setFixedSize(25, 25)
        self.btn_reset_zoom.setToolTip("Restablecer zoom")
        self.btn_reset_zoom.clicked.connect(self.reset_zoom)

        self.btn_clear = QPushButton("✕")
        self.btn_clear.setFixedSize(25, 25)
        self.btn_clear.setToolTip("Limpiar gráfica")
        self.btn_clear.clicked.connect(self.clear_plot)
        
        self.btn_delete = QPushButton('🗑')
        # self.btn_delete.setIcon(QIcon.fromTheme("edit-delete"))  # Usa ícono del sistema, podés usar texto o path a imagen
        self.btn_delete.setFixedSize(25, 25)
        self.btn_delete.setToolTip("Eliminar gráfico")
        self.btn_delete.clicked.connect(self.delete_self)     
        
        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)  
        self.ax.callbacks.connect("xlim_changed", self.on_xlim_changed)

        btn_container = QVBoxLayout()
        btn_container.setContentsMargins(0, 20, 0, 0)
        btn_container.setSpacing(0)
        # btn_container.setSpacing(0)
        btn_container.addWidget(self.btn_add_channel, alignment=Qt.AlignCenter | Qt.AlignHCenter)
        btn_container.addWidget(self.btn_edit_title, alignment=Qt.AlignCenter | Qt.AlignHCenter)
        btn_container.addWidget(self.btn_reset_zoom, alignment=Qt.AlignCenter | Qt.AlignHCenter)
        btn_container.addWidget(self.btn_clear, alignment=Qt.AlignCenter | Qt.AlignHCenter)
        btn_container.addWidget(self.btn_delete, alignment=Qt.AlignCenter | Qt.AlignHCenter)

        btn_widget = QWidget()
        btn_widget.setLayout(btn_container)
        btn_widget.setFixedWidth(30)

        layout.addWidget(btn_widget)
    
    def on_xlim_changed(self, ax):
        if self.synchronizing:
            return
        if self.parent_tab:
            self.parent_tab.synchronize_xlim(self.ax)
        
    def on_mouse_move(self, event):
        if event.inaxes and self.status_callback:
            x = f"{event.xdata:.5f}"
            y = f"{event.ydata:.5f}"
            self.status_callback(f"x = {x}, y = {y}")

    def reload_plot_if_needed(self):
        # Verify if the plot has lines to reload
        if not hasattr(self, 'ax') or not self.ax.get_lines():
            return

        prev_title = self.ax.get_title()
        prev_xlabel = self.ax.get_xlabel()
        prev_ylabel = self.ax.get_ylabel()
        grid_on = self.ax.xaxis._major_tick_kw.get('gridOn', False) and self.ax.yaxis._major_tick_kw.get('gridOn', False)
        # Save current lines information
        lines_info = []
        for line in self.ax.get_lines():
            lines_info.append({
                'label': line.get_label(),
                'color': line.get_color(),
                'visible': line.get_visible(),
                'source': getattr(line, 'source_file', None),
                'channel': getattr(line, 'channel_name', None)
            })
        xlim = self.ax.get_xlim()
        self.ax.cla()
        print(lines_info)
        for info in lines_info:
            file = info['source']
            print(file)
            channel = info['channel']

            if file and channel and os.path.isfile(file):
                try:
                    if file.endswith('.out'):
                        time, values = get_channel_data_from_out(file, channel)
                    elif file.endswith('.csv'):
                        time, values = get_time_and_data_from_csv(file, channel)
                    else:
                        continue

                    print(f"Recargando {channel} desde {file}")
                    line = self.ax.plot(time, values, label=info['label'], color=info['color'])[0]
                    line.set_visible(info['visible'])
                    line.source_file = file
                    line.channel_name = channel
                    self.ax.set_xlim(xlim)
                    self.ax.callbacks.connect("xlim_changed", self.on_xlim_changed)
                except Exception as e:
                    print(f"Error recargando gráfico para {channel} en {file}: {e}")
            else:
                print(f"Archivo no encontrado o canal inválido: {file}, canal: {channel}")
                msg = f"Archivo no encontrado o canal inválido:\n{file}\nCanal: {channel}"
                print(msg)  # Sigue siendo útil para depuración en consola
                QMessageBox.warning(self, "Error al recargar", msg)

        self.ax.set_title(prev_title)
        self.ax.set_xlabel(prev_xlabel)
        self.ax.set_ylabel(prev_ylabel)
        self.ax.grid(grid_on)

        # Solo crea la leyenda si hay líneas con etiquetas válidas
        valid_lines = [line for line in self.ax.get_lines()
                    if line.get_label() and not line.get_label().startswith('_')]
        if valid_lines:
            self.ax.legend().set_picker(True)

        self.canvas.draw()


    def delete_self(self):
        # Remove this widget from its parent layout and delete it
        parent_layout = self.parentWidget().layout
        if parent_layout:
            parent_layout.removeWidget(self)
            self.setParent(None)
            self.deleteLater()


    def add_channel(self):
        # Plot channel from file
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
            line = self.ax.plot(time, values, label=new_label)[0]
            line.source_file = file
            line.channel_name = channel
            self.ax.set_xlabel('(s)', horizontalalignment='right', x=1.02, labelpad=-10)
            
        else:
            init_time, ok = QInputDialog.getDouble(self, "Tiempo de inicialización", "Ignorar tiempo menor a:", 0.0, 0)
            if not ok:
                return
            time, values = get_time_and_data_from_csv(file, channel, init_time = init_time)
            line = self.ax.plot(time, values, label=new_label)[0]
            line.source_file = file
            line.channel_name = channel
            self.ax.set_xlabel('(s)', horizontalalignment='right', x=1.02, labelpad=-10)

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
        # Open a dialog to edit the title, x-label, y-label, and legend labels/colors and multipliers
        current_title = self.ax.get_title()
        current_xlabel = self.ax.get_xlabel()
        current_ylabel = self.ax.get_ylabel()
        lines = self.ax.get_lines()
        current_labels = [line.get_label() for line in lines]
        current_colors = [line.get_color() for line in lines]
        grid_enabled = self.ax.xaxis._major_tick_kw.get('gridOn', False) and self.ax.yaxis._major_tick_kw.get('gridOn', False)
        current_multipliers = [getattr(line, "_multiplier", 1.0) for line in lines]
        
        dialog = EditLabelsDialog(current_title, current_xlabel, current_ylabel, current_labels, current_colors, grid_enabled,self,current_multipliers)
        if dialog.exec_():
            new_title, new_xlabel, new_ylabel, new_labels, new_colors, grid_enabled, multipliers = dialog.get_data()
            self.ax.set_title(new_title)
            self.ax.set_xlabel(new_xlabel, horizontalalignment='right', x=1.02, labelpad=-10)
            self.ax.set_ylabel(new_ylabel)
            self.ax.grid(grid_enabled)

            for line, new_label, new_color, multiplier in zip(lines, new_labels, new_colors, multipliers):
                line.set_label(new_label)
                line.set_color(new_color)
                if not hasattr(line, "_original_ydata"):
                    line._original_ydata = line.get_ydata()
                line.set_ydata(line._original_ydata * multiplier)
                line._multiplier = multiplier  # Guarda el multiplicador actual

            self.ax.legend().set_picker(True)
            self.canvas.draw()


    def reset_zoom(self):
        # Reset the x and y limits to their original state
        self.ax.autoscale()
        self.canvas.draw()

    def clear_plot(self):
        # Clear the plot and reset the axes
        self.ax.cla()
        self.ax.callbacks.connect("xlim_changed", self.on_xlim_changed)
        self.ax.set_title("")
        self.canvas.draw()

    def on_mouse_press(self, event):
        # Store the initial position and limits for panning
        if event.button == 1:
            self._drag_start = (event.x, event.y)
            self._drag_xlim = self.ax.get_xlim()
            self._drag_ylim = self.ax.get_ylim()

    def on_mouse_release(self, event):
        # Reset drag start position on mouse release
        if event.button == 1:
            self._drag_start = None

    def on_mouse_drag(self, event):
        # Handle mouse drag for panning
        if hasattr(self, '_drag_start') and self._drag_start and event.button == 1:
            dx = event.x - self._drag_start[0]
            dy = event.y - self._drag_start[1]

            ax = self.ax
            x0, x1 = self._drag_xlim
            y0, y1 = self._drag_ylim

            scale_x = (x1 - x0) / self.canvas.width()
            scale_y = (y1 - y0) / self.canvas.height()

            ax.set_xlim(x0 - dx * scale_x, x1 - dx * scale_x)
            ax.set_ylim(y0 - dy * scale_y, y1 - dy * scale_y)
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
        # Zoom in/out on scroll
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
        # Toggle visibility of lines based on legend item pick
        legend_line = event.artist
        label = legend_line.get_label()
        for line in self.ax.get_lines():
            if line.get_label() == label:
                visible = not line.get_visible()
                line.set_visible(visible)
                legend_line.set_alpha(1.0 if visible else 0.2)
        self.canvas.draw()

 

class PlotTab(QWidget):
    def __init__(self, parent=None, close_callback=None, get_file_list_callback=None, status_callback=None):
        super().__init__(parent)
        self.close_callback = close_callback
        self.get_file_list_callback = get_file_list_callback
        self.status_callback = status_callback
        self.synchronizing = False
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(10, 2, 10, 2)
        button_layout = QHBoxLayout()
        self.btn_add_plot = QPushButton("Agregar gráfico")
        self.btn_add_plot.clicked.connect(self.add_plot_canvas)
        self.btn_close = QPushButton("Cerrar pestaña")
        self.btn_close.clicked.connect(self.close_tab)
        button_layout.addWidget(self.btn_add_plot)
        button_layout.addWidget(self.btn_close)

        self.layout.addLayout(button_layout)

    def export_plots_combined(self, directory, base_name):
        # Export all plots in this tab as a single PNG file
        plots = [self.layout.itemAt(i).widget() for i in range(self.layout.count()) if isinstance(self.layout.itemAt(i).widget(), PlotCanvas)]
        if not plots:
            return

        fig, axs = plt.subplots(len(plots), 1, figsize=(10, 4 * len(plots)))
        if len(plots) == 1:
            axs = [axs]
        for ax, plot in zip(axs, plots):
            lines = plot.ax.get_lines()
            for line in lines:
                ax.plot(line.get_xdata(), line.get_ydata(), label=line.get_label(), color=line.get_color())
            ax.set_xlim(plot.ax.get_xlim())
            ax.set_ylim(plot.ax.get_ylim())
            ax.set_title(plot.ax.get_title())
            ax.set_xlabel(plot.ax.get_xlabel(), horizontalalignment='right', x=1.02, labelpad=-10)
            ax.set_ylabel(plot.ax.get_ylabel())
            # ax.grid(True)
            xgrid = any(line.get_visible() for line in plot.ax.get_xgridlines())
            ygrid = any(line.get_visible() for line in plot.ax.get_ygridlines())
            ax.grid(xgrid and ygrid)            
            ax.legend()
        fig.tight_layout()
        fig.savefig(os.path.join(directory, f"{base_name}.png"))
        plt.close(fig)

    def add_plot_canvas(self):
        # Create a new PlotCanvas and add it to the layout
        plot_canvas = PlotCanvas(self.get_file_list_callback, self.status_callback, parent_tab=self)
        self.layout.addWidget(plot_canvas)

    def close_tab(self):
        # Ask for confirmation before closing the tab
        if self.close_callback:
            self.close_callback(self)
            
    def reload_all_plots(self):
        # Reload all PlotCanvas widgets in this tab
        for i in range(self.layout.count()):
            widget = self.layout.itemAt(i).widget()
            if isinstance(widget, PlotCanvas):
                widget.reload_plot_if_needed()

    def synchronize_xlim(self, source_ax):
        # Synchronize x-axis limits across all PlotCanvas widgets in this tab
        new_xlim = source_ax.get_xlim()
        for i in range(self.layout.count()):
            widget = self.layout.itemAt(i).widget()
            if isinstance(widget, PlotCanvas) and widget.ax != source_ax:
                widget.synchronizing = True
                widget.ax.set_xlim(new_xlim)
                widget.canvas.draw()
                widget.synchronizing = False

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
        ## Used for get all files loaded in the dual tree
        files = []
        for tree in [self.tree_psse, self.tree_pscad]:
            for i in range(tree.topLevelItemCount()):
                item = tree.topLevelItem(i)
                files.append(item.toolTip(0))
        return files
    
class EditLabelsDialog(QDialog):
    def __init__(self, current_title, current_xlabel, current_ylabel, line_labels, line_colors, grid_enabled=False, parent=None, multipliers=None):
        super().__init__(parent)
        self.setWindowTitle("Editar etiquetas del gráfico")

        self.title_edit = QLineEdit(current_title)
        self.xlabel_edit = QLineEdit(current_xlabel if current_xlabel else "(s)")
        self.ylabel_edit = QLineEdit(current_ylabel)

        self.legends_list = QListWidget()
        self.color_map = {}
        self.mult_spinboxes = []

        if multipliers is None:
            multipliers = [1.0] * len(line_labels)

        # Layout para leyenda + multiplicador
        legend_mult_layout = QVBoxLayout()
        for idx, (label, color) in enumerate(zip(line_labels, line_colors)):
            hbox = QHBoxLayout()
            item = QListWidgetItem(label)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            item.setBackground(QColor(color))
            self.legends_list.addItem(item)
            self.color_map[label] = color

            # Multiplicador
            mult_spin = QDoubleSpinBox()
            mult_spin.setDecimals(4)
            mult_spin.setMinimum(-1e6)
            mult_spin.setMaximum(1e6)
            # Aquí se inicializa con el valor actual:
            mult_spin.setValue(multipliers[idx] if idx < len(multipliers) else 1.0)
            mult_spin.setToolTip("Multiplicador para la curva")
            self.mult_spinboxes.append(mult_spin)

            # Widget para leyenda y multiplicador juntos
            label_widget = QWidget()
            label_layout = QHBoxLayout()
            label_layout.setContentsMargins(0, 0, 0, 0)
            label_layout.addWidget(QLabel(label))
            label_layout.addWidget(QLabel(" x "))
            label_layout.addWidget(mult_spin)
            label_widget.setLayout(label_layout)
            legend_mult_layout.addWidget(label_widget)

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
        layout.addRow("Multiplicadores:", legend_mult_layout)
        layout.addRow(self.grid_checkbox)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def change_color(self, item):
        ## Used for change the color of the item in the legends list
        current_color = item.background().color()
        new_color = QColorDialog.getColor(current_color, self, "Seleccionar color")
        if new_color.isValid():
            item.setBackground(new_color)

    def get_data(self):
        ## Used for get the data from the dialog
        labels = [self.legends_list.item(i).text() for i in range(self.legends_list.count())]
        colors = [self.legends_list.item(i).background().color().name() for i in range(self.legends_list.count())]
        multipliers = [spin.value() for spin in self.mult_spinboxes]
        return self.title_edit.text(), self.xlabel_edit.text(), self.ylabel_edit.text(), labels, colors, self.grid_checkbox.isChecked(), multipliers

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PSSE/PSCAD ViEEwer")
        self.resize(1200, 700)

        # Establece el ícono de la aplicación
        self.setWindowIcon(QIcon("icono.ico"))

        # Panel izquierdo: archivos divididos
        self.dual_tree = DualDropWidget()

        # Zona de pestañas
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(False)
        self.tabs.tabBarDoubleClicked.connect(self.rename_tab)

        # Botón para agregar nueva pestaña
        self.btn_new_tab = QPushButton("+ Nueva pestaña")
        self.btn_new_tab.setMinimumWidth(180)      
        self.btn_new_tab.clicked.connect(self.add_new_tab)
        
        self.btn_reload = QPushButton("↻ Recargar archivos")
        self.btn_reload.setMinimumWidth(180)
        # self.btn_reload.setEnabled(False)
        self.btn_reload.clicked.connect(self.reload_files)
        
        self.btn_save_template = QPushButton("💾 Guardar plantilla")
        self.btn_save_template.setMaximumWidth(140)
        self.btn_save_template.clicked.connect(self.save_template)
        self.btn_load_template = QPushButton("📂 Cargar plantilla")
        self.btn_load_template.setMaximumWidth(140)
        self.btn_load_template.clicked.connect(self.load_template)
       
        self.btn_export = QPushButton("🖼 Exportar gráficos")
        self.btn_export.setMaximumWidth(140)
        self.btn_export.clicked.connect(self.export_all_plots)
        
        
        btn_layout = QHBoxLayout()
        # btn_layout.addStretch()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)
        btn_layout.addWidget(self.btn_new_tab)
        btn_layout.addWidget(self.btn_reload)
        
        top_layout = QVBoxLayout()
        # top_layout.addWidget(self.btn_new_tab)
        top_layout.addLayout(btn_layout)
        top_layout.addWidget(self.tabs)
        btn_layout.addWidget(self.btn_export)

        tabs_widget = QWidget()
        tabs_widget.setLayout(top_layout)
        btn_layout.addWidget(self.btn_save_template)
        btn_layout.addWidget(self.btn_load_template)
        
        # Diseño principal
        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(self.dual_tree, 2)
        layout.addWidget(tabs_widget, 8)

        self.setCentralWidget(central)
        self.status_bar = QStatusBar()
        self.status_bar.setLayoutDirection(Qt.RightToLeft)
        self.setStatusBar(self.status_bar)

        # Agrega la primera pestaña
        self.add_new_tab()

    def get_loaded_files(self):
        ## Used for get all files loaded in the dual tree
        return self.dual_tree.get_all_files()
           
    def add_new_tab(self):
        ## Used for add a new tab with a PlotTab widget
        tab = PlotTab(close_callback=self.remove_tab, get_file_list_callback=self.get_loaded_files, status_callback=self.status_bar.showMessage)
        index = self.tabs.addTab(tab, f"Gráfico {self.tabs.count() + 1}")
        self.tabs.setCurrentIndex(index)

    def remove_tab(self, tab_widget):
        ## Used for remove the tab
        reply = QMessageBox.question(self, "Confirmar eliminación", "¿Estás seguro de que deseas eliminar esta pestaña?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            index = self.tabs.indexOf(tab_widget)
            if index != -1:
                self.tabs.removeTab(index)

    def rename_tab(self, index):
        ## Used for rename the tab
        if index != -1:
            current_name = self.tabs.tabText(index)
            new_name, ok = QInputDialog.getText(self, "Renombrar pestaña", "Nuevo nombre:", text=current_name)
            if ok and new_name:
                self.tabs.setTabText(index, new_name)

    def reload_files(self):
        ## Used for reload all plots in the tabs
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if hasattr(tab, 'reload_all_plots'):
                tab.reload_all_plots()
    def export_all_plots(self):
        ## Used for export all plots in the tabs as PNG files
        save_dir = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta para exportar", "")
        if save_dir:
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                tab_name = self.tabs.tabText(i)
                if hasattr(tab, 'export_plots_combined'):
                    tab.export_plots_combined(save_dir, tab_name) 
                    self.statusBar().showMessage(f"Exportación completada: {tab_name}.png", 5000) 

    def save_template(self):
        ## Used for save templates in JSON format
        path, _ = QFileDialog.getSaveFileName(self, "Guardar plantilla", "", "Plantilla JSON (*.json)")
        if not path:
            return
        template = []
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            tab_data = {"name": self.tabs.tabText(i), "plots": []}
            for j in range(tab.layout.count()):
                widget = tab.layout.itemAt(j).widget()
                if isinstance(widget, PlotCanvas):
                    grid_on = widget.ax.xaxis._major_tick_kw.get('gridOn', False) and widget.ax.yaxis._major_tick_kw.get('gridOn', False)
                    plot_info = {
                        "title": widget.ax.get_title(),
                        "xlabel": widget.ax.get_xlabel(),
                        "ylabel": widget.ax.get_ylabel(),
                        "lines": [],
                        "xlim": widget.ax.get_xlim(),
                        "ylim": widget.ax.get_ylim(),
                        "grid": widget.ax.xaxis._major_tick_kw.get('gridOn', False) and widget.ax.yaxis._major_tick_kw.get('gridOn', False)
                    }
                    for line in widget.ax.get_lines():
                        plot_info["lines"].append({
                            "file": getattr(line, "source_file", None),
                            "channel": getattr(line, "channel_name", None),
                            "label": line.get_label(),
                            "color": line.get_color(),
                            "visible": line.get_visible(),
                        })
                    tab_data["plots"].append(plot_info)
            template.append(tab_data)


            template_data = {
                "tabs": template,
                "files": {
                    "psse": [self.dual_tree.tree_psse.topLevelItem(i).toolTip(0) for i in range(self.dual_tree.tree_psse.topLevelItemCount())],
                    "pscad": [self.dual_tree.tree_pscad.topLevelItem(i).toolTip(0) for i in range(self.dual_tree.tree_pscad.topLevelItemCount())]
                }
            }
                
        with open(path, "w", encoding="utf-8") as f:
            json.dump(template_data, f, indent=2)
        self.statusBar().showMessage("Plantilla guardada.", 3000)

    def load_template(self):
        # Used for load templates in JSON format
    
        path, _ = QFileDialog.getOpenFileName(self, "Cargar plantilla", "", "Plantilla JSON (*.json)")
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            template_data = json.load(f)

        # Limpiar los árboles
        self.dual_tree.tree_psse.clear()
        self.dual_tree.tree_pscad.clear()

        # Restaurar archivos en los árboles
        try:
            for file in template_data.get("files", {}).get("psse", []):
                if os.path.isfile(file):
                    item = QTreeWidgetItem([os.path.basename(file)])
                    item.setToolTip(0, file)
                    self.dual_tree.tree_psse.addTopLevelItem(item)
            for file in template_data.get("files", {}).get("pscad", []):
                if os.path.isfile(file):
                    item = QTreeWidgetItem([os.path.basename(file)])
                    item.setToolTip(0, file)
                    self.dual_tree.tree_pscad.addTopLevelItem(item)
        except AttributeError as e:
            QMessageBox.warning(self, "Error al cargar archivos", f"No se pudieron cargar algunos archivos:\n{e}")
        # Restaurar las pestañas y gráficos como antes
        self.tabs.clear()
        for tab_data in template_data["tabs"]:
            tab = PlotTab(close_callback=self.remove_tab, get_file_list_callback=self.get_loaded_files, status_callback=self.status_bar.showMessage)
            self.tabs.addTab(tab, tab_data["name"])
            for plot_info in tab_data["plots"]:
                plot_canvas = PlotCanvas(self.get_loaded_files, self.status_bar.showMessage, parent_tab=tab)
                tab.layout.addWidget(plot_canvas)
                plot_canvas.ax.set_title(plot_info.get("title", ""))
                plot_canvas.ax.set_xlabel(plot_info.get("xlabel", ""), horizontalalignment='right', x=1.02, labelpad=-10)
                plot_canvas.ax.set_ylabel(plot_info.get("ylabel", ""))
                plot_canvas.ax.grid(plot_info.get("grid", False))
                
                ## Conect events
                plot_canvas.canvas.mpl_connect("pick_event", plot_canvas.on_pick_legend)
                plot_canvas.canvas.mpl_connect("scroll_event", plot_canvas.on_scroll)
                plot_canvas.canvas.mpl_connect("motion_notify_event", plot_canvas.on_mouse_drag)
                plot_canvas.canvas.mpl_connect("button_press_event", plot_canvas.on_mouse_press)
                plot_canvas.canvas.mpl_connect("button_release_event", plot_canvas.on_mouse_release)
                plot_canvas._last_mouse_pos = None                
                
                for line_info in plot_info["lines"]:
                    file = line_info["file"]
                    channel = line_info["channel"]
                    if file and channel and os.path.isfile(file):
                        if file.endswith(".out"):
                            time, values = get_channel_data_from_out(file, channel)
                        elif file.endswith(".csv"):
                            time, values = get_time_and_data_from_csv(file, channel)
                        else:
                            continue
                        line = plot_canvas.ax.plot(time, values, label=line_info["label"], color=line_info["color"])[0]
                        line.set_visible(line_info.get("visible", True))
                        line.source_file = file
                        line.channel_name = channel
                if "xlim" in plot_info:
                    plot_canvas.ax.set_xlim(plot_info["xlim"])
                if "ylim" in plot_info:
                    plot_canvas.ax.set_ylim(plot_info["ylim"])
                plot_canvas.ax.legend().set_picker(True)
                plot_canvas.canvas.draw()
        self.statusBar().showMessage("Plantilla cargada.", 3000)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("icono.ico"))
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
