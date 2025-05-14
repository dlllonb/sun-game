#include <Wire.h>
#include <MPU6050.h>
#include "BluetoothSerial.h"
#define BLINK_PIN 13  // GPIO 13
#define VIBRATION_PIN 12
#define THERMISTOR_PIN 26


BluetoothSerial SerialBT;
MPU6050 mpu;

int16_t ax, ay, az;
int16_t gx, gy, gz;
float heat = 0;

String incomingCommand = "";

bool game = false;

const int PWM_CHANNEL = 0;
int vibrationLevel = 0;

bool flaring = false;

void readMPU() {
  mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
}
int16_t x_offset;
int16_t y_offset;
int16_t z_offset;
// int16_t ax_base;
// int16_t ay_base;
// int16_t az_base;

void setup() {
  pinMode(BLINK_PIN, OUTPUT);
  ledcAttachPin(VIBRATION_PIN, PWM_CHANNEL);   
  ledcSetup(PWM_CHANNEL, 5000, 8);
  Serial.begin(115200); // now for debugging on laptop serial 
  SerialBT.begin("ESP32Sun");
  Wire.begin(23, 22);

  Serial.println("Initializing MPU6050...");
  mpu.initialize();             // Initialize the MPU
  if (!mpu.testConnection()) {
    Serial.println("MPU6050 connection failed");
    while (1);  // Stop program
  }
  Serial.println("MPU6050 connected successfully!");
  Serial.println("Calibrating gyroscope offsets...");
  int32_t sum_gx = 0, sum_gy = 0, sum_gz = 0;
  // int32_t sum_ax = 0, sum_ay = 0, sum_az = 0;

  const int calibration_samples = 100;

  for (int i = 0; i < calibration_samples; i++) {
    readMPU();  // gets ax, ay, az, gx, gy, gz
    sum_gx += gx;
    sum_gy += gy;
    sum_gz += gz;
    // sum_ax += ax;
    // sum_ay += ay;
    // sum_az += az;
    delay(5);
  }

  int16_t x_offset = sum_gx / calibration_samples;
  int16_t y_offset = sum_gy / calibration_samples;
  int16_t z_offset = sum_gz / calibration_samples;
  // int16_t ax_base = sum_gx / calibration_samples;
  // int16_t ay_base = sum_gy / calibration_samples;
  // int16_t az_base = sum_gz / calibration_samples;
  // Serial.print("x_offset: "); Serial.println(x_offset);
  // Serial.print("y_offset: "); Serial.println(y_offset);
  // Serial.print("z_offset: "); Serial.println(z_offset);
}

unsigned long previousMillis = 0;
const long blinkInterval = 1000;  // milliseconds
bool ledState = false;

void loop() {
  // handle commands and vibrate motor
  //readSerialCommand();
  readBTCommand();

  //blinkDebugLED();
  // read and send sensor data
  readThermistor();
  readMPU();
  sendSensorData();
  sendSensorDataBT();

  if (!flaring){
    vibration_feedback();
  } else {
    flare();
    flaring = false;
  }

  // small delay to match FPS of game
  delay(16);
}

void readSerialCommand() {
  while (Serial.available() > 0) {
    char c = Serial.read();

    // End of command linegit 
    if (c == '\n') {
      incomingCommand.trim();  // remove stray whitespace or \r

      if (incomingCommand.startsWith("vibrate")) {
        int level = incomingCommand.substring(7).toInt();
        vibrate(level);
        Serial.print("vibrate level: ");
        Serial.println(level);
      }
      else if (incomingCommand == "flare") {
        flaring = true;
      } 
      else if (incomingCommand == "reset") {
        // resetSun();
      } 
      else if (incomingCommand == "ping") {
        Serial.println("pong");
      } 
      else {
        Serial.print("Unknown command: ");
        Serial.println(incomingCommand);
      }

      incomingCommand = "";  // clear buffer
    } 
    else {
      incomingCommand += c;
    }
  }
}

