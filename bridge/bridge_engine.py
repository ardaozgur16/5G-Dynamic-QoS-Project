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
    def __init__(self, load_file_path="../sim/current_load.json", policy_file_path="policies.yaml"):
        self.load_file_path = load_file_path
        self.policy_file_path = policy_file_path

        # 5G Core PCF (Policy Control Function) Endpoint'i
        # Not: Gerçek bir Core kullanıldığında burası onun IP'si olacak.
        # bridge_engine.py içindeki ilgili satır şu şekilde OLMALIDIR:
        self.pcf_api_url = "http://127.0.0.1:8000/npcf-smpolicy/v1/policies"

        # O anki QoS durumunu takip etmek için (Gereksiz API çağrılarını önler)
        self.current_applied_policy = None

        # Politikaları yükle
        self.policies = self.load_policies()

    def load_policies(self):
        """policies.yaml dosyasından eşik değerlerini ve QoS kurallarını okur."""
        try:
            with open(self.policy_file_path, "r", encoding="utf-8") as file:
                policies = yaml.safe_load(file)
                print("[KÖPRÜ] Politikalar başarıyla yüklendi.")
                return policies
        except FileNotFoundError:
            print(f"[HATA] Politika dosyası bulunamadı: {self.policy_file_path}")
            # Dosya yoksa varsayılan koruma politikası oluştur
            return {
                "thresholds": {"high_load_percent": 80},
                "profiles": {
                    "normal": {"5qi": 9, "mbr_dl": "50 Mbps", "mbr_ul": "20 Mbps"},
                    "throttled": {"5qi": 9, "mbr_dl": "2 Mbps", "mbr_ul": "1 Mbps"}
                },
                "target_ues": ["imsi-208930000000003"]
            }

    def get_current_cell_load(self):
        """Sionna tarafından üretilen current_load.json dosyasını okur."""
        if not os.path.exists(self.load_file_path):
            return None

        try:
            with open(self.load_file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
                return data.get("cell_load_percent", 0.0)
        except (json.JSONDecodeError, PermissionError):
            # Dosya o an simülasyon tarafından yazılıyorsa okuma hatası olabilir, atla
            return None

    def send_pcf_update(self, target_ue, policy_name, qos_params):
        """PCF'e 3GPP Npcf_SMPolicyControl standardında HTTP POST isteği atar."""
        payload = {
            "supi": target_ue,  # Abone Kimliği (SUPI/IMSI)
            "trigger": "CELL_CONGESTION",
            "policy_decision": {
                "qos_profile": {
                    "5qi": qos_params["5qi"],
                    "maxbrDl": qos_params["mbr_dl"],
                    "maxbrUl": qos_params["mbr_ul"]
                }
            }
        }

        try:
            # Timeout süresi kritik, ağ tıkanıklığında köprü scripti kilitlenmemeli
            response = requests.post(self.pcf_api_url, json=payload, timeout=2.0)
            if response.status_code in [200, 201]:
                print(f"  [>] SBI İSTEĞİ BAŞARILI: {target_ue} için hız {qos_params['mbr_dl']} olarak ayarlandı.")
            else:
                print(f"  [X] SBI İSTEĞİ BAŞARISIZ: Sunucu yanıt kodu {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"  [X] PCF BAĞLANTI HATASI: Sunucuya ulaşılamıyor. ({self.pcf_api_url})")

    def evaluate_and_enforce(self):
        """Hücre yükünü değerlendirir ve gerekiyorsa QoS politikasını değiştirir."""
        load_percent = self.get_current_cell_load()

        if load_percent is None:
            return  # Veri okunamadıysa bu döngüyü atla

        print(f"[KÖPRÜ] Okunan Hücre Doluluğu: %{load_percent}")

        threshold = self.policies["thresholds"]["high_load_percent"]
        target_ues = self.policies["target_ues"]

        # Karar Mekanizması
        if load_percent >= threshold:
            determined_policy = "throttled"
        else:
            determined_policy = "normal"

        # Eğer durum değiştiyse API çağrısı yap (Gereksiz trafiği önle)
        if determined_policy != self.current_applied_policy:
            print(f"[KÖPRÜ] DURUM DEĞİŞİKLİĞİ TESPİT EDİLDİ -> Yeni Politika: {determined_policy.upper()}")

            qos_params = self.policies["profiles"][determined_policy]

            for ue in target_ues:
                self.send_pcf_update(ue, determined_policy, qos_params)

            # Durumu güncelle
            self.current_applied_policy = determined_policy

        # --- EKLENEN KISIM: Benchmark Analizi İçin Veri Kaydetme ---
        # Bu kısım if bloğunun dışında olmalıdır ki her okumada (durum değişmese bile) grafiğe nokta koysun.
        try:
            with open("benchmark_log.csv", "a", encoding="utf-8") as log_file:
                log_file.write(f"{time.time()},{load_percent},{determined_policy}\n")
        except Exception as e:
            pass  # Eğer dosya yazılırken anlık bir kilitlenme olursa sistemi çökertmemesi için

    def run(self):
        """Sürekli çalışan ana dinleme döngüsü"""
        print("[KÖPRÜ] QoS Karar Motoru Başlatıldı. Fiziksel katman dinleniyor...")
        try:
            while True:
                self.evaluate_and_enforce()
                time.sleep(5)  # 5 saniyede bir kontrol et
        except KeyboardInterrupt:
            print("\n[KÖPRÜ] Kapatılıyor...")


if __name__ == "__main__":
    # Test ortamında dosyaların yollarını doğru verdiğinizden emin olun
    # Eğer aynı klasörde çalıştırıyorsanız: load_file_path="current_load.json" yapabilirsiniz.
    bridge = QoSBridgeEngine(load_file_path="../sim/current_load.json", policy_file_path="policies.yaml")
    bridge.run()