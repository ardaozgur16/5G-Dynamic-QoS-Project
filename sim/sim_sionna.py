# Dosya: sim_sionna.py
# Çalıştırmadan önce gereksinimleri yükleyin: pip install sionna tensorflow numpy

import os

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Gereksiz TensorFlow uyarılarını gizler
import tensorflow as tf
import time
import json
import random

try:
    import sionna
except ImportError:
    print("[HATA] Sionna kütüphanesi bulunamadı. Lütfen yükleyin: pip install sionna")
    exit(1)


class SionnaCellLoadSimulator:
    def __init__(self, total_prb=273, subcarrier_spacing=30e3):
        """
        5G NR Fiziksel Katman Parametreleri Başlatılır.
        100 MHz bant genişliği ve 30 kHz SCS (Subcarrier Spacing) için:
        Toplam PRB sayısı yaklaşık 273'tür.
        1 PRB = 12 Alt Taşıyıcı (Subcarrier)
        """
        self.total_prb = tf.constant(total_prb, dtype=tf.float32)
        # 1 PRB'nin frekans alanındaki genişliği (Hz)
        self.prb_bw = tf.constant(12 * subcarrier_spacing, dtype=tf.float32)

        # Simülasyon sınırları
        self.min_ues = 40
        self.max_ues = 80

    def simulate_channel_snr(self, num_ues):
        """
        Kullanıcıların baz istasyonuna uzaklıklarına (Pathloss) ve
        anlık kanal solmasına (Fading) göre rastgele SNR üretir.
        """
        # Kullanıcıların ortalama SNR değerleri (0 dB ile 25 dB arası uzaklığa bağlı)
        mean_snr_db = tf.random.uniform(shape=[num_ues], minval=0.0, maxval=25.0, dtype=tf.float32)

        # Hızlı Fading etkisi (Sionna benzeri kanal dalgalanması)
        fading_db = tf.random.normal(shape=[num_ues], mean=0.0, stddev=4.0, dtype=tf.float32)

        # Toplam SNR (dB) ve Lineer Dönüşüm
        final_snr_db = mean_snr_db + fading_db
        snr_linear = tf.math.pow(10.0, final_snr_db / 10.0)

        return snr_linear

    def compute_cell_load(self):
        """
        Tensör operasyonları ile ağ kapasitesi ve yükünü hesaplar.
        """
        # 1. O anki aktif abone sayısını belirle
        current_ues = tf.random.uniform(shape=[], minval=self.min_ues, maxval=self.max_ues, dtype=tf.int32)

        # 2. Kanal Kalitesini (SNR) simüle et
        snr_linear = self.simulate_channel_snr(current_ues)

        # 3. Spektral Verimlilik Hesaplaması (Shannon Kapasitesi: bps/Hz)
        # C = log2(1 + SNR)
        spectral_efficiency = tf.math.log(1.0 + snr_linear) / tf.math.log(2.0)

        # Pratik 5G MIMO/Ağ kayıpları için verimliliği ölçeklendir (Örn: %70 başarı)
        practical_efficiency = spectral_efficiency * 0.7

        # 4. PRB Başına Kapasite (bps) = Spektral Verimlilik * PRB Bant Genişliği
        prb_capacity_bps = practical_efficiency * self.prb_bw

        # 5. Abonelerin anlık trafik talepleri (Örn: 2 Mbps ile 12 Mbps arası)
        demands_bps = tf.random.uniform(shape=[current_ues], minval=2e6, maxval=12e6, dtype=tf.float32)

        # 6. Talep edilen PRB sayısını hesapla
        required_prbs = demands_bps / prb_capacity_bps
        total_required_prbs = tf.math.reduce_sum(required_prbs)

        # 7. Hücre Doluluk Oranını Hesapla (%)
        load_ratio = total_required_prbs / self.total_prb
        load_percentage = tf.clip_by_value(load_ratio * 100.0, 0.0, 100.0)  # %100'ü geçemez

        return {
            "timestamp": time.time(),
            "active_ues": int(current_ues.numpy()),
            "cell_load_percent": round(float(load_percentage.numpy()), 2)
        }


if __name__ == "__main__":
    print(f"[SIONNA] 5G NR Fiziksel Katman Yük Simülasyonu Başlatılıyor...")
    print(f"[SIONNA] TensorFlow Sürümü: {tf.__version__}")

    sim = SionnaCellLoadSimulator()
    output_file = "current_load.json"

    try:
        while True:
            # Yükü hesapla
            metrics = sim.compute_cell_load()

            # Konsola yazdır
            print(f"[Ağ Durumu] Aktif UE: {metrics['active_ues']:02d} | "
                  f"Hücre Doluluğu: %{metrics['cell_load_percent']:05.2f}")

            # Bridge (Köprü) scriptinin okuyabilmesi için JSON'a kaydet
            with open(output_file, "w") as f:
                json.dump(metrics, f)

            # Mimaride belirttiğiniz gibi 5 saniyede bir tetiklenir
            time.sleep(5)

    except KeyboardInterrupt:
        print("\n[SIONNA] Simülasyon kullanıcı tarafından durduruldu.")
        if os.path.exists(output_file):
            os.remove(output_file)