#pragma once
#include <WiFi.h>
#include <WebServer.h>
#include <DNSServer.h>
#include <Preferences.h>
#include <ESPmDNS.h>

// Configuration stays on the camera; the device token never enters the web form.
class CameraNetwork {
  WebServer web{80};
  DNSServer dns;
  Preferences preferences;
  String ssid, password, address, setupPassword, formToken, apName;
  bool accessPoint = false;
  uint32_t offlineSince = 0, connectedSince = 0, restartAt = 0;
  uint32_t lastSetupActivity = 0;

  String escape(String value) {
    value.replace("&", "&amp;"); value.replace("<", "&lt;");
    value.replace(">", "&gt;"); value.replace("\"", "&quot;");
    value.replace("'", "&#39;"); return value;
  }
  bool authorized() {
    lastSetupActivity = millis();
    if (web.authenticate("caretaker", setupPassword.c_str())) return true;
    web.requestAuthentication(); return false;
  }
  void openAccessPoint() {
    if (accessPoint) return;
    WiFi.mode(WIFI_AP_STA);
    if (!WiFi.softAP(apName.c_str(), setupPassword.c_str())) return;
    accessPoint = true;
    dns.start(53, "*", WiFi.softAPIP());
    Serial.println("Wi-Fi setup network: " + apName);
    Serial.println("Open http://192.168.4.1 (user: caretaker).");
  }
  void page() {
    if (!authorized()) return;
    web.sendHeader("Cache-Control", "no-store");
    web.sendHeader("X-Frame-Options", "DENY");
    String html = R"HTML(<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SAHAYAK Wi-Fi setup</title><style>
    *{box-sizing:border-box}body{margin:0;background:#f6f3fa;color:#30283d;font:16px system-ui,sans-serif;padding:24px}main{max-width:580px;margin:5vh auto;background:white;border:1px solid #e7dfef;border-radius:22px;padding:32px}h1{font-size:28px;margin-top:0}p{line-height:1.6;color:#665a72}label{display:block;margin:20px 0 8px;font-weight:600}input{width:100%;padding:14px;border:1px solid #cfc3dc;border-radius:10px;font:inherit}button{margin-top:26px;padding:14px 22px;border:0;border-radius:12px;background:#7850ac;color:white;font:inherit;cursor:pointer}small{display:block;margin-top:8px;color:#665a72}.status{background:#f6f3fa;padding:14px;border-radius:12px}</style><main><h1>SAHAYAK Wi-Fi setup</h1><p>Connect your camera to the same 2.4 GHz network as your laptop. Your people, memories and Telegram settings stay on the laptop.</p>)HTML";
    html += "<p class='status'>Wi-Fi: " + String(WiFi.status() == WL_CONNECTED ? "Connected" : "Disconnected") + "<br>Camera address: " + escape(WiFi.localIP().toString()) + "</p>";
    html += "<form method='post' action='/save'><input type='hidden' name='nonce' value='"+formToken+"'>";
    html += "<label for='ssid'>Wi-Fi name</label><input id='ssid' name='ssid' maxlength='32' required value='"+escape(ssid)+"' autocomplete='off'>";
    html += "<label for='password'>Wi-Fi password</label><input id='password' name='password' type='password' maxlength='63' autocomplete='new-password'><small>Leave blank to keep the saved password for the same network. For a different network, enter its password.</small>";
    html += "<label><input style='width:auto' type='checkbox' name='open' value='yes'> This network has no password</label>";
    html += "<label for='address'>SAHAYAK backend address</label><input id='address' name='address' type='url' required value='"+escape(address)+"' placeholder='https://your-backend.example.com'><small>Use your cloud HTTPS backend, or a local laptop HTTP address such as http://192.168.1.10:5000.</small>";
    html += "<button>Save and reconnect</button></form><p>After saving, the camera restarts. If it cannot connect within 30 seconds, this setup network returns so you can correct the settings.</p></main></html>";
    web.send(200, "text/html; charset=utf-8", html);
  }
  void save() {
    if (!authorized()) return;
    if (web.arg("nonce") != formToken) { web.send(403,"text/plain","Reload the setup page and try again."); return; }
    String nextSsid=web.arg("ssid"), nextPassword=web.arg("password"), nextAddress=web.arg("address");
    nextAddress.trim();
    while (nextAddress.endsWith("/")) nextAddress.remove(nextAddress.length()-1);
    bool https=nextAddress.startsWith("https://");
    String host=https ? nextAddress.substring(8) : (nextAddress.startsWith("http://") ? nextAddress.substring(7) : "");
    if (!nextSsid.length() || nextSsid.length()>32 || !host.length() || host.indexOf('/')>=0 || host.indexOf('@')>=0 || host.indexOf('?')>=0 || host.indexOf('#')>=0 || host.indexOf(' ')>=0 || host.indexOf('\r')>=0 || host.indexOf('\n')>=0 || host.indexOf('\\')>=0 || nextAddress.length()>180) {
      web.send(400,"text/plain","Enter a Wi-Fi name and an HTTPS cloud backend or private HTTP laptop address. Go back to correct the form."); return;
    }
    int portAt=host.indexOf(':');
    String hostIp=portAt<0 ? host : host.substring(0,portAt);
    String port=portAt<0 ? (https ? "443" : "80") : host.substring(portAt+1);
    bool validPort=port.length()>0 && port.length()<=5;
    for (unsigned i=0;i<port.length();i++) if (port[i]<'0' || port[i]>'9') validPort=false;
    IPAddress serverIp;
    bool privateIp=serverIp.fromString(hostIp) && (serverIp[0]==10 ||
      (serverIp[0]==192 && serverIp[1]==168) || (serverIp[0]==172 && serverIp[1]>=16 && serverIp[1]<=31) ||
      (serverIp[0]==169 && serverIp[1]==254));
    bool validDomain=hostIp.indexOf('.')>0 && !serverIp.fromString(hostIp) && hostIp.length()<=253;
    for (unsigned i=0;i<hostIp.length();i++) {
      char c=hostIp[i];
      if (!((c>='a' && c<='z') || (c>='A' && c<='Z') || (c>='0' && c<='9') || c=='.' || c=='-')) validDomain=false;
    }
    if (!(https ? validDomain : privateIp) || !validPort || port.toInt()<1 || port.toInt()>65535) {
      web.send(400,"text/plain","Use an HTTPS cloud hostname, or your laptop's private HTTP Wi-Fi IPv4 address with a valid port. Public HTTP is not allowed."); return;
    }
    if (web.arg("open")=="yes") nextPassword="";
    else if (!nextPassword.length() && nextSsid==ssid) nextPassword=password;
    else if (nextPassword.length()<8 || nextPassword.length()>63) {
      web.send(400,"text/plain","Enter an 8-63 character Wi-Fi password, or select the password-free network option. Go back to correct the form."); return;
    }
    // One NVS value prevents a power loss from mixing different configuration fields.
    String saved=nextSsid+'\n'+nextPassword+'\n'+nextAddress;
    if (nextSsid.indexOf('\n')>=0 || nextPassword.indexOf('\n')>=0 || preferences.putString("network",saved)==0) {
      web.send(500,"text/plain","Settings could not be saved. Please retry."); return;
    }
    web.sendHeader("Cache-Control","no-store");
    web.send(200,"text/html","<!doctype html><html lang='en'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Settings saved</title><body style='font:18px system-ui;padding:32px'><h1>Settings saved</h1><p>The camera is restarting. Reconnect your phone or laptop to your normal Wi-Fi.</p><p>If the camera cannot connect, join its SAHAYAK setup network again after 30 seconds and correct the settings.</p></body></html>");
    restartAt=millis()+1500;
  }
public:
  const String& serverBase() const { return address; }
  bool editing() const { return restartAt || (lastSetupActivity && millis()-lastSetupActivity<30000); }
  void begin(const char* defaultSsid,const char* defaultPassword,const char* defaultAddress) {
    preferences.begin("sahayak-wifi",false);
    ssid=defaultSsid; password=defaultPassword; address=defaultAddress;
    String saved=preferences.getString("network","");
    int first=saved.indexOf('\n'), second=saved.indexOf('\n',first+1);
    if (first>0 && second>first) { ssid=saved.substring(0,first); password=saved.substring(first+1,second); address=saved.substring(second+1); }
    // Apply a newly installed cloud destination once, retaining the saved Wi-Fi.
    // Later edits through the setup page remain authoritative until another
    // cloud destination is compiled and installed.
    String cloudDefault(defaultAddress);
    if (cloudDefault.startsWith("https://") && preferences.getString("cloud-default","")!=cloudDefault) {
      address=cloudDefault;
      preferences.putString("network",ssid+"\n"+password+"\n"+address);
      preferences.putString("cloud-default",cloudDefault);
    }
    setupPassword=preferences.getString("setup-pass","");
    if (setupPassword.length()<12) {
      char generated[25]; snprintf(generated,sizeof(generated),"%08lx%08lx",(unsigned long)esp_random(),(unsigned long)esp_random());
      setupPassword=generated; preferences.putString("setup-pass",setupPassword);
    }
    char suffix[9]; snprintf(suffix,sizeof(suffix),"%06lx",(unsigned long)(ESP.getEfuseMac()&0xffffff));
    apName="SAHAYAK-Setup-"+String(suffix);
    formToken=String(esp_random(),HEX)+String(esp_random(),HEX);
    Serial.println("Setup password: "+setupPassword);
    Serial.println("Setup username: caretaker");
    WiFi.persistent(false); WiFi.mode(WIFI_STA); WiFi.setSleep(false); WiFi.setAutoReconnect(true);
    WiFi.setHostname("sahayak-camera");
    WiFi.begin(ssid.c_str(),password.c_str());
    offlineSince=millis();
    web.on("/",HTTP_GET,[this](){page();});
    web.on("/save",HTTP_POST,[this](){save();});
    web.onNotFound([this](){ web.sendHeader("Location",accessPoint ? "http://192.168.4.1/" : "/"); web.send(302,"text/plain",""); });
    web.begin();
    if (!ssid.length() || ssid=="YOUR_WIFI_NAME") openAccessPoint();
  }
  void tick() {
    web.handleClient();
    if (accessPoint) dns.processNextRequest();
    uint32_t current=millis();
    if (restartAt && (int32_t)(current-restartAt)>=0) { ESP.restart(); return; }
    if (WiFi.status()==WL_CONNECTED) {
      if (!connectedSince) {
        connectedSince=current;
        Serial.println("Camera setup address: http://"+WiFi.localIP().toString());
        if (MDNS.begin("sahayak-camera")) MDNS.addService("http","tcp",80);
      }
      offlineSince=0;
      if (accessPoint && current-connectedSince>60000) {
        dns.stop(); WiFi.softAPdisconnect(true); WiFi.mode(WIFI_STA); accessPoint=false;
      }
    } else {
      if (connectedSince) MDNS.end();
      connectedSince=0;
      if (!offlineSince) offlineSince=current;
      if (current-offlineSince>=30000) openAccessPoint();
    }
  }
};
