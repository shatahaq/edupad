// Uji ESP32-S3 + amplifier I2S MAX98357A + speaker, tanpa kode EduPad.
// Memutar tangga nada lalu nada 1 kHz, berulang. Tekan BOOT untuk mengulang segera.
// Serial Monitor 115200 menampilkan nada yang sedang diputar.
#include <Arduino.h>
#include <driver/i2s.h>
#include <math.h>

// Pin ini tidak bentrok dengan LCD (9-13, 21) dan mic (4-6), jadi bisa dipakai seterusnya.
#define PIN_AMP_BCLK 15
#define PIN_AMP_LRC 16
#define PIN_AMP_DIN 17
#define PIN_BUTTON 0

#define SAMPLE_RATE 16000
#define VOLUME 0.25f  // 0.0-1.0; mulai pelan supaya speaker aman

const i2s_port_t PORT = I2S_NUM_1;  // I2S_NUM_0 nanti untuk mic

bool startI2S() {
  i2s_config_t cfg = {};
  cfg.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX);
  cfg.sample_rate = SAMPLE_RATE;
  cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT;
  cfg.channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT;
  cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;
  cfg.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
  cfg.dma_buf_count = 8;
  cfg.dma_buf_len = 256;
  cfg.use_apll = false;
  cfg.tx_desc_auto_clear = true;  // diam saat tidak ada data, bukan dengung

  i2s_pin_config_t pins = {};
  pins.mck_io_num = I2S_PIN_NO_CHANGE;
  pins.bck_io_num = PIN_AMP_BCLK;
  pins.ws_io_num = PIN_AMP_LRC;
  pins.data_out_num = PIN_AMP_DIN;
  pins.data_in_num = I2S_PIN_NO_CHANGE;

  return i2s_driver_install(PORT, &cfg, 0, nullptr) == ESP_OK && i2s_set_pin(PORT, &pins) == ESP_OK;
}

// Nada sinus; naik/turun 10 ms di awal dan akhir supaya tidak berbunyi "klik".
void playTone(float freq, int ms) {
  const int total = SAMPLE_RATE * ms / 1000;
  const int fade = SAMPLE_RATE / 100;
  int16_t frame[256 * 2];  // kiri + kanan
  float phase = 0, step = 2.0f * PI * freq / SAMPLE_RATE;
  for (int done = 0; done < total;) {
    int n = min(256, total - done);
    for (int i = 0; i < n; i++, done++) {
      float env = min(1.0f, min(done, total - done) / (float)fade);
      int16_t s = (int16_t)(sinf(phase) * VOLUME * env * 32767);
      frame[2 * i] = frame[2 * i + 1] = s;
      phase += step;
      if (phase > 2.0f * PI) phase -= 2.0f * PI;
    }
    size_t written;
    i2s_write(PORT, frame, n * 2 * sizeof(int16_t), &written, portMAX_DELAY);
  }
}

void playSilence(int ms) {
  int16_t frame[256 * 2] = {};
  for (int total = SAMPLE_RATE * ms / 1000; total > 0; total -= 256) {
    size_t written;
    i2s_write(PORT, frame, min(256, total) * 2 * sizeof(int16_t), &written, portMAX_DELAY);
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_BUTTON, INPUT_PULLUP);
  delay(500);
  if (!startI2S()) {
    Serial.println("I2S gagal dimulai, periksa pin");
    while (true) delay(1000);
  }
  Serial.println("Uji speaker siap");
}

void loop() {
  const char *names[] = {"Do", "Re", "Mi", "Fa", "Sol", "La", "Si", "Do'"};
  const float notes[] = {262, 294, 330, 349, 392, 440, 494, 523};
  for (int i = 0; i < 8; i++) {
    Serial.printf("Nada %s (%.0f Hz)\n", names[i], notes[i]);
    playTone(notes[i], 300);
    playSilence(50);
  }
  Serial.println("Nada 1 kHz, 1 detik");
  playTone(1000, 1000);

  Serial.println("Jeda 3 detik (tekan BOOT untuk mengulang)");
  for (int t = 0; t < 300 && digitalRead(PIN_BUTTON) == HIGH; t++) playSilence(10);
}
