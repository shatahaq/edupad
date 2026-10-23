#include "adpcm.h"

namespace {

const int16_t STEP[89] = {
    7,     8,     9,     10,    11,    12,    13,    14,    16,    17,    19,    21,    23,
    25,    28,    31,    34,    37,    41,    45,    50,    55,    60,    66,    73,    80,
    88,    97,    107,   118,   130,   143,   157,   173,   190,   209,   230,   253,   279,
    307,   337,   371,   408,   449,   494,   544,   598,   658,   724,   796,   876,   963,
    1060,  1166,  1282,  1411,  1552,  1707,  1878,  2066,  2272,  2499,  2749,  3024,  3327,
    3660,  4026,  4428,  4871,  5358,  5894,  6484,  7132,  7845,  8630,  9493,  10442, 11487,
    12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767};
const int8_t INDEX[16] = {-1, -1, -1, -1, 2, 4, 6, 8, -1, -1, -1, -1, 2, 4, 6, 8};

}  // namespace

namespace adpcm {

size_t decodeBlock(const uint8_t *block, size_t size, int16_t *out) {
  if (size < 4) return 0;
  size = min(size, BLOCK_BYTES);
  int predictor = (int16_t)(block[0] | block[1] << 8);
  int index = min((int)block[2], 88);
  size_t n = 0;
  for (size_t i = 4; i < size; i++) {
    for (int shift = 0; shift <= 4; shift += 4) {  // nibble rendah dulu
      int code = (block[i] >> shift) & 0x0F;
      int step = STEP[index];
      int diff = step >> 3;
      if (code & 4) diff += step;
      if (code & 2) diff += step >> 1;
      if (code & 1) diff += step >> 2;
      predictor = constrain(predictor + ((code & 8) ? -diff : diff), -32768, 32767);
      index = constrain(index + INDEX[code], 0, 88);
      out[n++] = (int16_t)predictor;
    }
  }
  return n;
}

}  // namespace adpcm
