#include <Arduino.h>
#include <math.h>

const int outputPin = 25;  // DAC-capable pin (GPIO25 or GPIO26)

String waveType = "sine";
int frequency = 1000;      // in Hz
int amplitude = 200;       // 0 to 255
int phase = 0;             // degrees
int sampleRate = 10000;    // in Hz
int waveformLength = 100;
int waveform[200];         // allow buffer expansion

unsigned long lastUpdate = 0;
int sampleIndex = 0;

// --- Generate Waveform ---
void generateWaveform() {
  waveformLength = sampleRate / frequency;
  waveformLength = constrain(waveformLength, 10, 200);

  for (int i = 0; i < waveformLength; i++) {
    float angle = 2 * PI * i / waveformLength + (phase * PI / 180.0);
    float val = 0;

    if (waveType == "sine") {
      val = sin(angle);
    } else if (waveType == "square") {
      val = sin(angle) >= 0 ? 1.0 : -1.0;
    } else if (waveType == "triangle") {
      val = 2 * abs(2 * (i / (float)waveformLength - floor(i / (float)waveformLength + 0.5))) - 1;
    } else if (waveType == "sawtooth") {
      val = 2 * (i / (float)waveformLength) - 1;
    } else {
      val = 0;  // unknown waveform
    }

    waveform[i] = (int)((val + 1.0) / 2.0 * amplitude);
    waveform[i] = constrain(waveform[i], 0, 255);
  }

  sampleIndex = 0;
}

// --- Parse Serial Command ---
void parseCommand(String cmd) {
  cmd.trim();
  cmd.toLowerCase();

  if (cmd.startsWith("wave=")) {
    int wavePos = cmd.indexOf("wave=");
    int end = cmd.indexOf(",", wavePos);
    waveType = cmd.substring(wavePos + 5, end == -1 ? cmd.length() : end);
  }

  if (cmd.indexOf("freq=") >= 0) {
    int freqPos = cmd.indexOf("freq=");
    int end = cmd.indexOf(",", freqPos);
    frequency = cmd.substring(freqPos + 5, end == -1 ? cmd.length() : end).toInt();
    frequency = constrain(frequency, 1, 5000);
  }

  if (cmd.indexOf("amp=") >= 0) {
    int ampPos = cmd.indexOf("amp=");
    int end = cmd.indexOf(",", ampPos);
    amplitude = cmd.substring(ampPos + 4, end == -1 ? cmd.length() : end).toInt();
    amplitude = constrain(amplitude, 0, 255);
  }

  if (cmd.indexOf("phase=") >= 0) {
    int phasePos = cmd.indexOf("phase=");
    int end = cmd.indexOf(",", phasePos);
    phase = cmd.substring(phasePos + 6, end == -1 ? cmd.length() : end).toInt();
    phase = constrain(phase, 0, 360);
  }

  generateWaveform();

  Serial.println("ACK");  // Acknowledge for GUI sync
}

void setup() {
  Serial.begin(115200);
  delay(500);
  generateWaveform();
  Serial.println("READY");
}

void loop() {
  // Handle incoming commands
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    parseCommand(cmd);
  }

  // Output waveform to DAC + simulate ADC reading
  if (micros() - lastUpdate >= 1000000UL / sampleRate) {
    dacWrite(outputPin, waveform[sampleIndex]);

    int adcValue = map(waveform[sampleIndex], 0, 255, 0, 4095);
    Serial.println(adcValue);

    sampleIndex = (sampleIndex + 1) % waveformLength;
    lastUpdate = micros();
  }
}
