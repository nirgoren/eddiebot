from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QRunnable, pyqtSlot, QThreadPool, QProcess
from PyQt5.QtGui import QPixmap
from pynput.keyboard import Listener
import XInput
import sys
import traceback
from worker import Worker
import eddiebot

controller_detected = False
capture_activation_key = None
sides_representation = ['P1', 'P2']

manual_action_map = {
    'Key.left': ('Dpad', eddiebot.direction_value_map['left']),
    'Key.right': ('Dpad', eddiebot.direction_value_map['right']),
    'Key.up': ('Dpad', eddiebot.direction_value_map['up']),
    'Key.down': ('Dpad', eddiebot.direction_value_map['down']),
    "'q'": ('BtnShoulderL', 1),
    "'w'": ('BtnX', 1),
    "'e'": ('BtnY', 1),
    "'r'": ('BtnShoulderR', 1),
    "'a'": ('TriggerL', 1),
    "'s'": ('BtnA', 1),
    "'d'": ('BtnB', 1),
    "'f'": ('TriggerR', 1)
}

HOTKEYS_TEXT =\
    '''Hotkeys:
    Reload Script - ctrl+r
    P1 side - ctrl+1
    P2 side - ctrl+2
    Increase Number of Repetitions - (ctrl+"=")
    Decrease Number of Repetitions - (ctrl+"-")
    Press Start on P2 Controller - Home Key
    Press select on P2 Controller - End Key
    Toggle Manual P2 Control (for Mapping) - Insert Key
    Map Play Button - ctrl+a
    Play Sequence - ctrl+p or mapped button
    Stop Sequence - ctrl+x 
    Toggle Sequence Start/End Sound - ctrl+m \n\n'''

XInput.get_connected()
LT_VALUE = -1
RT_VALUE = -2
activation_key = None
manual_mode = False


def on_press(key):
    global capture_activation_key
    global activation_key
    key_val = str(key)
    print("received", key_val)
    if key_val == r"'\x18'":  # ctrl+x
        eddiebot.playing = False
    elif eddiebot.playing:
        return
    if capture_activation_key:
        capture_activation_key = False
        activation_key = key_val
        print('Activation key set to', key_val)
    elif key_val == activation_key:
        worker = Worker(eddiebot.run_scenario)
        eddiebot.threadpool.start(worker)
        return
    if eddiebot.recordings_file:
        if key_val == r"'\x12'":  # ctrl+r
            print("Reloading script")
            eddiebot.reset()
        if key_val == r"<49>":  # ctrl+1
            eddiebot.direction_map_index = 0
            print("Switching to " + sides_representation[0] + " side")
            w.active_side_label.setText('Active side: ' +
                                        sides_representation[0])
            eddiebot.reset()
        if key_val == r"<50>":  # ctrl+2
            eddiebot.direction_map_index = 1
            eddiebot.reset()
            print("Switching to " + sides_representation[1] + " side")
            w.active_side_label.setText('Active side: ' +
                                        sides_representation[1])
        if key_val == r"'\x10'":  # ctrl+p
            worker = Worker(eddiebot.run_scenario)
            eddiebot.threadpool.start(worker)
    if key_val == r"<189>":  # '-'
        eddiebot.repetitions = max(1, eddiebot.repetitions - 1)
        print("Number of repetitions set to", eddiebot.repetitions)
        w.num_repetitions_label.setText('Number of repetitions: ' + str(eddiebot.repetitions))
    if key_val == r"<187>":  # '='
        eddiebot.repetitions = min(100, eddiebot.repetitions + 1)
        print("Number of repetitions set to", eddiebot.repetitions)
        w.num_repetitions_label.setText('Number of repetitions: ' + str(eddiebot.repetitions))
    if key_val == "Key.home":  # home
        eddiebot.tap_button('BtnStart', 1)
    if key_val == "Key.end":  # end
        eddiebot.tap_button('BtnBack', 1)
    if key_val == r"'\r'":  # ctrl+m
        eddiebot.toggle_mute()
        w.mute_label.setText('Mute Start/End Sequence Sound: ' + str(eddiebot.mute))
    if key_val == r"'\x04'":  # ctrl+d
        activation_key = None
        capture_activation_key = True
        print("Capturing activation key...")
    if key_val == "Key.insert":  # insert
        global manual_mode
        if not manual_mode:
            print('Manual mode activated')
        else:
            print('Manual mode deactivated')
        manual_mode = not manual_mode
    # manual control with the keyboard
    if manual_mode and not eddiebot.playing:
        if key_val in manual_action_map:
            eddiebot.tap_button(*manual_action_map[key_val])


