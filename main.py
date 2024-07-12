import sys
import os
import re
import logging
import sqlite3
from PyQt5 import QtGui
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLineEdit,
                             QFileDialog, QMessageBox, QComboBox, QLabel, QMenuBar, QAction, QDialog, QCheckBox,
                             QPlainTextEdit, QListWidget, QListWidgetItem, QTabWidget, QProgressBar,
                             QSystemTrayIcon, QMenu)
from PyQt5.QtCore import Qt, QTimer, QUrl, QThread, pyqtSignal
from PyQt5.QtGui import QDesktopServices, QIcon

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

class ParseReverseQTextEditLogger(logging.Handler):
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit

    def emit(self, record):
        msg = self.format(record)
        self.text_edit.appendPlainText(msg)

class ParseReverseApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QtGui.QIcon(resource_path("app_icon.ico")))
        self.clipboard = QApplication.clipboard()
        self.tabs = []
        self.show_notifications = True
        self.db_path = "C:/TSTP/ParseReverse/DB/folders.db"
        self.create_db()
        try:
            self.initUI()
            self.init_tray_icon()
            self.init_logging()
        except Exception as e:
            logging.error(f"Initialization Error: {str(e)}")
            self.show_error("Initialization Error", f"An error occurred during initialization: {str(e)}")
            sys.exit(1)

    def init_logging(self):
        self.log_area_handler = ParseReverseQTextEditLogger(self.log_area)
        self.log_area_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(self.log_area_handler)
        logging.getLogger().setLevel(logging.DEBUG)
        logging.info("Logging initialized and ready.")

    def create_db(self):
        try:
            os.makedirs("C:/TSTP/ParseReverse/DB", exist_ok=True)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS folders (id INTEGER PRIMARY KEY, path TEXT UNIQUE)''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS parsed_items (id INTEGER PRIMARY KEY, content TEXT)''')
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error(f"Database Creation Error: {str(e)}")
            self.show_error("Database Creation Error", f"An error occurred while creating the database: {str(e)}")

    def initUI(self):
        try:
            self.layout = QVBoxLayout()

            # Menu Bar
            menubar = QMenuBar()
            self.layout.setMenuBar(menubar)

            file_menu = menubar.addMenu('File')
            edit_menu = menubar.addMenu('Edit')
            help_menu = menubar.addMenu('Help')

            new_tab_action = QAction('New Tab', self)
            new_tab_action.triggered.connect(self.new_tab)
            file_menu.addAction(new_tab_action)

            save_action = QAction('Save', self)
            save_action.triggered.connect(self.save_content)
            save_action.setShortcut('Ctrl+S')
            file_menu.addAction(save_action)

            exit_action = QAction('Exit', self)
            exit_action.triggered.connect(self.close)
            file_menu.addAction(exit_action)

            copy_clipboard_action = QAction('Copy from Clipboard', self)
            copy_clipboard_action.triggered.connect(self.copy_from_clipboard)
            copy_clipboard_action.setShortcut('Ctrl+1')
            edit_menu.addAction(copy_clipboard_action)

            toggle_auto_clipboard_action = QAction('Toggle Auto Clipboard', self)
            toggle_auto_clipboard_action.triggered.connect(lambda: self.toggle_auto_clipboard(None))
            toggle_auto_clipboard_action.setCheckable(True)
            toggle_auto_clipboard_action.setShortcut('Ctrl+2')
            edit_menu.addAction(toggle_auto_clipboard_action)

            toggle_auto_parse_action = QAction('Toggle Auto Parse', self)
            toggle_auto_parse_action.triggered.connect(lambda: self.toggle_auto_parse(None))
            toggle_auto_parse_action.setCheckable(True)
            toggle_auto_parse_action.setShortcut('Ctrl+3')
            edit_menu.addAction(toggle_auto_parse_action)

            detect_delimiter_action = QAction('Detect Delimiter', self)
            detect_delimiter_action.triggered.connect(self.detect_delimiter)
            edit_menu.addAction(detect_delimiter_action)

            toggle_notifications_action = QAction('Toggle Notifications', self)
            toggle_notifications_action.triggered.connect(self.toggle_notifications)
            toggle_notifications_action.setCheckable(True)
            edit_menu.addAction(toggle_notifications_action)

            toggle_log_action = QAction('Toggle Log', self)
            toggle_log_action.triggered.connect(self.toggle_log)
            toggle_log_action.setCheckable(True)
            edit_menu.addAction(toggle_log_action)

            help_menu.addAction(self.create_action("TSTP.xyz", lambda: QDesktopServices.openUrl(QUrl("https://www.tstp.xyz"))))

            tutorial_action = QAction('Tutorial', self)
            tutorial_action.triggered.connect(self.show_tutorial)
            help_menu.addAction(tutorial_action)

            about_action = QAction('About', self)
            about_action.triggered.connect(self.show_about)
            help_menu.addAction(about_action)

            donate_action = QAction('Donate', self)
            donate_action.triggered.connect(self.show_donate)
            help_menu.addAction(donate_action)

            self.tab_widget = QTabWidget()
            self.tab_widget.setTabsClosable(True)
            self.tab_widget.tabCloseRequested.connect(self.close_tab)
            self.tab_widget.currentChanged.connect(self.on_tab_changed)
            self.layout.addWidget(self.tab_widget)
            self.new_tab()

            self.log_area = QPlainTextEdit()
            self.log_area.setReadOnly(True)
            self.log_area.setVisible(False)
            self.layout.addWidget(self.log_area)

            self.setLayout(self.layout)
            self.setWindowTitle('TSTP:Parse Reverse')
            self.setGeometry(300, 300, 800, 600)
            self.show()

        except Exception as e:
            logging.error(f"UI Initialization Error: {str(e)}")
            self.show_error("UI Initialization Error", f"An error occurred while setting up the UI: {str(e)}")
            raise

    def new_tab(self):
        try:
            tab = QWidget()
            tab_layout = QVBoxLayout()

            # Content text area
            content_area = QTextEdit()
            content_area.textChanged.connect(self.update_file_list)
            tab_layout.addWidget(content_area)

            # File delimiter input
            delimiter_layout = QHBoxLayout()
            delimiter_layout.addWidget(QLabel("File Delimiter:"))
            delimiter_input = QComboBox()
            delimiter_input.setEditable(True)
            delimiter_input.addItems(["//", "###", "/*", "<!--"])
            delimiter_input.currentTextChanged.connect(self.update_delimiter_example)
            delimiter_layout.addWidget(delimiter_input)

            save_delimiter_button = QPushButton("Save Delimiter")
            save_delimiter_button.clicked.connect(self.save_delimiter)
            delimiter_layout.addWidget(save_delimiter_button)

            delimiter_type = QComboBox()
            delimiter_type.addItems(["Prefix", "Surround"])
            delimiter_type.currentTextChanged.connect(self.update_delimiter_example)
            delimiter_layout.addWidget(delimiter_type)

            delimiter_example = QLineEdit()
            delimiter_example.setReadOnly(True)
            delimiter_layout.addWidget(delimiter_example)
            tab_layout.addLayout(delimiter_layout)

            self.update_delimiter_example(delimiter_input, delimiter_type, delimiter_example)  # Initialize the example

            # Path selection
            path_layout = QHBoxLayout()
            path_input = QComboBox()
            path_input.setEditable(True)
            self.load_saved_folders(path_input)
            path_layout.addWidget(path_input)

            path_button = QPushButton("Select Folder")
            path_button.clicked.connect(lambda: self.select_folder(path_input))
            path_layout.addWidget(path_button)

            save_path_button = QPushButton("Save Folder")
            save_path_button.clicked.connect(lambda: self.save_folder(path_input))
            path_layout.addWidget(save_path_button)

            tab_layout.addLayout(path_layout)

            # List of files and checkboxes
            file_list = QListWidget()
            tab_layout.addWidget(file_list)

            # Buttons
            button_layout = QHBoxLayout()

            clear_button = QPushButton("Clear")
            clear_button.clicked.connect(lambda: content_area.clear())
            button_layout.addWidget(clear_button)

            auto_clipboard_button = QCheckBox("Auto Clipboard")
            auto_clipboard_button.stateChanged.connect(lambda state: self.toggle_auto_clipboard(tab))
            button_layout.addWidget(auto_clipboard_button)

            auto_parse_button = QCheckBox("Auto Parse")
            auto_parse_button.stateChanged.connect(lambda state: self.toggle_auto_parse(tab))
            button_layout.addWidget(auto_parse_button)

            select_all_button = QPushButton("Select All")
            select_all_button.clicked.connect(lambda: self.toggle_select_all(select_all_button, file_list))
            button_layout.addWidget(select_all_button)

            copy_clipboard_button = QPushButton("Copy Clipboard")
            copy_clipboard_button.clicked.connect(lambda: self.copy_from_clipboard(content_area))
            button_layout.addWidget(copy_clipboard_button)

            save_button = QPushButton("Save")
            save_button.clicked.connect(lambda: self.save_content(content_area))
            button_layout.addWidget(save_button)

            reverse_parse_button = QPushButton("Parse")
            reverse_parse_button.clicked.connect(lambda: self.reverse_parse(content_area, path_input, delimiter_input, delimiter_type, file_list))
            button_layout.addWidget(reverse_parse_button)

            tab_layout.addLayout(button_layout)

            tab.setLayout(tab_layout)
            self.tab_widget.addTab(tab, f"Tab {len(self.tabs) + 1}")
            self.tabs.append({
                'tab': tab,
                'content_area': content_area,
                'delimiter_input': delimiter_input,
                'delimiter_type': delimiter_type,
                'delimiter_example': delimiter_example,
                'path_input': path_input,
                'file_list': file_list,
                'auto_clipboard_button': auto_clipboard_button,
                'auto_parse_button': auto_parse_button,
                'auto_clipboard_timer': QTimer(self),
                'check_folder_timer': QTimer(self),
                'last_clipboard_content': ''  # Initialize last_clipboard_content
            })

            # Connect the clipboard timer to the check_clipboard method
            self.tabs[-1]['auto_clipboard_timer'].timeout.connect(self.check_clipboard)

            logging.info(f"New tab created: Tab {len(self.tabs)}")

        except Exception as e:
            logging.error(f"New Tab Error: {str(e)}")
            self.show_error("New Tab Error", f"An error occurred while creating a new tab: {str(e)}")
            raise

    def close_tab(self, index):
        try:
            self.tab_widget.removeTab(index)
            self.tabs.pop(index)
            logging.info(f"Tab {index + 1} closed")
        except Exception as e:
            logging.error(f"Close Tab Error: {str(e)}")
            self.show_error("Close Tab Error", f"An error occurred while closing the tab: {str(e)}")

    def on_tab_changed(self, index):
        try:
            if index != -1:
                for tab_index, tab_data in enumerate(self.tabs):
                    if tab_data['auto_clipboard_button'].isChecked():
                        if tab_index == index:
                            tab_data['auto_clipboard_timer'].start(1000)
                        else:
                            tab_data['auto_clipboard_timer'].stop()
            logging.info(f"Switched to tab {index + 1}")
        except Exception as e:
            logging.error(f"Tab Changed Error: {str(e)}")
            self.show_error("Tab Changed Error", f"An error occurred while changing tabs: {str(e)}")

    def update_delimiter_example(self, delimiter_input, delimiter_type, delimiter_example):
        try:
            delimiter = delimiter_input.currentText()
            if delimiter_type.currentText() == "Prefix":
                delimiter_example.setText(f"{delimiter} filename.filetype")
            else:
                delimiter_example.setText(f"{delimiter} filename.filetype {delimiter}")
            logging.info(f"Delimiter example updated: {delimiter_example.text()}")
        except Exception as e:
            logging.error(f"Update Delimiter Example Error: {str(e)}")
            self.show_error("Update Delimiter Example Error", f"An error occurred while updating the delimiter example: {str(e)}")

    def save_delimiter(self):
        try:
            delimiter = self.tabs[self.tab_widget.currentIndex()]['delimiter_input'].currentText()
            if delimiter and delimiter not in [self.tabs[self.tab_widget.currentIndex()]['delimiter_input'].itemText(i) for i in range(self.tabs[self.tab_widget.currentIndex()]['delimiter_input'].count())]:
                self.tabs[self.tab_widget.currentIndex()]['delimiter_input'].addItem(delimiter)
            logging.info(f"Delimiter saved: {delimiter}")
        except Exception as e:
            logging.error(f"Save Delimiter Error: {str(e)}")
            self.show_error("Save Delimiter Error", f"An error occurred while saving the delimiter: {str(e)}")

    def select_folder(self, path_input):
        try:
            folder = QFileDialog.getExistingDirectory(self, "Select Folder")
            if folder:
                path_input.setCurrentText(folder)
            logging.info(f"Folder selected: {folder}")
        except Exception as e:
            logging.error(f"Folder Selection Error: {str(e)}")
            self.show_error("Folder Selection Error", f"An error occurred while selecting the folder: {str(e)}")

    def save_folder(self, path_input):
        try:
            folder = path_input.currentText()
            if folder:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''INSERT OR IGNORE INTO folders (path) VALUES (?)''', (folder,))
                conn.commit()
                conn.close()
                # Update the combobox with the saved folder
                self.load_saved_folders(path_input)
            logging.info(f"Folder saved: {folder}")
        except Exception as e:
            logging.error(f"Save Folder Error: {str(e)}")
            self.show_error("Save Folder Error", f"An error occurred while saving the folder: {str(e)}")

    def load_saved_folders(self, path_input):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''SELECT path FROM folders''')
            folders = cursor.fetchall()
            path_input.clear()  # Clear current items before loading
            for folder in folders:
                path_input.addItem(folder[0])
            conn.close()
            logging.info(f"Saved folders loaded: {folders}")
        except Exception as e:
            logging.error(f"Load Saved Folders Error: {str(e)}")
            self.show_error("Load Saved Folders Error", f"An error occurred while loading saved folders: {str(e)}")

    def detect_delimiter(self):
        try:
            content = self.tabs[self.tab_widget.currentIndex()]['content_area'].toPlainText()
            if not content:
                self.show_error("Detect Delimiter Error", "Content area is empty")
                return

            delimiters = set(re.findall(r'\W+', content))
            if not delimiters:
                self.show_error("Detect Delimiter Error", "No delimiters detected in the content")
                return

            dialog = QDialog(self)
            dialog.setWindowTitle("TSTP:PR - Select Delimiter")
            layout = QVBoxLayout()
            dialog.setLayout(layout)

            delimiter_combobox = QComboBox()
            delimiter_combobox.addItems(delimiters)
            layout.addWidget(delimiter_combobox)

            select_button = QPushButton("Select")
            layout.addWidget(select_button)

            def on_select():
                selected_delimiter = delimiter_combobox.currentText()
                if selected_delimiter:
                    self.tabs[self.tab_widget.currentIndex()]['delimiter_input'].setCurrentText(selected_delimiter)
                dialog.close()

            select_button.clicked.connect(on_select)
            dialog.exec_()

            logging.info("Delimiter detected")
        except Exception as e:
            logging.error(f"Detect Delimiter Error: {str(e)}")
            self.show_error("Detect Delimiter Error", f"An error occurred while detecting the delimiter: {str(e)}")

    def toggle_select_all(self, select_all_button, file_list):
        try:
            select_all = select_all_button.text() == "Select All"
            for index in range(file_list.count()):
                item = file_list.item(index)
                item.setCheckState(Qt.Checked if select_all else Qt.Unchecked)
            select_all_button.setText("Deselect All" if select_all else "Select All")
            logging.info("Select All toggled")
        except Exception as e:
            logging.error(f"Toggle Select All Error: {str(e)}")
            self.show_error("Toggle Select All Error", f"An error occurred while toggling select all: {str(e)}")

    def update_file_list(self):
        try:
            content = self.tabs[self.tab_widget.currentIndex()]['content_area'].toPlainText()
            delimiter = self.tabs[self.tab_widget.currentIndex()]['delimiter_input'].currentText()
            delimiter_type = self.tabs[self.tab_widget.currentIndex()]['delimiter_type'].currentText()

            if not delimiter:
                return

            files = {}
            current_file = None

            if delimiter_type == "Prefix":
                pattern = f"^{re.escape(delimiter)}\\s*(.+\\..+)$"  # Ensure the filename has an extension
            else:  # Surround
                pattern = f"^{re.escape(delimiter)}\\s*(.+\\..+)\\s*{re.escape(delimiter)}$"

            for line in content.split('\n'):
                match = re.match(pattern, line.strip())
                if match:
                    current_file = match.group(1)
                    if current_file:
                        files[current_file] = ""
                elif current_file:
                    files[current_file] += line + '\n'

            self.tabs[self.tab_widget.currentIndex()]['file_list'].clear()
            for filename in files.keys():
                if filename:  # Ensure filename is not empty
                    item = QListWidgetItem(filename)
                    item.setCheckState(Qt.Checked)
                    self.tabs[self.tab_widget.currentIndex()]['file_list'].addItem(item)
            logging.info("File list updated")
        except Exception as e:
            logging.error(f"Update File List Error: {str(e)}")
            self.show_error("Update File List Error", f"An error occurred while updating the file list: {str(e)}")

    def reverse_parse(self, content_area, path_input, delimiter_input, delimiter_type, file_list):
        try:
            content = content_area.toPlainText()
            path = path_input.currentText()

            if not content:
                raise ValueError("Content area is empty")
            if not path:
                raise ValueError("No output path specified")

            delimiter = delimiter_input.currentText()
            delimiter_type = delimiter_type.currentText()

            if not delimiter:
                raise ValueError("File delimiter is not specified")

            files = {}
            current_file = None

            if delimiter_type == "Prefix":
                pattern = f"^{re.escape(delimiter)}\\s*(.+\\..+)$"  # Ensure the filename has an extension
            else:  # Surround
                pattern = f"^{re.escape(delimiter)}\\s*(.+\\..+)\\s*{re.escape(delimiter)}$"

            for line in content.split('\n'):
                match = re.match(pattern, line.strip())
                if match:
                    current_file = match.group(1)
                    if current_file:
                        files[current_file] = ""
                elif current_file:
                    files[current_file] += line + '\n'

            if not files:
                raise ValueError("No files were detected in the content")

            for index in range(file_list.count()):
                item = file_list.item(index)
                if item.checkState() == Qt.Checked:
                    filename = item.text()
                    file_content = files.get(filename)
                    if not file_content.strip():
                        continue

                    file_path = os.path.join(path, filename)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'w') as f:
                        f.write(file_content.strip())

                    self.save_parsed_item(file_content.strip())

            if not self.tabs[self.tab_widget.currentIndex()]['auto_clipboard_button'].isChecked() and not self.tabs[self.tab_widget.currentIndex()]['auto_parse_button'].isChecked():
                self.show_info("Success", f"Created {len(files)} files successfully!")
            else:
                self.show_tray_notification("Content parsed and saved")

            logging.info(f"Files parsed and saved to {path}")
        except Exception as e:
            logging.error(f"Reverse Parse Error: {str(e)}")
            self.show_tray_notification("Error during parsing: Some content could not be parsed.")

    def save_parsed_item(self, content):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO parsed_items (content) VALUES (?)''', (content,))
            conn.commit()
            conn.close()
            logging.info(f"Parsed item saved to database")
        except Exception as e:
            logging.error(f"Save Parsed Item Error: {str(e)}")
            self.show_error("Save Parsed Item Error", f"An error occurred while saving parsed item: {str(e)}")

    def show_error(self, title, message):
        logging.error(f"{title}: {message}")
        QMessageBox.critical(self, title, message)

    def show_info(self, title, message):
        logging.info(f"{title}: {message}")
        QMessageBox.information(self, title, message)

    def copy_from_clipboard(self, content_area):
        try:
            clipboard_content = self.clipboard.text()
            if clipboard_content != content_area.toPlainText():
                content_area.setPlainText(clipboard_content)
                self.tabs[self.tab_widget.currentIndex()]['last_clipboard_content'] = clipboard_content
                logging.info(f"Content copied from clipboard")
        except Exception as e:
            logging.error(f"Copy from Clipboard Error: {str(e)}")
            self.show_error("Copy from Clipboard Error", f"An error occurred while copying from clipboard: {str(e)}")

    def save_content(self, content_area):
        try:
            file_name, _ = QFileDialog.getSaveFileName(self, "Save File", "", "Text Files (*.txt);;All Files (*)")
            if file_name:
                with open(file_name, 'w') as f:
                    f.write(content_area.toPlainText())
                self.show_info("Success", "Content saved successfully!")
                logging.info(f"Content saved to {file_name}")
        except Exception as e:
            logging.error(f"Save Error: {str(e)}")
            self.show_error("Save Error", f"An error occurred while saving the content: {str(e)}")

    def toggle_auto_clipboard(self, tab=None):
        try:
            current_tab_index = self.tab_widget.currentIndex()
            if tab is None:
                tab = self.tab_widget.widget(current_tab_index)

            tab_data = next((t for t in self.tabs if t['tab'] == tab), None)
            if tab_data is None:
                raise ValueError("Tab not found")

            tab_data['auto_clipboard'] = tab_data['auto_clipboard_button'].isChecked()
            if tab_data['auto_clipboard']:
                tab_data['auto_clipboard_timer'].start(1000)  # Check every second
                logging.info("Auto Clipboard enabled")
            else:
                tab_data['auto_clipboard_timer'].stop()
                logging.info("Auto Clipboard disabled")
        except Exception as e:
            logging.error(f"Toggle Auto Clipboard Error: {str(e)}")
            self.show_error("Toggle Auto Clipboard Error", f"An error occurred while toggling auto clipboard: {str(e)}")

    def toggle_auto_parse(self, tab=None):
        try:
            current_tab_index = self.tab_widget.currentIndex()
            if tab is None:
                tab = self.tab_widget.widget(current_tab_index)

            tab_data = next((t for t in self.tabs if t['tab'] == tab), None)
            if tab_data is None:
                raise ValueError("Tab not found")

            tab_data['auto_parse'] = tab_data['auto_parse_button'].isChecked()
            if tab_data['auto_parse']:
                if not tab_data['path_input'].currentText():
                    self.select_folder(tab_data['path_input'])
                    if not tab_data['path_input'].currentText():
                        tab_data['auto_parse_button'].setChecked(False)
                        tab_data['auto_parse'] = False
                else:
                    tab_data['check_folder_timer'].timeout.connect(lambda: self.check_folder(tab_data))
                    tab_data['check_folder_timer'].start(10000)  # Check every 10 seconds
                logging.info("Auto Parse enabled")
            else:
                tab_data['check_folder_timer'].stop()
                logging.info("Auto Parse disabled")
        except Exception as e:
            logging.error(f"Toggle Auto Parse Error: {str(e)}")
            self.show_error("Toggle Auto Parse Error", f"An error occurred while toggling auto parse: {str(e)}")

    def check_folder(self, tab_data):
        try:
            if not os.path.isdir(tab_data['path_input'].currentText()):
                tab_data['auto_parse_button'].setChecked(False)
                tab_data['auto_parse'] = False
                self.show_error("Invalid Folder", "The selected folder is not valid.")
            logging.info(f"Folder checked: {tab_data['path_input'].currentText()}")
        except Exception as e:
            logging.error(f"Check Folder Error: {str(e)}")
            self.show_error("Check Folder Error", f"An error occurred while checking the folder: {str(e)}")

    def check_clipboard(self):
        try:
            current_tab_index = self.tab_widget.currentIndex()
            if current_tab_index != -1:
                tab = self.tabs[current_tab_index]
                new_clipboard = self.clipboard.text()
                if new_clipboard != tab['last_clipboard_content']:
                    tab['last_clipboard_content'] = new_clipboard
                    tab['content_area'].setPlainText(new_clipboard)
                    if tab['auto_parse_button'].isChecked():
                        self.reverse_parse(tab['content_area'], tab['path_input'], tab['delimiter_input'], tab['delimiter_type'], tab['file_list'])
                        tab['content_area'].clear()
                    logging.info("Clipboard content updated")
        except Exception as e:
            logging.error(f"Check Clipboard Error: {str(e)}")
            self.show_error("Check Clipboard Error", f"An error occurred while checking clipboard: {str(e)}")

    def show_tutorial(self):
        try:
            tutorial = ParseReverseTutorialWindow(self)
            tutorial.exec_()
        except Exception as e:
            logging.error(f"Show Tutorial Error: {str(e)}")
            self.show_error("Show Tutorial Error", f"An error occurred while showing the tutorial: {str(e)}")

    def show_about(self):
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("TSTP:PR - About")
            dialog.setFixedSize(400, 300)

            layout = QVBoxLayout()

            message = QLabel("This is the Parse Reverse application that allows you to reverse parse files.\n\nFor more information, check out the Tutorial in the Help menu.\n\nFor support, email us at Support@ParseReverse.xyz.\n\nThank you for your support and for downloading Parse Reverse!")
            message.setWordWrap(True)
            message.setAlignment(Qt.AlignCenter)

            layout.addWidget(message)

            button_layout = QHBoxLayout()

            btn_yes = QPushButton("Yes")
            btn_yes.clicked.connect(lambda: QUrl("https://parserverse.xyz/programs/parse-reverse/").openUrl())

            btn_ok = QPushButton("OK")
            btn_ok.clicked.connect(dialog.close)

            button_layout.addWidget(btn_yes)
            button_layout.addWidget(btn_ok)

            layout.addLayout(button_layout)

            dialog.setLayout(layout)
            dialog.exec_()
        except Exception as e:
            logging.error(f"About Error: {str(e)}")
            self.show_error("About Error", f"An error occurred while showing the about dialog: {str(e)}")

    def show_donate(self):
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle("TSTP:PR - Donate")
            dialog.setFixedSize(500, 300)

            layout = QVBoxLayout()

            message = QLabel("Thank you for considering a donation!\n\nYou do not have to donate, as this program is free and we will continue to provide free programs and projects for the public, but your donation is greatly appreciated if you still choose to.\n\nThank you for supporting us by downloading the program!\n\nWe appreciate it over at Parse Reverse.\n\nWould you like to visit the donation page now? Click Yes to go to the donation page or OK to close the window.")
            message.setWordWrap(True)
            message.setAlignment(Qt.AlignCenter)

            layout.addWidget(message)

            button_layout = QHBoxLayout()

            btn_yes = QPushButton("Yes")
            btn_yes.clicked.connect(lambda: QUrl("https://www.parserverse.xyz/donate").openUrl())

            btn_ok = QPushButton("OK")
            btn_ok.clicked.connect(dialog.close)

            button_layout.addWidget(btn_yes)
            button_layout.addWidget(btn_ok)

            layout.addLayout(button_layout)

            dialog.setLayout(layout)

            dialog.exec_()
        except Exception as e:
            logging.error(f"Donate Error: {str(e)}")
            self.show_error("Donate Error", f"An error occurred while showing the donate dialog: {str(e)}")

    def init_tray_icon(self):
        try:
            self.tray_icon = QSystemTrayIcon(QIcon(resource_path("app_icon.ico")), self)
            self.tray_icon.setToolTip("TSTP:Parse Reverse")  # Set the tooltip for the tray icon
            tray_menu = QMenu()

            toggle_auto_clipboard_action = QAction("Auto Clipboard", self)
            toggle_auto_clipboard_action.setCheckable(True)
            toggle_auto_clipboard_action.triggered.connect(self.toggle_auto_clipboard_from_tray)
            tray_menu.addAction(toggle_auto_clipboard_action)

            toggle_auto_parse_action = QAction("Auto Parse", self)
            toggle_auto_parse_action.setCheckable(True)
            toggle_auto_parse_action.triggered.connect(self.toggle_auto_parse_from_tray)
            tray_menu.addAction(toggle_auto_parse_action)

            tray_menu.addAction(self.create_action("TSTP.xyz", lambda: QDesktopServices.openUrl(QUrl("https://www.tstp.xyz"))))

            toggle_log_action = QAction("Toggle Log", self)
            toggle_log_action.setCheckable(True)
            toggle_log_action.triggered.connect(self.toggle_log)
            tray_menu.addAction(toggle_log_action)

            tray_menu.addAction(self.create_action("Donate", self.show_donate))
            tray_menu.addAction(self.create_action("About", self.show_about))
            tray_menu.addAction(self.create_action("Tutorial", self.show_tutorial))

            select_folder_action = QAction("Select Folder", self)
            select_folder_action.triggered.connect(lambda: self.select_folder(self.tabs[self.tab_widget.currentIndex()]['path_input']))
            tray_menu.addAction(select_folder_action)

            new_tab_action = QAction("New Tab", self)
            new_tab_action.triggered.connect(self.new_tab)
            tray_menu.addAction(new_tab_action)

            toggle_notifications_action = QAction("Toggle Notifications", self)
            toggle_notifications_action.setCheckable(True)
            toggle_notifications_action.triggered.connect(self.toggle_notifications)
            tray_menu.addAction(toggle_notifications_action)

            exit_action = QAction("Exit", self)
            exit_action.triggered.connect(self.close)
            tray_menu.addAction(exit_action)

            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.show()
        except Exception as e:
            logging.error(f"Tray Icon Initialization Error: {str(e)}")
            self.show_error("Tray Icon Initialization Error", f"An error occurred while initializing the tray icon: {str(e)}")

    def toggle_auto_clipboard_from_tray(self):
        try:
            current_tab_index = self.tab_widget.currentIndex()
            current_tab = self.tabs[current_tab_index]
            current_tab['auto_clipboard_button'].toggle()
        except Exception as e:
            logging.error(f"Toggle Auto Clipboard From Tray Error: {str(e)}")
            self.show_error("Toggle Auto Clipboard From Tray Error", f"An error occurred while toggling auto clipboard from tray: {str(e)}")

    def toggle_auto_parse_from_tray(self):
        try:
            current_tab_index = self.tab_widget.currentIndex()
            current_tab = self.tabs[current_tab_index]
            current_tab['auto_parse_button'].toggle()
        except Exception as e:
            logging.error(f"Toggle Auto Parse From Tray Error: {str(e)}")
            self.show_error("Toggle Auto Parse From Tray Error", f"An error occurred while toggling auto parse from tray: {str(e)}")

    def toggle_log(self):
        self.log_area.setVisible(not self.log_area.isVisible())
        logging.info(f"Log {'enabled' if self.log_area.isVisible() else 'disabled'}")

    def show_tray_notification(self, message):
        self.tray_icon.showMessage("TSTP:Parse Reverse", message, QSystemTrayIcon.Information, 10000)

    def toggle_notifications(self):
        self.show_notifications = not self.show_notifications
        logging.info(f"Notifications {'enabled' if self.show_notifications else 'disabled'}")

    def create_action(self, name, function):
        action = QAction(name, self)
        action.triggered.connect(function)
        return action

