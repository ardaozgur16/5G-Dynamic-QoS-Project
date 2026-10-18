# Dosya: core_mock/mock_pcf_server.py

from flask import Flask, request, jsonify
import logging

# Flask'ın kendi gereksiz HTTP loglarını kapatıp ekranı temiz tutalım
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)


# 3GPP SBI Standardına Uygun Npcf_SMPolicyControl Endpoint'i
@app.route('/npcf-smpolicy/v1/policies', methods=['POST'])
def sm_policy_control():
    try:
        # Bridge Engine'den gelen JSON verisini al
        payload = request.get_json()

        target_ue = payload.get("supi", "Bilinmeyen UE")
        trigger = payload.get("trigger", "Bilinmeyen Tetikleyici")
        qos_profile = payload.get("policy_decision", {}).get("qos_profile", {})

        qi_5 = qos_profile.get("5qi", "Bilinmiyor")
        mbr_dl = qos_profile.get("maxbrDl", "Bilinmiyor")
        mbr_ul = qos_profile.get("maxbrUl", "Bilinmiyor")

        # Terminalde kolay okunması için dekoratif log çıktısı
        print("\n" + "=" * 50)
        print("📡 [MOCK PCF] 5G CORE QOS GÜNCELLEMESİ ALINDI")
        print("=" * 50)
        print(f"👤 Hedef Abone (SUPI) : {target_ue}")
        print(f"⚠️ Tetikleyici (Event) : {trigger}")
        print(f"⚙️ Yeni QoS Profili   :")
        print(f"   - Trafik Sınıfı (5QI) : {qi_5}")
        print(f"   - Max İndirme Hızı  : {mbr_dl}")
        print(f"   - Max Yükleme Hızı  : {mbr_ul}")
        print("=" * 50)
        print("✅ [UPF'e İletildi] Abone hızı veri düzleminde başarıyla uygulandı.\n")

        # Bridge scriptine "İşlem Başarılı" (201 Created) yanıtı dön
        response_data = {
            "status": "success",
            "message": "Policy provisioned successfully in UPF"
        }
        return jsonify(response_data), 201

    except Exception as e:
        print(f"\n❌ [MOCK PCF HATA] İstek işlenirken hata oluştu: {str(e)}")
        return jsonify({"status": "error", "message": "Bad Request"}), 400


if __name__ == '__main__':
    print("🌐 [MOCK PCF] 3GPP SBI Simülatörü Başlatıldı. 8000 Portu Dinleniyor...")
    # Sunucuyu 0.0.0.0 üzerinden başlatıyoruz ki Docker ağı üzerinden erişilebilsin
    app.run(host='0.0.0.0', port=8000)