class MyHandler(XInput.EventHandler):
    def process_button_event(self, event: XInput.Event):
        global capture_activation_key
        global activation_key
        if event.type == XInput.EVENT_BUTTON_PRESSED:
            if capture_activation_key:
                capture_activation_key = False
                activation_key = event.button_id
                print('Activation key set to', event.button)
            elif event.button_id == activation_key:
                if not eddiebot.playing:
                    worker = Worker(eddiebot.run_scenario)
                    eddiebot.threadpool.start(worker)
        pass

    def process_trigger_event(self, event):
        global capture_activation_key
        global activation_key
        LT, RT = XInput.get_trigger_values(XInput.get_state(0))
        #print(LT, RT)
        if LT == 1.0 or RT == 1.0:
            if capture_activation_key:
                capture_activation_key = False
                activation_key = LT_VALUE if LT == 1.0 else RT_VALUE
                print('Activation key set to', 'Left Trigger' if LT == 1.0 else 'Right Trigger')
            elif (LT == 1.0 and activation_key == -1) or (RT == 1.0 and activation_key == -2):
                if not eddiebot.playing:
                    worker = Worker(eddiebot.run_scenario)
                    eddiebot.threadpool.start(worker)
        pass

    def process_stick_event(self, event):
        pass

    def process_connection_event(self, event):
        pass


class DropFileLabel(QLabel):
    def __init__(self):
        super().__init__()

        self.setAlignment(Qt.AlignCenter)
        self.setText('\n\n Drop a Recording File Here \n\n' + HOTKEYS_TEXT)
        self.setStyleSheet('''
            QLabel{
                border: 4px dashed #aaa
            }
        ''')


class GUI(QWidget):

    def __init__(self):
        super().__init__()
        self.resize(500, 500)
        self.setAcceptDrops(True)
        self.setWindowTitle('EddieBot')
        main_layout = QVBoxLayout()

        self.drop_file_label = DropFileLabel()
        main_layout.addWidget(self.drop_file_label)

        self.recordings_file_label = QLabel()
        self.recordings_file_label.setAlignment(Qt.AlignCenter)
        self.recordings_file_label.setText('Active Recording File: \n')
        main_layout.addWidget(self.recordings_file_label)

        self.active_side_label = QLabel()
        self.active_side_label.setAlignment(Qt.AlignCenter)
        self.active_side_label.setText('Active Side: ' +
                                       sides_representation[eddiebot.direction_map_index])
        main_layout.addWidget(self.active_side_label)

        self.num_repetitions_label = QLabel()
        self.num_repetitions_label.setAlignment(Qt.AlignCenter)
        self.num_repetitions_label.setText('Number of Repetitions: ' + str(eddiebot.repetitions))
        main_layout.addWidget(self.num_repetitions_label)

        self.mute_label = QLabel()
        self.mute_label.setAlignment(Qt.AlignCenter)
        self.mute_label.setText('Mute Start/End Sequence Sound: ' + str(eddiebot.mute))
        main_layout.addWidget(self.mute_label)

        self.setLayout(main_layout)
        self.process = QProcess(self)

    def dragEnterEvent(self, event):
        event.accept()

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        if eddiebot.playing:
            print("Recording currently playing, can't load new recording")
            return
        if event.mimeData().hasText:
            event.setDropAction(Qt.CopyAction)
            file_path: str = event.mimeData().urls()[0].toLocalFile()
            if file_path.endswith('.txt'):
                temp = eddiebot.recordings_file
                eddiebot.recordings_file = file_path
                if eddiebot.load_recordings():
                    self.recordings_file_label.setText('Active recording file: \n' + eddiebot.recordings_file)
                else:
                    eddiebot.recordings_file = temp
            event.accept()
        else:
            event.ignore()


if __name__ == "__main__":
    # redirect stdout https://gist.github.com/rbonvall/9982648
    if XInput.get_connected()[0]:
        controller_detected = True
        print('XInput controller detected')
        my_handler: XInput.EventHandler = MyHandler(0)
        my_gamepad_thread = XInput.GamepadThread(my_handler)
    eddiebot.vcontroller.connect()
    app = QApplication(sys.argv)
    w = GUI()
    w.show()
    with Listener(on_press=on_press) as listener:
        app.exec_()
        listener.stop()
        eddiebot.vcontroller.disconnect()
        listener.join()
