#include "lang.h"

#include <Arduino.h>
#include <Preferences.h>

namespace {

volatile bool en = false;  // dibaca task gambar di core lain

}  // namespace

namespace lang {

void begin() {
  Preferences prefs;
  if (prefs.begin("lang", true)) {  // false bila belum pernah disimpan
    en = prefs.getBool("en", false);
    prefs.end();
  }
}

void update(JsonVariantConst doc) {
  const char *code = doc["language"] | "";
  if (!*code) return;  // server lama tanpa `language`
  bool value = !strcmp(code, "en");
  if (value == en) return;
  en = value;
  Preferences prefs;
  if (prefs.begin("lang", false)) {
    prefs.putBool("en", value);
    prefs.end();
  }
  Serial.printf("[lang] layar %s\n", value ? "English" : "Indonesia");
}

bool english() { return en; }

}  // namespace lang