class ParseReverseTutorialWindow(QDialog):
    def __init__(self, parent=None):
        super(ParseReverseTutorialWindow, self).__init__(parent)
        try:
            self.setWindowTitle("TSTP:PR - Interactive Tutorial")
            self.setGeometry(100, 100, 800, 600)

            self.layout = QVBoxLayout()

            self.webView = QPlainTextEdit()
            self.webView.setReadOnly(True)
            self.webView.setStyleSheet("background-color: #ffffff;")

            self.layout.addWidget(self.webView)

            self.navigation_layout = QHBoxLayout()
            self.navigation_layout.setContentsMargins(10, 10, 10, 10)

            self.back_button = QPushButton("Previous")
            self.back_button.setStyleSheet(self.button_style())
            self.back_button.clicked.connect(self.go_to_previous_page)
            self.navigation_layout.addWidget(self.back_button)

            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setStyleSheet(self.progress_bar_style())
            self.navigation_layout.addWidget(self.progress_bar)

            self.next_button = QPushButton("Next")
            self.next_button.setStyleSheet(self.button_style())
            self.next_button.clicked.connect(self.go_to_next_page)
            self.navigation_layout.addWidget(self.next_button)

            self.start_button = QPushButton("Start Using App")
            self.start_button.setStyleSheet(self.button_style())
            self.start_button.clicked.connect(self.close)
            self.navigation_layout.addWidget(self.start_button)

            self.layout.addLayout(self.navigation_layout)
            self.setLayout(self.layout)

            self.current_page_index = 0
            self.tutorial_pages = [
                self.create_welcome_page(),
                self.create_overview_page(),
                self.create_select_folder_page(),
                self.create_set_delimiter_page(),
                self.create_parse_files_page(),
                self.create_save_copy_page(),
                self.create_auto_clipboard_page(),
                self.create_error_handling_page()
            ]

            self.load_tutorial_page(self.current_page_index)
        except Exception as e:
            logging.error(f"Initialization Error: {str(e)}")
            self.show_error("Initialization Error", f"Error initializing tutorial: {str(e)}")

    def load_tutorial_page(self, index):
        try:
            self.webView.setPlainText(self.tutorial_pages[index])
            self.progress_bar.setValue(int((index + 1) / len(self.tutorial_pages) * 100))
        except Exception as e:
            logging.error(f"Loading Error: {str(e)}")
            self.show_error("Loading Error", f"Error loading tutorial page: {str(e)}")
            
    def progress_bar_style(self):
        return """
        QProgressBar {
            border: 1px solid #bbb;
            border-radius: 5px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #4CAF50;
            width: 20px;
        }
        """
            
    def button_style(self):
        return """
        QPushButton {
            background-color: #4CAF50; /* Green */
            border: none;
            color: white;
            padding: 15px 32px;
            text-align: center;
            text-decoration: none;
            font-size: 16px;
            margin: 4px 2px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        """

    def go_to_previous_page(self):
        try:
            if self.current_page_index > 0:
                self.current_page_index -= 1
                self.load_tutorial_page(self.current_page_index)
        except Exception as e:
            logging.error(f"Navigation Error: {str(e)}")
            self.show_error("Navigation Error", f"Error navigating to previous page: {str(e)}")

    def go_to_next_page(self):
        try:
            if self.current_page_index < len(self.tutorial_pages) - 1:
                self.current_page_index += 1
                self.load_tutorial_page(self.current_page_index)
        except Exception as e:
            logging.error(f"Navigation Error: {str(e)}")
            self.show_error("Navigation Error", f"Error navigating to next page: {str(e)}")

    def create_welcome_page(self):
        return """
        Welcome to the Parse Reverse Interactive Tutorial

        In this tutorial, you will learn how to use the key features of the Parse Reverse application in detail.

        Let's get started!
        """

    def create_overview_page(self):
        return """
        Overview

        The Parse Reverse application allows you to reverse parse files, extracting content based on custom delimiters and saving them into separate files.

        Key features include:
        - Selecting and displaying file contents.
        - Setting custom delimiters for file content extraction.
        - Saving and copying parsed content.
        - Auto Clipboard functionality for real-time content updates.
        - Advanced error handling to ensure smooth operation.
        """

    def create_select_folder_page(self):
        return """
        Selecting a Folder

        To begin, select a folder to parse:
        1. Click on the 'Select Folder' button.
        2. Browse to the desired directory and select it.
        3. The selected path will be displayed in the path input field.
        """

    def create_set_delimiter_page(self):
        return """
        Setting File Delimiters

        To set the delimiters for parsing:
        1. Enter or select a delimiter in the 'File Delimiter' dropdown.
        2. Choose the delimiter type: 'Prefix' or 'Surround'.
        3. An example of the delimiter usage will be displayed for reference.
        4. Click 'Save Delimiter' to store the custom delimiter.
        """

    def create_parse_files_page(self):
        return """
        Parsing Files

        To parse files:
        1. Paste the content to be parsed into the text area.
        2. The file list will automatically update with detected files based on the set delimiter.
        3. Check or uncheck files in the list to include or exclude them from the parsing process.
        """

    def create_save_copy_page(self):
        return """
        Saving and Copying Parsed Content

        You can save or copy the parsed content for further use:
        1. Click 'Save' to save the parsed content to a file.
        2. Click 'Copy from Clipboard' to copy the parsed content from the clipboard to the text area.
        """

    def create_auto_clipboard_page(self):
        return """
        Using Auto Clipboard

        The Auto Clipboard feature allows real-time updates of the content area based on clipboard changes:
        1. Toggle the 'Auto Clipboard' checkbox to enable or disable this feature.
        2. When enabled, any new content copied to the clipboard will prompt the user to update the text area.
        """

    def create_error_handling_page(self):
        return """
        Advanced Error Handling

        Parse Reverse includes advanced error handling to ensure smooth operation:
        - Errors encountered during parsing will be displayed in a message box.
        - Detailed error messages provide information about the issue and possible causes.
        - Ensure you have the necessary permissions to read and write files in the selected folder.
        """

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        ex = ParseReverseApp()
        sys.exit(app.exec_())
    except Exception as e:
        logging.critical(f"Critical Error: {str(e)}")
        QMessageBox.critical(None, "Critical Error", f"An unexpected error occurred: {str(e)}")
        sys.exit(1)
