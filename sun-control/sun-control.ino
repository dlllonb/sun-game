#include <Wire.h>
#include <MPU6050.h>
#define BLINK_PIN 13  // GPIO 13
#define VIBRATION_PIN 12
#define THERMISTOR_PIN 26

MPU6050 mpu;

int16_t ax, ay, az;
int16_t gx, gy, gz;
float heat = 0;

String incomingCommand = "";

bool game = false;

const int PWM_CHANNEL = 0;
int vibrationLevel = 0;

bool flaring = false;


void setup() {
  pinMode(BLINK_PIN, OUTPUT);
  ledcAttachPin(VIBRATION_PIN, PWM_CHANNEL);   
  ledcSetup(PWM_CHANNEL, 5000, 8);
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
  // handle commands and vibrate motor
  readSerialCommand();

  //blinkDebugLED();
  // read and send sensor data
  readThermistor();
  readMPU();
  sendSensorData();

  if (!flaring){
    vibration_feedback();
  } else {
    flare();
    flaring = false;
  }

  // small delay 
  //delay(15);
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

void readMPU() {
  mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
}

void sendSensorData() {
  Serial.print(ax); Serial.print(" ");
  Serial.print(ay); Serial.print(" ");
  Serial.print(az); Serial.print(" ");
  Serial.print(gx); Serial.print(" ");
  Serial.print(gy); Serial.print(" ");
  Serial.print(gz); Serial.print(" ");
  Serial.println(heat);
}

void vibrate(int level) {
  vibrationLevel = constrain(level, 0, 5);
  int pwmDuty = map(vibrationLevel, 0, 5, 0, 255);
  ledcWrite(PWM_CHANNEL, pwmDuty);  // Set motor speed
}

void vibration_feedback() {
  // Baseline accelerometer readings when still (tune these for your setup)
  const int16_t ax_base = 1000;
  const int16_t ay_base = -1000;
  const int16_t az_base = 18200;

  // Calculate delta from resting state
  int16_t dax = ax - ax_base;
  int16_t day = ay - ay_base;
  int16_t daz = az - az_base;

  // Calculate magnitude of acceleration change
  float motion_mag = sqrt(dax * dax + day * day + daz * daz);

  // Map to 0–50 PWM range, clamp as needed
  int pwm_value = motion_mag / 180.0;  // adjust divisor to tune sensitivity
  if (pwm_value > 60) pwm_value = 60;

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


