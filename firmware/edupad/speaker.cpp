#include "speaker.h"

#include <driver/i2s.h>
#include <math.h>

#include "config.h"

namespace {

constexpr i2s_port_t PORT = I2S_NUM_1;  // I2S_NUM_0 dipakai mic
constexpr size_t FRAMES = 256;
constexpr size_t DMA_BUFS = 8;
constexpr uint32_t DMA_SAMPLES = DMA_BUFS * FRAMES;  // sudah dikirim ke I2S tapi belum terdengar
constexpr size_t PREBUFFER_BYTES = SAMPLE_RATE * 2 * SPEAKER_PREBUFFER_MS / 1000;
constexpr int32_t GAIN = (int32_t)(SPEAKER_VOLUME * 256);  // fixed point 8 bit

alignas(4) uint8_t prebuffer[PREBUFFER_BYTES];
size_t prebuffered = 0;
bool playing = false;  // prebuffer sudah dilepas, data berikutnya langsung ke I2S
uint8_t carry = 0;
bool hasCarry = false;
volatile uint32_t samplesOut = 0;  // sampel yang sudah masuk I2S sejak audio mulai
volatile float levelDb = -90;      // keras suara blok terakhir yang masuk I2S

// Sampel mono -> kiri+kanan (MAX98357A memutar rata-rata keduanya), dengan volume.
void output(const int16_t *samples, size_t count) {
  static int16_t frame[FRAMES * 2];
  while (count > 0) {
    size_t n = min(count, FRAMES);
    float energy = 0;
    for (size_t i = 0; i < n; i++) {
      int32_t s = (int32_t)samples[i] * GAIN / 256;
      frame[2 * i] = frame[2 * i + 1] = (int16_t)constrain(s, -32768, 32767);
      energy += (float)samples[i] * samples[i];
    }
    size_t written;
    i2s_write(PORT, frame, n * 2 * sizeof(int16_t), &written, portMAX_DELAY);
    levelDb = energy > 0 ? 10 * log10f(energy / n / (32768.0f * 32768.0f)) : -90;
    samplesOut += n;
    samples += n;
    count -= n;
  }
}

// Byte yang sudah genap (sampel utuh), sesudah prebuffer.
void play(const uint8_t *data, size_t size) {
  if (!playing) {
    size_t take = min(size, PREBUFFER_BYTES - prebuffered);
    memcpy(prebuffer + prebuffered, data, take);
    prebuffered += take;
    data += take;
    size -= take;
    if (prebuffered < PREBUFFER_BYTES) return;
    playing = true;
    output((const int16_t *)prebuffer, prebuffered / 2);
    prebuffered = 0;
  }
  // `data` bisa tidak rata 2 byte: salin per blok supaya aman dibaca sebagai int16_t.
  static int16_t aligned[FRAMES];
  while (size > 0) {
    size_t n = min(size, sizeof aligned);
    memcpy(aligned, data, n);
    output(aligned, n / 2);
    data += n;
    size -= n;
  }
}

void reset() {
  prebuffered = 0;
  playing = false;
  hasCarry = false;
  samplesOut = 0;
  levelDb = -90;
}

}  // namespace

namespace speaker {

bool begin() {
  i2s_config_t cfg = {};
  cfg.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX);
  cfg.sample_rate = SAMPLE_RATE;
  cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT;
  cfg.channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT;
  cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;
  cfg.intr_alloc_flags = ESP_INTR_FLAG_LEVEL1;
  cfg.dma_buf_count = DMA_BUFS;  // 8 x 256 frame = 0,13 s; selebihnya ditampung prebuffer
  cfg.dma_buf_len = FRAMES;
  cfg.use_apll = false;
  cfg.tx_desc_auto_clear = true;  // diam saat data habis, bukan mengulang sisa buffer

  i2s_pin_config_t pins = {};
  pins.mck_io_num = I2S_PIN_NO_CHANGE;
  pins.bck_io_num = PIN_AMP_BCLK;
  pins.ws_io_num = PIN_AMP_LRC;
  pins.data_out_num = PIN_AMP_DIN;
  pins.data_in_num = I2S_PIN_NO_CHANGE;

  return i2s_driver_install(PORT, &cfg, 0, nullptr) == ESP_OK && i2s_set_pin(PORT, &pins) == ESP_OK;
}

void write(const uint8_t *pcm, size_t size) {
  if (size == 0) return;
  if (hasCarry) {
    uint8_t pair[2] = {carry, pcm[0]};
    hasCarry = false;
    play(pair, 2);
    pcm++;
    size--;
  }
  if (size % 2) {
    carry = pcm[size - 1];
    hasCarry = true;
    size--;
  }
  if (size) play(pcm, size);
}

void finish() {
  if (!playing && prebuffered) output((const int16_t *)prebuffer, prebuffered / 2);
  reset();
}

void stop() {
  i2s_zero_dma_buffer(PORT);
  reset();
}

void chime() {
  // dua nada (E6 lalu C6) dengan harmoni oktaf dan dengung yang meluruh, seperti bel pintu
  static const struct {
    float freq, seconds;
  } notes[] = {{1318.5f, 0.32f}, {1046.5f, 0.6f}};
  static int16_t block[FRAMES];
  for (const auto &note : notes) {
    int total = (int)(note.seconds * SAMPLE_RATE);
    for (int i = 0; i < total; i += FRAMES) {
      int n = min((int)FRAMES, total - i);
      for (int k = 0; k < n; k++) {
        float t = (float)(i + k) / SAMPLE_RATE;
        float env = expf(-t * 5.5f) * fminf(1.0f, t * 400);  // serangan 2,5 ms lalu meluruh
        float wave = sinf(2 * PI * note.freq * t) + 0.3f * sinf(4 * PI * note.freq * t);
        block[k] = (int16_t)(wave * env * 9000);
      }
      write((const uint8_t *)block, n * 2);
    }
  }
  finish();
}

float level() { return levelDb; }

uint32_t positionMs() {
  uint32_t n = samplesOut;
  return n > DMA_SAMPLES ? (uint32_t)((uint64_t)(n - DMA_SAMPLES) * 1000 / SAMPLE_RATE) : 0;
}

}  // namespace speaker
