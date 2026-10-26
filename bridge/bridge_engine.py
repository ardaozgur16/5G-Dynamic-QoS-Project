# Dosya: bridge_engine.py

import os
import time
import json
import requests

try:
    import yaml
except ImportError:
    print("[HATA] PyYAML kütüphanesi bulunamadı. Yükleyin: pip install pyyaml")
    exit(1)


class QoSBridgeEngine:
    def __init__(self, load_file_path="current_load.json", policy_file_path="policies.yaml", state_file_path="active_policy.json"):
        # Dosya yolu ../sim/current_load.json ise otomatik yakalar
        if not os.path.exists(load_file_path) and os.path.exists("../sim/current_load.json"):
            self.load_file_path = "../sim/current_load.json"
        else:
            self.load_file_path = load_file_path

        self.policy_file_path = policy_file_path
        self.state_file_path = state_file_path

        # 5G Core PCF REST API URL
        self.pcf_api_url = "http://127.0.0.1:8000/npcf-smpolicy/v1/policies"
        self.current_applied_policy = "normal"

        # Politikaları yükle
        self.policies = self.load_policies()

        # Simülatörün okuyabilmesi için başlangıç politikasını yaz
        self._write_state(self.current_applied_policy)

    def load_policies(self):
        """policies.yaml dosyasından eşikleri ve profilleri okur."""
        try:
            with open(self.policy_file_path, "r", encoding="utf-8") as file:
                policies = yaml.safe_load(file)
                print("[KÖPRÜ] Politikalar başarıyla yüklendi.")
                return policies
        except FileNotFoundError:
            print(f"[HATA] Politika dosyası bulunamadı: {self.policy_file_path}")
            return {
                "thresholds": {"high_load_percent": 80.0, "recovery_load_percent": 70.0},
                "profiles": {
                    "normal": {"5qi": 9, "mbr_dl": "50 Mbps", "mbr_ul": "20 Mbps"},
                    "throttled": {"5qi": 9, "mbr_dl": "2 Mbps", "mbr_ul": "1 Mbps"}
                },
                "target_ues": ["imsi-208930000000003"]
            }

    def _write_state(self, policy_name):
        """Simülatörün geri besleme (closed-loop) alabilmesi için aktif durumu JSON'a yazar."""
        try:
            temp_path = self.state_file_path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump({"active_policy": policy_name}, f)
            os.replace(temp_path, self.state_file_path)
        except Exception:
            pass

    def get_current_cell_load(self):
        """Sionna simülatörünün ürettiği yük verisini okur."""
        if not os.path.exists(self.load_file_path):
            return None

        try:
            with open(self.load_file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
                return data.get("cell_load_percent", 0.0)
        except (json.JSONDecodeError, PermissionError):
            return None

    def send_pcf_update(self, target_ue, policy_name, qos_params):
        """PCF'e 3GPP SBI formatında HTTP POST atar."""
        payload = {
            "supi": target_ue,
            "trigger": "CELL_CONGESTION" if policy_name == "throttled" else "CONGESTION_MITIGATED",
            "policy_decision": {
                "qos_profile": {
                    "5qi": qos_params["5qi"],
                    "maxbrDl": qos_params["mbr_dl"],
                    "maxbrUl": qos_params["mbr_ul"]
                }
            }
        }

        try:
            response = requests.post(self.pcf_api_url, json=payload, timeout=2.0)
            if response.status_code in [200, 201]:
                print(f"  [>] SBI İSTEĞİ BAŞARILI: {target_ue} -> {policy_name.upper()} ({qos_params['mbr_dl']})")
            else:
                print(f"  [X] SBI İSTEĞİ BAŞARISIZ: Sunucu yanıt kodu {response.status_code}")
        except requests.exceptions.RequestException:
            print(f"  [!] PCF BAĞLANTI UYARISI: Sunucuya ulaşılamıyor ({self.pcf_api_url})")

    def evaluate_and_enforce(self):
        """Histerezis (Hysteresis) mantığı ile hücre yükünü değerlendirir."""
        load_percent = self.get_current_cell_load()

        if load_percent is None:
            return

        high_thresh = self.policies.get("thresholds", {}).get("high_load_percent", 80.0)
        low_thresh = self.policies.get("thresholds", {}).get("recovery_load_percent", 70.0)
        target_ues = self.policies.get("target_ues", [])

        # Histerezis Karar Mekanizması:
        # Sistem zaten 'throttled' durumundaysa ancak %70 altına inince 'normal'e döner.
        # Sistem 'normal' durumdaysa ancak %80 üzerine çıkınca 'throttled'a geçer.
        if self.current_applied_policy == "throttled":
            if load_percent < low_thresh:
                determined_policy = "normal"
            else:
                determined_policy = "throttled"
        else:
            if load_percent >= high_thresh:
                determined_policy = "throttled"
            else:
                determined_policy = "normal"

        # Durum değişikliği kontrolü (Gereksiz sinyalleşmeyi önler)
        if determined_policy != self.current_applied_policy:
            print(f"\n[KÖPRÜ] >>> DURUM DEĞİŞİKLİĞİ: {self.current_applied_policy.upper()} -> {determined_policy.upper()} (Yük: %{load_percent}) <<<")

            qos_params = self.policies["profiles"][determined_policy]
            for ue in target_ues:
                self.send_pcf_update(ue, determined_policy, qos_params)

            self.current_applied_policy = determined_policy
            self._write_state(determined_policy)

        # Benchmark log kaydı (Her 5 saniyede bir noktayı kaydeder)
        try:
            with open("benchmark_log.csv", "a", encoding="utf-8") as log_file:
                log_file.write(f"{time.time()},{load_percent},{self.current_applied_policy}\n")
        except Exception:
            pass

    def run(self):
        print("[KÖPRÜ] QoS Karar Motoru (Kapalı Çevrim & Histerezis Destekli) Başlatıldı...")
        try:
            while True:
                self.evaluate_and_enforce()
                time.sleep(5)
        except KeyboardInterrupt:
            print("\n[KÖPRÜ] Kapatılıyor...")


if __name__ == "__main__":
    bridge = QoSBridgeEngine()
    bridge.run()
