import serial
from messages.command import Command


class SerialInterface:
    def __init__(self, port, baudrate):
        self.ser = serial.Serial(port, baudrate, timeout=0.01)

    def send(self, command: Command):
        """
        Send Command to Arduino as compact string

        Format:
        pan,tilt\n
        Example:
        32,-15\n   (scaled by 100)
        """

        pan = int(command.pan * 100)
        tilt = int(command.tilt * 100)

        message = f"{pan},{tilt}\n"
        self.ser.write(message.encode())

    def close(self):
        self.ser.close()