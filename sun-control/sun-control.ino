#include <Wire.h>
#include <MPU6050.h>
#define BLINK_PIN 13  // GPIO 13
#define THERMISTOR_PIN 26

MPU6050 mpu;

int16_t ax, ay, az;
int16_t gx, gy, gz;

void setup() {
  pinMode(BLINK_PIN, OUTPUT);
  Serial.begin(115200);
  Wire.begin(23, 22);

  Serial.println("Initializing MPU6050...");
  mpu.initialize();             // Initialize the MPU
  if (!mpu.testConnection()) {
    Serial.println("MPU6050 connection failed");
    while (1);  // Stop program
  }
  Serial.println("MPU6050 connected successfully!");
}

unsigned long previousMillis = 0;
const long blinkInterval = 1000;  // milliseconds
bool ledState = false;

void loop() {
  unsigned long currentMillis = millis();

  if (currentMillis - previousMillis >= blinkInterval) {
    previousMillis = currentMillis;

    ledState = !ledState;  // Toggle state
    digitalWrite(BLINK_PIN, ledState ? HIGH : LOW);
  }

  int raw = analogRead(THERMISTOR_PIN);
  float voltage = raw * (3.3 / 4095.0);  // Convert to volts (ESP32 = 12-bit ADC)
  Serial.println(voltage);
  delay(500);

  mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);

  // Print values in space-separated format (Serial Plotter compatible)
  Serial.print(ax); Serial.print(" ");
  Serial.print(ay); Serial.print(" ");
  Serial.print(az); Serial.print(" ");
  Serial.print(gx); Serial.print(" ");
  Serial.print(gy); Serial.print(" ");
  Serial.print(gz); Serial.print(" ");
  Serial.println(voltage);
   // Ends the line
  delay(50);
}


