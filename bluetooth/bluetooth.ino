#include "BluetoothSerial.h"

BluetoothSerial SerialBT;

void setup() {
  Serial.begin(115200);
  SerialBT.begin("ESP32Sun");  // This is the device name shown during pairing
  Serial.println("Bluetooth started. Pair to 'ESP32Sun'");
}

void loop() {
  if (SerialBT.available()) {
    String cmd = SerialBT.readStringUntil('\n');
    SerialBT.println("Echo: " + cmd);  // Replace with real handling
  }

  SerialBT.println("ax ay az gx gy gz temp");  // Send mock sensor data
  delay(100);  // Adjust as needed
}
