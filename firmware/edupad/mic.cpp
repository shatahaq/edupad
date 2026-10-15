#include "mic.h"

#include <driver/i2s.h>
#include <esp_heap_caps.h>
#include <freertos/stream_buffer.h>
#include <math.h>

#include "config.h"

namespace {

constexpr i2s_port_t PORT = I2S_NUM_0;
constexpr size_t FRAMES = 256;  // 16 ms per blok

StreamBufferHandle_t buffer;
volatile bool capturing = false;
volatile float level = -90.0f;
volatile uint32_t dropped = 0;

void task(void *) {
  static int32_t raw[FRAMES];
  static int16_t pcm[FRAMES];
  float prevIn = 0, prevOut = 0;
  for (;;) {
    size_t bytes = 0;
    if (i2s_read(PORT, raw, sizeof raw, &bytes, portMAX_DELAY) != ESP_OK || bytes == 0) continue;
    size_t n = bytes / sizeof raw[0];
    float sumSquares = 0;
    for (size_t i = 0; i < n; i++) {
      // INMP441 mengirim 24 bit di bagian atas slot 32 bit.
      float x = (float)(raw[i] >> MIC_GAIN_SHIFT);
      float y = x - prevIn + 0.995f * prevOut;  // buang offset DC
      prevIn = x;
      prevOut = y;
      int32_t s = constrain((int32_t)y, -32768, 32767);
      pcm[i] = (int16_t)s;
      sumSquares += (float)s * s;
    }
    float rms = sqrtf(sumSquares / n);
    float db = 20.0f * log10f(fmaxf(rms, 1.0f) / 32768.0f);
    level = fmaxf(db, level - 1.5f);

    if (!capturing) continue;
    size_t size = n * sizeof pcm[0];
    if (xStreamBufferSpacesAvailable(buffer) >= size) {
      xStreamBufferSend(buffer, pcm, size, 0);
    } else {
      dropped += size;
    }
  }
}

}  // namespace

namespace mic {

bool begin() {
  // Penampung 96 KB di PSRAM bila ada (N16R8: Tools -> PSRAM -> OPI PSRAM), supaya RAM internal
  // tetap cukup untuk koneksi TLS. Tanpa PSRAM, dipakai RAM internal.
  static StaticStreamBuffer_t control;
  uint8_t *storage = (uint8_t *)heap_caps_malloc(AUDIO_BUFFER_BYTES + 1, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
  if (!storage) storage = (uint8_t *)malloc(AUDIO_BUFFER_BYTES + 1);
  if (!storage) return false;
  buffer = xStreamBufferCreateStatic(AUDIO_BUFFER_BYTES, 1, storage, &control);
  if (!buffer) return false;

  i2s_config_t cfg = {};
  cfg.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX);
  cfg.sample_rate = SAMPLE_RATE;
  cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT;
  cfg.channel_format = MIC_USE_RIGHT_CHANNEL ? I2S_CHANNEL_FMT_ONLY_RIGHT : I2S_CHANNEL_FMT_ONLY_LEFT;
  cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;
  cfg.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
  cfg.dma_buf_count = 8;
  cfg.dma_buf_len = FRAMES;
  cfg.use_apll = false;

  i2s_pin_config_t pins = {};
  pins.mck_io_num = I2S_PIN_NO_CHANGE;
  pins.bck_io_num = PIN_MIC_SCK;
  pins.ws_io_num = PIN_MIC_WS;
  pins.data_out_num = I2S_PIN_NO_CHANGE;
  pins.data_in_num = PIN_MIC_SD;

  if (i2s_driver_install(PORT, &cfg, 0, nullptr) != ESP_OK) return false;
  if (i2s_set_pin(PORT, &pins) != ESP_OK) return false;
  // Core 0: loop() (layar, jaringan) berjalan di core 1.
  return xTaskCreatePinnedToCore(task, "mic", 4096, nullptr, 5, nullptr, 0) == pdPASS;
}

void start() {
  capturing = false;
  delay(20);  // tunggu blok yang sedang ditulis selesai, lalu buang sisa rekaman lama
  uint8_t scrap[256];
  while (xStreamBufferReceive(buffer, scrap, sizeof scrap, 0) > 0) {
  }
  dropped = 0;
  capturing = true;
}

void stop() { capturing = false; }

size_t read(uint8_t *dst, size_t maxBytes, uint32_t waitMs) {
  return xStreamBufferReceive(buffer, dst, maxBytes, pdMS_TO_TICKS(waitMs));
}

size_t available() { return xStreamBufferBytesAvailable(buffer); }

float levelDbfs() { return level; }

uint32_t droppedBytes() { return dropped; }

}  // namespace mic
