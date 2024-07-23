import sys
import subprocess
import time
import threading
from pynput import keyboard
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLineEdit, QLabel, QFormLayout, QFrame
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

class MyApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.worker_thread = None
        self.running = False
        self.exit_event = threading.Event()  # Use an event for signaling exit
        self.window_id = None
        self.additional_key = None
        self.num_lock_state = None  # To store Num Lock state
        self.num_loops = None  # For number of loops

        # Start listener for global hotkeys
        self.listener = keyboard.Listener(on_press=self.on_key_press)
        self.listener.start()

    def initUI(self):
        self.setWindowTitle('AutoCrafter')
        self.setGeometry(300, 300, 550, 300)
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

        # Create layout
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setSpacing(10)
        form_layout.setContentsMargins(20, 20, 20, 20)

        # Create a frame for the help text
        self.help_text_frame = QFrame(self)
        self.help_text_frame.setObjectName("help_text_frame")
        self.help_text_frame.setLayout(QVBoxLayout())

        # Create and style help text
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

        # Create input box for delay
        self.delay_input = QLineEdit(self)
        self.delay_input.setPlaceholderText('Enter delay in seconds')
        form_layout.addRow(QLabel('Delay:'), self.delay_input)

        # Create input box for additional keypress
        self.additional_key_input = QLineEdit(self)
        self.additional_key_input.setPlaceholderText('Enter key for macro')
        form_layout.addRow(QLabel('Macro Key:'), self.additional_key_input)

        # Create input box for number of loops
        self.loops_input = QLineEdit(self)
        self.loops_input.setPlaceholderText('Enter how many items to craft. If left empty it will run until stopped.')
        form_layout.addRow(QLabel('Items:'), self.loops_input)

        # Create Stop Button
        self.stop_btn = QPushButton('Stop', self)
        self.stop_btn.setObjectName('stop_btn')
        self.stop_btn.clicked.connect(self.stopAutomation)
        form_layout.addRow(self.stop_btn)

        # Create Quit Button
        self.quit_btn = QPushButton('Quit', self)
        self.quit_btn.clicked.connect(self.closeApp)
        form_layout.addRow(self.quit_btn)

        # Set layout
        self.setLayout(form_layout)

    def getWindowId(self, window_name):
        try:
            result = subprocess.check_output(["xdotool", "search", "--name", window_name]).decode().strip()
            return result.split()[0]  # Just take the first window ID if multiple are found
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
        # Turn Num Lock on or off
        if state:
            subprocess.call(["xset", "led", "named", "Num Lock"])
        else:
            subprocess.call(["xset", "led", "named", "Num Lock", "off"])

    def startAutomation(self):
        if self.running:
            print("Automation already running.")
            return

        try:
            self.delay = int(self.delay_input.text())
        except ValueError:
            print("Invalid delay value. Please enter an integer.")
            return

        if self.delay <= 0:
            print("Delay must be a positive integer.")
            return

        # Get the additional key from input
        self.additional_key = self.additional_key_input.text().strip()
        if not self.additional_key:
            print("Additional key cannot be empty.")
            return

        # Get the number of loops from input
        try:
            self.num_loops = int(self.loops_input.text())
        except ValueError:
            self.num_loops = None  # If the input is empty or invalid, run indefinitely

        # Get the window ID and focus it only once
        self.window_id = self.getWindowId("FINAL FANTASY XIV")  # Replace with your game window title
        if self.window_id is None:
            return

        self.num_lock_state = self.getNumLockState()  # Save current Num Lock state
        self.focusWindow(self.window_id)  # Focus the window only once
        self.exit_event.clear()  # Reset the exit event
        self.running = True
        self.worker_thread = threading.Thread(target=self.runAutomation)
        self.worker_thread.start()
        print("Automation started.")

    def runAutomation(self):
        loops = 0
        while not self.exit_event.is_set():
            print(f"Running loop {loops + 1}")
            self.sendKeystrokes(self.window_id)
            if self.num_loops is not None and loops >= self.num_loops:
                print("Number of loops reached.")
                break
            if self.exit_event.wait(timeout=self.delay):
                break
            loops += 1

        # Restore the Num Lock state after automation stops
        if self.num_lock_state is not None:
            self.setNumLockState(self.num_lock_state)
        print("Automation stopped.")

    def focusWindow(self, window_id):
        # Activate the window
        subprocess.call(["xdotool", "windowactivate", "--sync", window_id])
        # Ensure focus is properly set
        time.sleep(0.1)

    def sendKeystrokes(self, window_id):
        keystrokes = ['KP_4', 'KP_0', 'KP_0', 'KP_0', 'KP_0', 'KP_0']
        for key in keystrokes:
            if self.exit_event.is_set():
                return
            print(f"Sending key: {key}")
            cmd = ["xdotool", "key", "--window", window_id, key]
            subprocess.call(cmd)
            time.sleep(1)  # Sleep between individual keystrokes

        # Send the additional key after default sequence
        if self.additional_key and not self.exit_event.is_set():
            print(f"Sending additional key: {self.additional_key}")
            cmd = ["xdotool", "key", "--window", window_id, self.additional_key]
            subprocess.call(cmd)

    def stopAutomation(self):
        if self.running:
            print("Stopping automation.")
            self.exit_event.set()  # Signal the thread to stop
            if self.worker_thread is not None:
                self.worker_thread.join()  # Ensure the thread has stopped

    def closeApp(self):
        print("Quitting application.")
        self.stopAutomation()
        self.listener.stop()  # Stop listening for hotkeys
        QApplication.quit()  # Quit the application

    def on_key_press(self, key):
        try:
            if key == keyboard.Key.esc:
                self.closeApp()
            elif key == keyboard.Key.f11:  # Example keybind for starting automation
                self.startAutomation()
            elif key == keyboard.Key.f12:  # Example keybind for stopping automation
                self.stopAutomation()
        except Exception as e:
            print(f"Error handling key press: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()
    ex.show()
    sys.exit(app.exec_())
