#include "api.h"

#include <WiFi.h>
#include <WiFiClientSecure.h>

#include "certs.h"
#include "config.h"
#include "secrets.h"

namespace {

#if EDUPAD_TLS
WiFiClientSecure conn;
#else
WiFiClient conn;
#endif

constexpr size_t MAX_RESPONSE_BYTES = 32 * 1024;
constexpr size_t CHUNK_MAX = 4096;
constexpr uint32_t IDLE_TIMEOUT_MS = 15000;  // tanpa data selama ini = koneksi dianggap putus
String audioReport;  // api::reportAudio(), terkirim di permintaan berikutnya

struct Head {
  int status = 0;
  long length = -1;
  bool chunked = false;
  bool close = false;
  bool adpcm = false;
};

enum class BodyEnd { Complete, Stopped, Broken };

bool expired(uint32_t deadline) { return (int32_t)(millis() - deadline) >= 0; }

String hostHeader() {
  bool defaultPort = EDUPAD_PORT == (EDUPAD_TLS ? 443 : 80);
  return defaultPort ? String(EDUPAD_HOST) : String(EDUPAD_HOST) + ":" + EDUPAD_PORT;
}

// `error` berisi penyebab singkat untuk layar (DNS / koneksi / TLS); rinciannya di Serial.
bool connectServer(String &error) {
  conn.stop();
  IPAddress ip;
  if (!WiFi.hostByName(EDUPAD_HOST, ip)) {
    error = String("DNS gagal: ") + EDUPAD_HOST;
    Serial.printf("[api] DNS %s gagal (DNS Wi-Fi: %s)\n", EDUPAD_HOST, WiFi.dnsIP().toString().c_str());
    return false;
  }
  if (conn.connect(EDUPAD_HOST, EDUPAD_PORT)) return true;
  error = String("gagal ke ") + ip.toString() + ":" + EDUPAD_PORT;
#if EDUPAD_TLS
  char reason[100];
  int code = conn.lastError(reason, sizeof reason);
  if (code != 0) {
    Serial.printf("[api] TLS -0x%04X: %s\n", -code, reason);
    error = String("TLS -0x") + String(-code, HEX) + " " + reason;
  }
#endif
  Serial.printf("[api] %s | heap bebas %u, blok terbesar %u, PSRAM bebas %u\n", error.c_str(),
                (unsigned)ESP.getFreeHeap(), (unsigned)ESP.getMaxAllocHeap(), (unsigned)ESP.getFreePsram());
  return false;
}

bool sendAll(const uint8_t *data, size_t size) {
  while (size > 0) {
    size_t sent = conn.write(data, size);
    if (sent == 0) return false;
    data += sent;
    size -= sent;
  }
  return true;
}

bool sendText(const String &text) { return sendAll((const uint8_t *)text.c_str(), text.length()); }

bool sendHead(const char *method, const String &path, const char *extraHeaders, bool keepAlive) {
  String head = String(method) + " " + path + " HTTP/1.1\r\n";
  head += "Host: " + hostHeader() + "\r\n";
  head += "Authorization: Bearer " EDUPAD_DEVICE_TOKEN "\r\n";
  head += "User-Agent: EduPad-ESP32/1.0\r\n";
  // Status perangkat untuk dashboard (Monitoring -> Perangkat).
  head += "X-Device-Id: " + WiFi.macAddress() + "\r\n";
  head += "X-Device-RSSI: " + String(WiFi.RSSI()) + "\r\n";
  head += "X-Device-Uptime: " + String(millis() / 1000) + "\r\n";
  head += "X-Device-Heap: " + String(ESP.getFreeHeap()) + "\r\n";
  head += "X-Firmware: " FIRMWARE_VERSION "\r\n";
  if (!audioReport.isEmpty()) {
    head += "X-Audio-Report: " + audioReport + "\r\n";
    audioReport = "";
  }
  head += keepAlive ? "Connection: keep-alive\r\n" : "Connection: close\r\n";
  head += extraHeaders;
  head += "\r\n";
  return sendText(head);
}

// Satu baris tanpa CRLF; false bila koneksi putus atau waktu habis.
bool readLine(String &line, uint32_t deadline) {
  line = "";
  while (!expired(deadline)) {
    while (conn.available()) {
      char c = conn.read();
      if (c == '\n') {
        if (line.endsWith("\r")) line.remove(line.length() - 1);
        return true;
      }
      if (line.length() >= 1024) return false;
      line += c;
    }
    if (!conn.connected()) return false;
    delay(1);
  }
  return false;
}

// Baca hingga `size` byte yang sudah tersedia. >0 = jumlah byte, 0 = waktu habis, -1 = ditutup.
int readSome(uint8_t *buf, size_t size, uint32_t idleMs) {
  uint32_t deadline = millis() + idleMs;
  while (!expired(deadline)) {
    if (conn.available()) {
      int n = conn.read(buf, size);
      if (n > 0) return n;
    } else if (!conn.connected()) {
      return -1;
    }
    delay(1);
  }
  return 0;
}

// Tunggu byte pertama jawaban (server sedang memproses).
bool waitFirstByte(uint32_t timeoutMs, void (*waiting)(uint32_t), String &error) {
  uint32_t started = millis(), lastTick = 0;
  while (!conn.available()) {
    if (!conn.connected()) {
      error = "koneksi ditutup server";
      return false;
    }
    if (millis() - started >= timeoutMs) {
      error = "server tidak menjawab";
      return false;
    }
    if (waiting && millis() - lastTick >= 200) {
      lastTick = millis();
      waiting(lastTick - started);
    }
    delay(10);
  }
  return true;
}

bool readHead(Head &head, String &error) {
  uint32_t deadline = millis() + IDLE_TIMEOUT_MS;
  String line;
  if (!readLine(line, deadline) || !line.startsWith("HTTP/")) {
    error = "jawaban HTTP rusak";
    return false;
  }
  head = Head();
  head.status = line.substring(line.indexOf(' ') + 1).toInt();
  head.close = line.startsWith("HTTP/1.0");
  while (true) {
    if (!readLine(line, deadline)) {
      error = "header jawaban terpotong";
      return false;
    }
    if (line.isEmpty()) return true;
    line.toLowerCase();
    if (line.startsWith("content-length:")) head.length = line.substring(15).toInt();
    if (line.startsWith("transfer-encoding:") && line.indexOf("chunked") >= 0) head.chunked = true;
    if (line.startsWith("connection:") && line.indexOf("close") >= 0) head.close = true;
    if (line.startsWith("x-audio-format:") && line.indexOf("adpcm") >= 0) head.adpcm = true;
  }
}

// Badan jawaban diberikan ke `sink` per potongan (Content-Length, chunked, atau sampai ditutup).
template <typename Sink>
BodyEnd readBody(const Head &head, Sink sink) {
  static uint8_t buf[1024];
  String line;
  auto pass = [&](long size) -> BodyEnd {
    while (size > 0) {
      int n = readSome(buf, min((size_t)size, sizeof buf), IDLE_TIMEOUT_MS);
      if (n <= 0) return BodyEnd::Broken;
      if (!sink(buf, (size_t)n)) return BodyEnd::Stopped;
      size -= n;
    }
    return BodyEnd::Complete;
  };

  if (head.chunked) {
    while (true) {
      if (!readLine(line, millis() + IDLE_TIMEOUT_MS)) return BodyEnd::Broken;
      long size = strtol(line.c_str(), nullptr, 16);
      if (size < 0) return BodyEnd::Broken;
      if (size == 0) {
        while (readLine(line, millis() + IDLE_TIMEOUT_MS) && !line.isEmpty()) {
        }  // trailer
        return BodyEnd::Complete;
      }
      BodyEnd end = pass(size);
      if (end != BodyEnd::Complete) return end;
      if (!readLine(line, millis() + IDLE_TIMEOUT_MS)) return BodyEnd::Broken;  // CRLF penutup
    }
  }
  if (head.length >= 0) return pass(head.length);
  while (true) {  // tanpa panjang: sampai koneksi ditutup
    int n = readSome(buf, sizeof buf, IDLE_TIMEOUT_MS);
    if (n < 0) return BodyEnd::Complete;
    if (n == 0) return BodyEnd::Broken;
    if (!sink(buf, (size_t)n)) return BodyEnd::Stopped;
  }
}

// Jawaban JSON utuh. Koneksi tetap terbuka kecuali server menutupnya atau terjadi error.
api::Response readResponse(uint32_t timeoutMs, void (*waiting)(uint32_t)) {
  api::Response res;
  Head head;
  if (!waitFirstByte(timeoutMs, waiting, res.error) || !readHead(head, res.error)) {
    conn.stop();
    return res;
  }
  bool tooBig = false;
  BodyEnd end = readBody(head, [&](const uint8_t *data, size_t size) {
    if (res.body.length() + size > MAX_RESPONSE_BYTES) {
      tooBig = true;
      return false;
    }
    res.body.concat((const char *)data, size);
    return true;
  });
  if (end != BodyEnd::Complete) {
    res.error = tooBig ? "jawaban terlalu besar" : "badan jawaban terpotong";
    conn.stop();
    return res;
  }
  if (head.close) conn.stop();
  res.status = head.status;
  return res;
}

}  // namespace

