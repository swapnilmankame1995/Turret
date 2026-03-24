

# 🧱 STEP 5 — Communication Layer

* `comm/serial_interface.py` → low-level UART
* `comm/comm_node.py` → ROS-style wrapper

---

# 📄 `comm/serial_interface.py`

```python
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
```

---

# 📄 `comm/comm_node.py`

```python
from comm.serial_interface import SerialInterface


class CommNode:
    def __init__(self, config):
        self.serial = SerialInterface(
            config["serial"]["port"],
            config["serial"]["baudrate"]
        )

    def send_command(self, command):
        self.serial.send(command)
```

---

# 🧠 Why Two Layers?

| Layer                 | Responsibility     |
| --------------------- | ------------------ |
| `serial_interface.py` | Talks to hardware  |
| `comm_node.py`        | System integration |

👉 This is exactly how ROS nodes are structured.

---

# ⚡ Data Protocol (VERY IMPORTANT)

We are using:

```text
pan,tilt\n
```

Example:

```text
32,-15\n
```

### Why this format?

* Very small (fast)
* Easy to debug
* Easy to parse on Arduino
* ROS-friendly later

---

# 🔥 Arduino Side (Minimal Example)

You’ll need this running on your Arduino:

```cpp
String input = "";

void setup() {
  Serial.begin(230400);
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();

    if (c == '\n') {
      int comma = input.indexOf(',');
      int pan = input.substring(0, comma).toInt();
      int tilt = input.substring(comma + 1).toInt();

      // TODO: convert to motor control
      input = "";
    } else {
      input += c;
    }
  }
}
```

---

# ⚠️ Important Engineering Notes

## 1. We send **velocity**, not position

👉 smoother + more stable

---

## 2. Scaling by 100

```text
0.32 → 32
```

👉 avoids float transmission issues

---

## 3. Non-blocking serial

```python
timeout=0.01
```

👉 prevents system stalls

---

## 4. No acknowledgements (for now)

👉 keep latency LOW

---

# 📄 Markdown Documentation (Copy This)

```markdown
# 🧱 comm/serial_interface.py

## 🎯 Purpose
Handles **low-level UART communication** between PC and Arduino

---

## 🧠 Concept

We send **motor velocity commands** from PC → Arduino

Format:
```

pan,tilt\n

```

Example:
```

32,-15\n

```

---

## ⚙️ Data Encoding

| Value | Meaning |
|------|--------|
| `pan` | Horizontal velocity (-100 to 100) |
| `tilt` | Vertical velocity (-100 to 100) |

Scaling:
```

float [-1,1] → int [-100,100]

````

---

## 🔧 Function

```python
send(command)
````

Converts:

* `Command` → serial message

---

## ⚠️ Design Decisions

### 1. ASCII over binary

* Easier debugging
* Slightly slower but acceptable

---

### 2. No acknowledgements

* Reduces latency
* Suitable for real-time control

---

### 3. Stateless protocol

Each message is independent.

---

## 🔗 ROS2 Mapping

Will become:

* `/cmd_vel` publisher
* Serial node subscriber

---

---

# 🧱 comm/comm_node.py

## 🎯 Purpose

Acts as a **ROS-style communication node**

---

## 🧠 Role in System

```text
Controller → CommNode → Serial → Arduino
```

---

## 🔧 Function

```python
send_command(command)
```

---

## 🔗 ROS2 Mapping

Becomes:

* `/comm_node`
* Subscribes to `/cmd_vel`

---

---

# 🧠 Arduino Protocol

## 🎯 Purpose

Receive motor commands and execute them

---

## 🧠 Data Flow

```text
PC → Serial → Arduino → Motors
```

---

## 📦 Input Format

```
pan,tilt\n
```

---

## 🔧 Example

```
25,-10
```

---

## ⚠️ Notes

* Must be non-blocking
* Must handle partial messages
* Must reset buffer after newline

```
