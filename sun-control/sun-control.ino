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

  // small delay 
  delay(15);
}

void readSerialCommand() {
  while (Serial.available() > 0) {
    char c = Serial.read();

    // End of command line
    if (c == '\n') {
      incomingCommand.trim();  // remove stray whitespace or \r

      if (incomingCommand.startsWith("vibrate")) {
        int level = incomingCommand.substring(7).toInt();
        vibrate(level);
        Serial.print("vibrate level: ");
        Serial.println(level);
      }
      else if (incomingCommand == "flare") {
        // triggerFlare();
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