namespace api {

void begin() {
#if EDUPAD_TLS
  conn.setCACert(ROOT_CA_PEM);
  conn.setHandshakeTimeout(15);
#endif
}

Response health() {
  Response res;
  if (!connectServer(res.error)) return res;
  if (!sendHead("GET", "/v1/health", "", false)) {
    res.error = "gagal mengirim permintaan";
  } else {
    res = readResponse(10000, nullptr);
  }
  conn.stop();
  return res;
}

Response get(const char *path, uint32_t timeoutMs) {
  Response res;
  if (!connectServer(res.error)) return res;
  if (!sendHead("GET", path, "", true)) {
    res.error = "gagal mengirim permintaan";
    conn.stop();
    return res;
  }
  return readResponse(timeoutMs, nullptr);
}

bool askOpen(bool newSession, String &error) {
  if (!connectServer(error)) return false;
  if (sendHead("POST", newSession ? "/v1/ask?new=1" : "/v1/ask",
               "Content-Type: application/octet-stream\r\n"
               "Transfer-Encoding: chunked\r\n",
               true)) {
    return true;
  }
  error = "gagal mengirim permintaan";
  conn.stop();
  return false;
}

bool askWrite(const uint8_t *pcm, size_t size) {
  // Header chunk + data + CRLF dalam satu tulis supaya jadi satu record TLS.
  static uint8_t frame[CHUNK_MAX + 16];
  while (size > 0) {
    size_t n = min(size, CHUNK_MAX);
    int head = snprintf((char *)frame, 16, "%X\r\n", (unsigned)n);
    memcpy(frame + head, pcm, n);
    memcpy(frame + head + n, "\r\n", 2);
    if (!sendAll(frame, head + n + 2)) return false;
    pcm += n;
    size -= n;
  }
  return true;
}

Response askFinish(void (*waiting)(uint32_t)) {
  if (!sendText("0\r\n\r\n")) {
    conn.stop();
    Response res;
    res.error = "koneksi terputus saat mengirim";
    return res;
  }
  return readResponse(RESPONSE_TIMEOUT_MS, waiting);  // koneksi dipakai lagi untuk audio
}

Response askSalvage() {
  Response res = readResponse(3000, nullptr);
  conn.stop();
  return res;
}

AudioResult streamAudio(const char *path, bool (*sink)(const uint8_t *, size_t)) {
  AudioResult result;
  Head head;
  // Coba koneksi yang masih terbuka dulu; bila ternyata sudah ditutup server/proxy, sambung ulang.
  for (int attempt = 0; attempt < 2; attempt++) {
    bool reused = conn.connected();
    if (!reused && !connectServer(result.error)) return result;
    if (sendHead("GET", path, "", true) && waitFirstByte(20000, nullptr, result.error) &&
        readHead(head, result.error)) {
      break;
    }
    conn.stop();
    if (!reused) {
      if (result.error.isEmpty()) result.error = "gagal mengirim permintaan";
      return result;
    }
    result.error = "";
  }

  if (head.status != 200) {  // badan berisi JSON error; cukup dibuang
    readBody(head, [](const uint8_t *, size_t) { return true; });
    if (head.close) conn.stop();
    result.status = head.status;
    return result;
  }
  result.adpcm = head.adpcm;
  BodyEnd end = readBody(head, [&](const uint8_t *data, size_t size) {
    result.bytes += size;
    return sink(data, size);
  });
  result.status = head.status;
  result.complete = end == BodyEnd::Complete;
  result.stopped = end == BodyEnd::Stopped;
  if (!result.complete) {
    if (!result.stopped) result.error = "audio terputus";
    conn.stop();  // sisa audio belum terbaca: koneksi tidak bisa dipakai lagi
  } else if (head.close) {
    conn.stop();
  }
  return result;
}

void reportAudio(const String &report) { audioReport = report; }

}  // namespace api
