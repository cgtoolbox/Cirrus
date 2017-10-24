import os
import sys

from PySide2 import QtGui
from PySide2 import QtWidgets
from PySide2 import QtCore

from CirrusCore import cirrus_io
reload(cirrus_io)
from CirrusCore import cirrus_objects
reload(cirrus_objects)
from CirrusCore import cirrus_config
reload(cirrus_config)

from CirrusCore.cirrus_connection import ConnectionInfos

ICONS = os.path.dirname(__file__) + "\\icons\\"

exe = sys.executable.split(os.sep)[-1].split('.')[0]
IS_HOUDINI = exe in ["hindie", "houdinicore", "hescape", "houdinifx"]

class PathBarDelimiter(QtWidgets.QLabel):

    def __init__(self, parent=None):
        super(PathBarDelimiter, self).__init__(parent=parent)

        self.setObjectName("navBarDelimiter")

        self.setFixedHeight(24)
        self.setFixedWidth(24)
        self.setContentsMargins(0, 0, 0, 0)
        self.setPixmap(QtGui.QIcon(ICONS + "pathbar_delimiter.png").pixmap(22,22))

class PathBarButton(QtWidgets.QPushButton):

    def __init__(self, label="", icon="folder.svg", path="", isroot=False, parent=None):
        super(PathBarButton, self).__init__(parent=parent)

        self.setObjectName("pathBarButton")
        self.isroot = isroot
        self.pathbar = parent
        self.setProperty("houdiniStyle", IS_HOUDINI)

        self.setText(label)
        self.label = label
        self.path = path
        self.setToolTip(path)
        if icon != "":
            self.setIcon(QtGui.QIcon(ICONS + icon))
            self.setIconSize(QtCore.QSize(22,22))
        self.setFixedHeight(24)
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)

        self.setContentsMargins(0, 0, 0, 0)
        self.clicked.connect(self.goto)

    def goto(self):

        main_ui = self.pathbar.main_ui
        if not self.isroot:
            bucket_name = ConnectionInfos.get("bucket_name")
            r = self.path.replace(bucket_name + '/', '')
            main_ui.show_panel(panel_name=self.label, panel_path=r)
        else:
             self.pathbar.reset()
             main_ui.back_to_root()

class PathBar(QtWidgets.QFrame):

    def __init__(self, root="", parent=None):
        super(PathBar, self).__init__(parent=parent)

        self.setProperty("houdiniStyle", IS_HOUDINI)
        self.setObjectName("pathbar")
        self.main_ui = parent
        self.root = root
        
        self.setFixedHeight(32)
        self.scroll_widget = QtWidgets.QWidget()
        self.scroll_layout = QtWidgets.QHBoxLayout()
        self.scroll_layout.setAlignment(QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.scroll_layout.setSpacing(0)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setContentsMargins(0, 0, 0, 0)
        self.scroll_area.setObjectName("pathbarscroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget.setLayout(self.scroll_layout)
        self.scroll_area.setWidget(self.scroll_widget)

        self.main_layout = QtWidgets.QHBoxLayout()
        self.main_layout.setAlignment(QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.setContentsMargins(5,0,0,0)
        self.main_layout.addWidget(self.scroll_area)

        self.root_w = PathBarButton(label=root, icon="root.svg", path=root, isroot=True, parent=self)
        self.scroll_layout.addWidget(self.root_w)
        self.scroll_layout.addWidget(PathBarDelimiter())

        self.setLayout(self.main_layout)

    def reset(self):

        for i in range(self.scroll_layout.count())[::-1]:
            it = self.scroll_layout.itemAt(i)
            
            w = it.widget()
            if isinstance(w, PathBarButton) and w.label == self.root:                
                continue

            self.scroll_layout.removeWidget(w)
            w.setParent(None)
            w.deleteLater()
            self.scroll_layout.update()
        
        self.scroll_layout.addWidget(PathBarDelimiter())

    def set_current_level(self, folder_path):

        levels = [n for n in folder_path.split('/') if n != ""]

        for i in range(self.scroll_layout.count())[::-1]:
            it = self.scroll_layout.itemAt(i)
            
            w = it.widget()
            if isinstance(w, PathBarButton) and w.label == self.root:                
                continue

            self.scroll_layout.removeWidget(w)
            w.setParent(None)
            w.deleteLater()
            self.scroll_layout.update()
        
        self.scroll_layout.addWidget(PathBarDelimiter())

        _path = self.root
        for level in levels:
            _path += '/' + level
            el = PathBarButton(label=level, icon="folder.svg", path=_path + '/', parent=self)
            self.scroll_layout.addWidget(el)
            self.scroll_layout.addWidget(PathBarDelimiter())

        self.scroll_layout.update()