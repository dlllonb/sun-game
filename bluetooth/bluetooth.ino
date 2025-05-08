#include "BluetoothSerial.h"

BluetoothSerial SerialBT;

void setup() {
  Serial.begin(115200);  // USB Serial for debug
  delay(5000);
  Serial.println("Setup...");
  SerialBT.begin("ESP32Sun");  // Name shown during pairing
  Serial.println("Bluetooth started. Pair to 'ESP32Sun'");
}

int pingcount = 0;
void loop() {
  // If a command was received from the laptop
  if (SerialBT.available()) {
    String command = SerialBT.readStringUntil('\n');
    command.trim();
    Serial.println("Received: " + command);  // USB debug
    SerialBT.println("Echo: " + command);    // Respond back over Bluetooth
  }

  // Simulate periodic data output (e.g., sensor)
  SerialBT.println(pingcount);  // Mock sensor data
  pingcount = pingcount + 1;
  delay(500);  // Slow it down for visibility
}
