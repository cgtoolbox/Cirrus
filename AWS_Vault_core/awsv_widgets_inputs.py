from PySide2 import QtGui
from PySide2 import QtCore
from PySide2 import QtWidgets

class MessageInput(QtWidgets.QDialog):

    def __init__(self, is_mandatory=False, parent=None):
        super(MessageInput, self).__init__(parent=parent)

        self.setWindowTitle("Message")
        self.message = ""

        main_layout = QtWidgets.QVBoxLayout()
        if is_mandatory:
            msg = "Enter a message ( mantadory ):"
        else:
            msg = "Enter a message:"
        self.lbl = QtWidgets.QLabel(msg)
        main_layout.addWidget(self.lbl)

        self.text_edit = QtWidgets.QTextEdit()
        main_layout.addWidget(self.text_edit)

        buttons_layout = QtWidgets.QHBoxLayout()
        self.valid_btn = QtWidgets.QPushButton("Ok")
        self.valid_btn.clicked.connect(self.valid)
        self.close_btn = QtWidgets.QPushButton("Cancel")
        self.close_btn.clicked.connect(self.close)
        buttons_layout.addWidget(self.valid_btn)
        buttons_layout.addWidget(self.close_btn)
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)

        self.is_mandatory = is_mandatory

        self.setStyleSheet("""QLabel{background-color: transparent}
                              QTextEdit{background-color: #1a1a1a;
                                        color: #f2f2f2}""")

    def valid(self):

        msg = self.text_edit.toPlainText()
        if msg.replace(' ', '') == "" and self.is_mandatory:
            QtWidgets.QMessageBox.warning(self, "Warning", "Message is empty")
            return

        self.message = msg
        self.close()