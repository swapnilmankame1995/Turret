from comm.serial_interface import SerialInterface


class CommNode:
    def __init__(self, config):
        self.serial = SerialInterface(
            config["serial"]["port"],
            config["serial"]["baudrate"]
        )

    def send_command(self, command):
        self.serial.send(command)