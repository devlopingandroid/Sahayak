#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>
#include <time.h>
#include "config.h"
#include "WifiSetup.h"
#include "CloudTrust.h"

// AI Thinker ESP32-CAM. Camera only; microphone and speaker use the laptop.
static const char* DEVICE_ID = "esp32-cam";
static uint32_t lastCapture = 0, lastConfig = 0, lastReconnect = 0;
static uint32_t intervalMs = 10000;
static bool captureEnabled = true;
static CameraNetwork network;
static HTTPClient backendHttp;
static WiFiClient localClient;
static WiFiClientSecure cloudClient;
static String connectionBase;

bool beginBackend(const char* path) {
  String base = network.serverBase();
  if (base != connectionBase) {
    backendHttp.end(); localClient.stop(); cloudClient.stop();
    connectionBase = base;
  }
  backendHttp.setReuse(true);
  backendHttp.setConnectTimeout(6000);
  if (base.startsWith("https://")) {
    static bool clockRequested = false;
    if (!clockRequested) {
      configTime(0, 0, "pool.ntp.org", "time.google.com");
      clockRequested = true;
    }
    // Certificate validity must be checked against a synchronized clock.
    if (time(nullptr) < 1700000000) return false;
    cloudClient.setCACert(SAHAYAK_CLOUD_ROOTS);
    cloudClient.setHandshakeTimeout(10);
    return backendHttp.begin(cloudClient, base + path);
  }
  return backendHttp.begin(localClient, base + path);
}

bool startCamera() {
  camera_config_t config = {};
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = 5; config.pin_d1 = 18; config.pin_d2 = 19; config.pin_d3 = 21;
  config.pin_d4 = 36; config.pin_d5 = 39; config.pin_d6 = 34; config.pin_d7 = 35;
  config.pin_xclk = 0; config.pin_pclk = 22;
  config.pin_vsync = 25; config.pin_href = 23;
  config.pin_sccb_sda = 26; config.pin_sccb_scl = 27;
  config.pin_pwdn = 32; config.pin_reset = -1;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = psramFound() ? FRAMESIZE_VGA : FRAMESIZE_QVGA;
  config.jpeg_quality = 12;
  config.fb_count = psramFound() ? 2 : 1;
  config.grab_mode = psramFound() ? CAMERA_GRAB_LATEST : CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = psramFound() ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;
  esp_err_t result = esp_camera_init(&config);
  if (result != ESP_OK) { Serial.printf("Camera initialization failed: 0x%x\n", result); return false; }
  return true;
}

void pollConfig() {
  HTTPClient& http = backendHttp;
  http.setTimeout(4000);
  if (!beginBackend("/api/device-config")) return;
  http.addHeader("X-Device-Token", DEVICE_TOKEN);
  int code = http.GET();
  if (code == 200) {
    String value = http.getString();
    // Parse the two scalar configuration fields without another firmware dependency.
    int key = value.indexOf("\"capture_interval\"");
    int colon = value.indexOf(':', key);
    if (key >= 0 && colon >= 0) {
      int seconds = value.substring(colon + 1).toInt();
      if (seconds >= 1 && seconds <= 60) intervalMs = seconds * 1000UL;
    }
    key = value.indexOf("\"capture_enabled\"");
    colon = value.indexOf(':', key);
    if (key >= 0 && colon >= 0) {
      String flag = value.substring(colon + 1); flag.trim();
      captureEnabled = flag.startsWith("true");
    }
  } else Serial.printf("Configuration HTTP status: %d\n", code);
  http.end();
}

void sendFrame() {
  camera_fb_t* frame = esp_camera_fb_get();
  if (!frame) { Serial.println("No camera frame available."); return; }
  HTTPClient& http = backendHttp;
  http.setTimeout(12000);
  if (beginBackend("/upload")) {
    http.addHeader("Content-Type", "image/jpeg");
    http.addHeader("X-Device-Token", DEVICE_TOKEN);
    http.addHeader("X-Device-Id", DEVICE_ID);
    http.addHeader("X-Wifi-Setup", "1");
    // Binary JPEG avoids Base64 copies and uses less memory and bandwidth.
    int code = http.POST(frame->buf, frame->len);
    Serial.printf("Frame: %u bytes, HTTP: %d\n", (unsigned)frame->len, code);
    if (code < 0) Serial.println(http.errorToString(code));
    if (code == 401) Serial.println("Check DEVICE_TOKEN in config.h.");
    if (code == 429) Serial.println("Laptop busy; will retry with the next fresh frame.");
    if (code > 0) http.getString(); // Consume the reply to reuse the TLS connection.
    http.end();
  }
  esp_camera_fb_return(frame);
}

void setup() {
  Serial.begin(115200);
  delay(700);
  Serial.println("SAHAYAK camera starting. Laptop handles audio and recognition.");
  if (!startCamera()) { delay(5000); ESP.restart(); }
  network.begin(WIFI_SSID, WIFI_PASSWORD, SERVER_BASE);
}

void loop() {
  network.tick();
  // Give setup requests priority over synchronous camera uploads/config polling.
  if (network.editing()) { delay(5); return; }
  uint32_t current = millis();
  if (WiFi.status() != WL_CONNECTED) {
    if (current - lastReconnect > 15000) {
      lastReconnect = current;
      Serial.println("Waiting for Wi-Fi; reconnecting.");
      WiFi.reconnect();
    }
    delay(20); return;
  }
  if (lastConfig == 0 || current - lastConfig >= 15000) {
    lastConfig = current; pollConfig();
  }
  if (captureEnabled && current - lastCapture >= intervalMs) {
    lastCapture = current; sendFrame();
  }
  delay(20);
}