void readBTCommand() {
  while (SerialBT.available() > 0) {
    char c = SerialBT.read();

    if (c == '\n') {
      incomingCommand.trim();

      if (incomingCommand.startsWith("vibrate")) {
        int level = incomingCommand.substring(7).toInt();
        vibrate(level);
        SerialBT.print("vibrate level: ");
        SerialBT.println(level);
      }
      else if (incomingCommand == "flare") {
        flaring = true;
      } 
      else if (incomingCommand == "reset") {
        // resetSun();
      } 
      else if (incomingCommand == "ping") {
        SerialBT.println("pong");
      } 
      else {
        SerialBT.print("Unknown command: ");
        SerialBT.println(incomingCommand);
      }

      incomingCommand = "";
    } 
    else {
      incomingCommand += c;
    }
  }
}



void blinkDebugLED() {
  unsigned long currentMillis = millis();
  if (currentMillis - previousMillis >= blinkInterval) {
    previousMillis = currentMillis;
    ledState = !ledState;
    digitalWrite(BLINK_PIN, ledState ? HIGH : LOW);
  }
}

void readThermistor() {
  int raw = analogRead(THERMISTOR_PIN);
  float voltage = raw * (3.3 / 4095.0);

  // Invert and scale: hotter = higher heatLevel
  heat = (3.3 - voltage) * 100.0;

  // Clamp to range
  if (heat < 0) heat = 0;
  if (heat > 100) heat = 100;
}

void sendSensorData() {
  //Serial.print(ax); Serial.print(" ");
  //Serial.print(ay); Serial.print(" ");
  //Serial.print(az); Serial.print(" ");
  //Serial.print(gx); Serial.print(" ");  // tilt
  //Serial.print(gy); Serial.println(" ");
  //Serial.print(gz); Serial.print(" ");  // spin
  //Serial.println(heat);
}

void sendSensorDataBT() {
  int z_offset_ = -180;
  int x_offset_ = -240;
  int y_offset_ = -65;
  // SerialBT.print(ax); SerialBT.print(" ");
  // SerialBT.print(ay); SerialBT.print(" ");
  // SerialBT.print(az); SerialBT.print(" ");
  SerialBT.print(gx - x_offset_); SerialBT.print(" ");
  SerialBT.print(gy - y_offset_); SerialBT.print(" ");
  SerialBT.print(gz - z_offset_); SerialBT.println(" ");
  // SerialBT.println(heat);

  // convert gz to a spin rate, send it to sun-display
  //SerialBT.println(gz);
}

void vibrate(int level) {
  vibrationLevel = constrain(level, 0, 5);
  int pwmDuty = map(vibrationLevel, 0, 5, 0, 255);
  ledcWrite(PWM_CHANNEL, pwmDuty);  // Set motor speed
}

void vibration_feedback() {
  const int16_t ax_base = 1100;
  const int16_t ay_base = -500;
  const int16_t az_base = 18200;

  // Calculate delta from resting state
  int16_t dax = ax - ax_base;
  int16_t day = ay - ay_base;
  int16_t daz = az - az_base;

  // Calculate magnitude of acceleration change
  float motion_mag = sqrt(dax * dax + day * day + daz * daz);
  Serial.println(motion_mag); Serial.print(" ");

  // Map to 0–50 PWM range, clamp as needed
  int pwm_value = motion_mag / 160.0;  // adjust divisor to tune sensitivity
  if (pwm_value > 85) pwm_value = 85;
  if (pwm_value < 35) pwm_value = 0;

  ledcWrite(PWM_CHANNEL, pwm_value);
  Serial.println(pwm_value); Serial.print(" ");
}

void flare() {
  const int duration_ms = 1000;      // total duration of flare
  const int steps = 50;              // number of PWM updates
  const float pi = 3.14159;

  for (int i = 0; i <= steps; i++) {
    // Create a flare-like curve: sin(pi * x) goes 0→1→0 smoothly
    float progress = (float)i / steps;
    float intensity = sin(progress * pi);  // sinusoidal envelope
    int pwm_value = intensity * 255;

    ledcWrite(0, pwm_value);
    delay(duration_ms / steps);
  }

  // Ensure motor ends at 0
  ledcWrite(0, 0);
}


