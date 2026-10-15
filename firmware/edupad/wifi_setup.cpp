#include "wifi_setup.h"

#include <DNSServer.h>
#include <Preferences.h>
#include <WebServer.h>
#include <WiFi.h>

#include <algorithm>

#include "config.h"
#include "display.h"
#include "secrets.h"

namespace {

struct Network {
  String ssid;
  int rssi;
  bool open;
};

constexpr int MAX_NETWORKS = 15;
Network networks[MAX_NETWORKS];
int networkCount = 0;
String failed;  // jaringan yang gagal disambung, untuk layar dan halaman

WebServer server(80);
DNSServer dns;

bool tryConnect(const String &ssid, const String &password) {
  WiFi.disconnect();
  delay(100);
  WiFi.begin(ssid.c_str(), password.c_str());
  for (uint32_t started = millis(); millis() - started < WIFI_CONNECT_TIMEOUT_MS;) {
    wl_status_t status = WiFi.status();
    if (status == WL_CONNECTED) return true;
    if (status == WL_CONNECT_FAILED) break;  // sandi salah
    delay(200);
  }
  return false;
}

void loadSaved(String &ssid, String &password) {
  Preferences prefs;
  if (!prefs.begin("wifi", true)) return;  // belum pernah disimpan
  if (prefs.isKey("ssid")) {
    ssid = prefs.getString("ssid");
    password = prefs.getString("pass");
  }
  prefs.end();
}

void scan() {
  int found = WiFi.scanNetworks();
  int order[64];
  int n = std::min(found, 64);
  for (int i = 0; i < n; i++) order[i] = i;
  std::sort(order, order + n, [](int a, int b) { return WiFi.RSSI(a) > WiFi.RSSI(b); });

  networkCount = 0;
  for (int k = 0; k < n && networkCount < MAX_NETWORKS; k++) {
    int i = order[k];
    String ssid = WiFi.SSID(i);
    bool seen = ssid.isEmpty();  // jaringan tersembunyi
    for (int j = 0; j < networkCount && !seen; j++) seen = networks[j].ssid == ssid;
    if (!seen) networks[networkCount++] = {ssid, WiFi.RSSI(i), WiFi.encryptionType(i) == WIFI_AUTH_OPEN};
  }
  WiFi.scanDelete();
}

String html(const String &text) {
  String out;
  out.reserve(text.length());
  for (size_t i = 0; i < text.length(); i++) {
    char c = text[i];
    switch (c) {
      case '&': out += "&amp;"; break;
      case '<': out += "&lt;"; break;
      case '>': out += "&gt;"; break;
      case '"': out += "&quot;"; break;
      case '\'': out += "&#39;"; break;
      default: out += c;
    }
  }
  return out;
}

String page(const String &body) {
  return String(
             "<!doctype html><html lang=id><meta charset=utf-8>"
             "<meta name=viewport content='width=device-width,initial-scale=1'>"
             "<title>Wi-Fi EduPad</title><style>"
             "body{font-family:system-ui,sans-serif;max-width:480px;margin:auto;padding:16px;"
             "background:#f4f6f8;color:#1b1f23}h1{font-size:1.4em}"
             ".n{display:flex;justify-content:space-between;width:100%;padding:12px;margin:4px 0;"
             "border:1px solid #ccd;border-radius:8px;background:#fff;font-size:1em;color:inherit}"
             "label{display:block}input{width:100%;box-sizing:border-box;padding:12px;font-size:1em;"
             "margin:4px 0 12px;border:1px solid #99a;border-radius:8px}"
             ".s{width:100%;padding:14px;font-size:1.1em;background:#1f6feb;color:#fff;border:0;"
             "border-radius:8px}.e{background:#fde8e8;color:#9b1c1c;padding:10px;border-radius:8px}"
             ".m{color:#667}</style>") +
         body + "</html>";
}

void sendForm(const String &error = "") {
  String body = "<h1>Wi-Fi EduPad</h1>";
  if (failed.length()) body += "<p class=m>Gagal tersambung ke: " + html(failed) + "</p>";
  if (error.length()) body += "<p class=e>" + html(error) + "</p>";
  body += "<p>Pilih jaringan:</p>";
  for (int i = 0; i < networkCount; i++) {
    String name = html(networks[i].ssid);
    body += "<button type=button class=n data-s=\"" + name + "\" onclick=pick(this)><span>" + name +
            (networks[i].open ? "" : " &#128274;") + "</span><span class=m>" + networks[i].rssi +
            " dBm</span></button>";
  }
  if (networkCount == 0) body += "<p class=m>Tidak ada jaringan terdeteksi.</p>";
  body +=
      "<p><a href=/scan>Pindai ulang</a></p>"
      "<form method=post action=/save>"
      "<label>Nama Wi-Fi (SSID)<input name=ssid id=ssid maxlength=32 required></label>"
      "<label>Sandi<input name=pass id=pass type=password maxlength=63></label>"
      "<label class=m><input type=checkbox style=width:auto "
      "onclick=\"pass.type=this.checked?'text':'password'\"> Tampilkan sandi</label>"
      "<p><button class=s>Simpan &amp; sambungkan</button></p></form>"
      "<script>function pick(b){ssid.value=b.dataset.s;pass.focus()}</script>";
  server.send(200, "text/html; charset=utf-8", page(body));
}

void handleSave() {
  String ssid = server.arg("ssid");
  String password = server.arg("pass");
  if (ssid.isEmpty() || ssid.length() > 32) {
    sendForm("Nama Wi-Fi harus 1-32 karakter.");
    return;
  }
  if (password.length() && (password.length() < 8 || password.length() > 63)) {
    sendForm("Sandi Wi-Fi harus 8-63 karakter (kosongkan untuk jaringan terbuka).");
    return;
  }
  Preferences prefs;
  prefs.begin("wifi", false);
  prefs.putString("ssid", ssid);
  prefs.putString("pass", password);
  prefs.end();
  Serial.printf("[wifi] disimpan: %s\n", ssid.c_str());

  server.send(200, "text/html; charset=utf-8",
              page("<h1>Tersimpan</h1><p>EduPad menyambung ke <b>" + html(ssid) +
                   "</b>. Lihat layar perangkat. Bila gagal, hotspot " SETUP_AP_SSID
                   " muncul lagi.</p>"));
  display::message("Wi-Fi disimpan", ssid.c_str(), "Menyambung ulang...");
  delay(1500);  // biarkan halaman terkirim ke HP
  ESP.restart();
}

// Semua alamat lain (cek internet Android/iOS) diarahkan ke halaman ini, sehingga HP
// membuka halaman pengaturan sendiri setelah tersambung ke hotspot.
void redirectHome() {
  server.sendHeader("Location", "http://" + WiFi.softAPIP().toString() + "/", true);
  server.send(302, "text/plain", "");
}

}  // namespace

