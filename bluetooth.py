import serial
import time

# may not be COM6 depending on your system
bt = serial.Serial(port='COM6', baudrate=115200, timeout=1)
time.sleep(1)  # Let the connection settle

print("Connected to ESP32 over Bluetooth.")

while True:
    # --- Read incoming data ---
    if bt.in_waiting > 0:
        line = bt.readline().decode('utf-8', errors='ignore').strip()
        if line:
            print("From ESP32:", line)

    # --- Send test commands ---
    # You can uncomment to send something every few seconds:
    # bt.write(b"ping\n")

    # Or manually test input:
    # command = input("Send command: ")
    # bt.write((command.strip() + "\n").encode())

    #time.sleep(0.05)  # ~20Hz loop
