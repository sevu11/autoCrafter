import sys
import subprocess
import time
import threading
from pynput import keyboard
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLineEdit, QLabel, QFormLayout, QFrame
from PyQt5.QtCore import Qt

class MyApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.worker_thread = None
        self.running = False
        self.exit_event = threading.Event()
        self.window_id = None
        self.additional_key = None
        self.num_lock_state = None
        self.num_loops = None
        self.delay = None

        self.listener = keyboard.Listener(on_press=self.on_key_press)
        self.listener.start()

    def initUI(self):
        self.setWindowTitle('AutoCrafter')
        self.setGeometry(300, 300, 550, 350)  # Increased height for additional label
        self.setStyleSheet("""
            QWidget {
                background-color: #2e2e2e;  /* Dark background */
                color: #e0e0e0;  /* Light text color */
            }
            QLabel {
                font-size: 11pt;
                color: #e0e0e0;
            }
            QLineEdit {
                background-color: #3c3c3c;
                color: #e0e0e0;
                border: 1px solid #4a4a4a;
                padding: 5px;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #4a90d6;
                color: white;
                padding: 10px;
                border-radius: 4px;
                border: none;
                font-size: 10pt;
            }
            QPushButton:pressed {
                background-color: #357abd;
            }
            QPushButton#stop_btn {
                background-color: #e94e77;
            }
            QPushButton#stop_btn:pressed {
                background-color: #d2365e;
            }
            QFrame.help_text_frame {
                background-color: #3c3c3c;
                border: 1px solid #4a4a4a;
                border-radius: 5px;
                padding: 10px;
            }
        """)

        # Set window to always stay on top
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setSpacing(10)
        form_layout.setContentsMargins(20, 20, 20, 20)

        self.help_text_frame = QFrame(self)
        self.help_text_frame.setObjectName("help_text_frame")
        self.help_text_frame.setLayout(QVBoxLayout())

        self.help_text = QLabel(
            '''
            <b>AutoCrafter Help:</b><br>
            Basic app to craft in bulk. Macro required. Is not a full-fledged bot.<br><br>
            <b>F11:</b> Start<br>
            <b>F12:</b> Stop<br>
            <b>Esc:</b> Quit
            ''',
            self
        )
        self.help_text.setWordWrap(True)
        self.help_text_frame.layout().addWidget(self.help_text)
        form_layout.addRow(self.help_text_frame)

        self.delay_input = QLineEdit(self)
        self.delay_input.setPlaceholderText('Enter delay in seconds')
        form_layout.addRow(QLabel('Delay (sec):'), self.delay_input)

        self.additional_key_input = QLineEdit(self)
        self.additional_key_input.setPlaceholderText('Enter key for macro')
        form_layout.addRow(QLabel('Macro Key:'), self.additional_key_input)

        self.loops_input = QLineEdit(self)
        self.loops_input.setPlaceholderText('Enter how many items to craft. If left empty it will run until stopped.')
        form_layout.addRow(QLabel('Items:'), self.loops_input)

        self.remaining_items_label = QLabel("Remaining items: Unknown", self)
        form_layout.addRow(self.remaining_items_label)

        self.stop_btn = QPushButton('Stop', self)
        self.stop_btn.setObjectName('stop_btn')
        self.stop_btn.clicked.connect(self.stopApp)
        form_layout.addRow(self.stop_btn)

        self.quit_btn = QPushButton('Quit', self)
        self.quit_btn.clicked.connect(self.closeApp)
        form_layout.addRow(self.quit_btn)

        self.setLayout(form_layout)

    def getWindowId(self, window_name):
        try:
            result = subprocess.check_output(["xdotool", "search", "--name", window_name]).decode().strip()
            return result.split()[0]
        except subprocess.CalledProcessError:
            print("Error: Window not found.")
            return None

    def getNumLockState(self):
        try:
            result = subprocess.check_output(["xset", "-q"]).decode()
            for line in result.splitlines():
                if "Num Lock" in line:
                    return "on" in line
        except subprocess.CalledProcessError:
            return None

    def setNumLockState(self, state):
        if state:
            subprocess.call(["xset", "led", "named", "Num Lock"])
        else:
            subprocess.call(["xset", "led", "named", "Num Lock", "off"])

    def startApp(self):
        if self.running:
            print("App already running.")
            return

        # Read and validate inputs
        try:
            self.delay = int(self.delay_input.text())
            if self.delay <= 0:
                raise ValueError("Delay must be a positive integer.")
        except ValueError as e:
            print(f"Invalid delay value: {e}")
            return

        self.additional_key = self.additional_key_input.text().strip()
        if not self.additional_key:
            print("Additional key cannot be empty.")
            return

        try:
            self.num_loops = int(self.loops_input.text())
        except ValueError:
            self.num_loops = None

        self.window_id = self.getWindowId("FINAL FANTASY XIV")
        if self.window_id is None:
            return

        self.num_lock_state = self.getNumLockState()
        self.focusWindow(self.window_id)
        self.exit_event.clear()
        self.running = True

        # Start the app thread
        self.worker_thread = threading.Thread(target=self.runApp)
        self.worker_thread.start()

        print("App started.")

    def runApp(self):
        loops = 0
        remaining_items = self.num_loops

        while not self.exit_event.is_set():
            print(f"Running loop {loops + 1}")
            self.focusWindow(self.window_id)
            self.sendKeystrokes(self.window_id)
            self.focusAppWindow()

            # Update the remaining items label
            if remaining_items is not None:
                remaining_items -= 1
                self.remaining_items_label.setText(f"Remaining items: {remaining_items}")

            if remaining_items is not None and remaining_items <= 0:
                print("Number of loops reached.")
                break

            if self.exit_event.wait(timeout=self.delay):
                break

            loops += 1

        if self.num_lock_state is not None:
            self.setNumLockState(self.num_lock_state)
        print("App stopped.")

    def focusWindow(self, window_id):
        subprocess.call(["xdotool", "windowactivate", "--sync", window_id])
        time.sleep(0.1)

    def focusAppWindow(self):
        self.raise_()  # Bring the PyQt5 window to the front
        self.activateWindow()  # Make sure it gains focus
        self.raise_()  # Bring the PyQt5 window to the front again
        self.activateWindow()  # Make sure it gains focus again

    def sendKeystrokes(self, window_id):
        keystrokes = ['KP_0', 'KP_0', 'KP_0', 'KP_0']
        for key in keystrokes:
            if self.exit_event.is_set():
                return
            print(f"Sending key: {key}")
            cmd = ["xdotool", "key", "--window", window_id, key]
            subprocess.call(cmd)
            time.sleep(0.5)

        if self.additional_key and not self.exit_event.is_set():
            print(f"Sending additional key: {self.additional_key}")
            cmd = ["xdotool", "key", "--window", window_id, self.additional_key]
            subprocess.call(cmd)

    def stopApp(self):
        if self.running:
            print("Stopping app.")
            self.exit_event.set()
            if self.worker_thread is not None:
                self.worker_thread.join()
            self.running = False  # Explicitly set running to False after stopping

    def closeApp(self):
        print("Quitting application.")
        self.stopApp()
        self.listener.stop()
        QApplication.quit()

    def on_key_press(self, key):
        try:
            if key == keyboard.Key.esc:
                self.closeApp()
            elif key == keyboard.Key.f11:
                self.startApp()
            elif key == keyboard.Key.f12:
                self.stopApp()
        except Exception as e:
            print(f"Error handling key press: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()
    ex.show()
    sys.exit(app.exec_())