namespace wifisetup {

bool connect(void (*trying)(const char *ssid)) {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);  // tanpa power save: kirim/terima lebih cepat
  WiFi.setAutoReconnect(true);

  String ssid, password;
  loadSaved(ssid, password);
  if (ssid.length()) {
    trying(ssid.c_str());
    if (tryConnect(ssid, password)) return true;
    failed = ssid;
  }
  if (ssid != WIFI_SSID) {
    trying(WIFI_SSID);
    if (tryConnect(WIFI_SSID, WIFI_PASSWORD)) return true;
    if (failed.length()) failed += ", ";
    failed += WIFI_SSID;
  }
  return false;
}

void runPortal() {
  // Hentikan percobaan sambung ulang: STA yang berpindah kanal memutus HP dari hotspot.
  WiFi.setAutoReconnect(false);
  WiFi.disconnect();
  WiFi.mode(WIFI_AP_STA);  // STA tetap perlu untuk memindai jaringan
  scan();
  WiFi.softAP(SETUP_AP_SSID, SETUP_AP_PASSWORD);
  IPAddress ip = WiFi.softAPIP();
  dns.start(53, "*", ip);

  server.on("/", HTTP_GET, [] { sendForm(); });
  server.on("/save", HTTP_POST, handleSave);
  server.on("/scan", HTTP_GET, [] {
    scan();
    redirectHome();
  });
  server.onNotFound(redirectHome);
  server.begin();

  Serial.printf("[wifi] gagal: %s; hotspot %s di http://%s\n", failed.c_str(), SETUP_AP_SSID,
                ip.toString().c_str());
  display::portal(SETUP_AP_SSID, SETUP_AP_PASSWORD, ip.toString().c_str(), failed.c_str());

  for (;;) {
    dns.processNextRequest();
    server.handleClient();
    if (digitalRead(PIN_BUTTON) == LOW) {
      delay(50);
      if (digitalRead(PIN_BUTTON) == LOW) {
        display::message("Mencoba Wi-Fi lagi...");
        delay(300);
        ESP.restart();
      }
    }
    delay(2);
  }
}

}  // namespace wifisetup
