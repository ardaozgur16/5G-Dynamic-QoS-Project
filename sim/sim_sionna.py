# Dosya: sim_sionna.py
# Çalıştırmadan önce gereksinimleri yükleyin: pip install sionna tensorflow numpy

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Gereksiz TensorFlow uyarılarını gizler
import tensorflow as tf
import time
import json

try:
    import sionna
except ImportError:
    print("[HATA] Sionna kütüphanesi bulunamadı. Lütfen yükleyin: pip install sionna")
    exit(1)


class SionnaCellLoadSimulator:
    def __init__(self, total_prb=273, subcarrier_spacing=30e3, state_file_path="active_policy.json"):
        """
        5G NR Fiziksel Katman Parametreleri (100 MHz, 30 kHz SCS, 273 PRB).
        """
        self.total_prb = tf.constant(total_prb, dtype=tf.float32)
        self.prb_bw = tf.constant(12 * subcarrier_spacing, dtype=tf.float32)
        self.state_file_path = state_file_path
        self.step_counter = 0

    def simulate_channel_snr(self, num_ues):
        """Kullanıcıların SNR ve fading değerlerini hesaplar."""
        mean_snr_db = tf.random.uniform(shape=[num_ues], minval=2.0, maxval=25.0, dtype=tf.float32)
        fading_db = tf.random.normal(shape=[num_ues], mean=0.0, stddev=3.0, dtype=tf.float32)
        final_snr_db = mean_snr_db + fading_db
        snr_linear = tf.math.pow(10.0, final_snr_db / 10.0)
        return snr_linear

    def get_applied_policy(self):
        """Bridge engine tarafından yazılan güncel politikayı okur."""
        if os.path.exists(self.state_file_path):
            try:
                with open(self.state_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("active_policy", "normal")
            except Exception:
                return "normal"
        return "normal"

    def compute_cell_load(self):
        """Tensör operasyonları ile ağ yükünü hesaplar ve kapalı çevrim kısıtlamasını uygular."""
        self.step_counter += 1

        # Dinamik Trafik Deseni: Her 24 adımda bir (yaklaşık 2 dk) trafik pik yapsın
        cycle_step = self.step_counter % 24
        if 8 <= cycle_step <= 16:
            # Pik Dönemi (Tıkanıklık tetikleyecek kullanıcı sayısı)
            current_ues = tf.random.uniform(shape=[], minval=28, maxval=36, dtype=tf.int32)
        else:
            # Normal Dönem (Sistemi rahatlatacak kullanıcı sayısı)
            current_ues = tf.random.uniform(shape=[], minval=14, maxval=22, dtype=tf.int32)

        # SNR ve Spektral Verimlilik
        snr_linear = self.simulate_channel_snr(current_ues)
        spectral_efficiency = tf.math.log(1.0 + snr_linear) / tf.math.log(2.0)
        practical_efficiency = spectral_efficiency * 0.7
        prb_capacity_bps = practical_efficiency * self.prb_bw

        # Normal şartlarda kullanıcı başına talep (1.5 Mbps - 6.0 Mbps)
        demands_bps = tf.random.uniform(shape=[current_ues], minval=1.5e6, maxval=6.0e6, dtype=tf.float32)

        # --- KAPALI ÇEVRİM GERİ BESLEME MEKANİZMASI ---
        active_policy = self.get_applied_policy()
        if active_policy == "throttled":
            # Düşük öncelikli hedef abonelerin (yaklaşık %35) hızını 2 Mbps'ye sabitle
            throttled_count = tf.cast(tf.cast(current_ues, tf.float32) * 0.35, tf.int32)
            mask = tf.concat([
                tf.ones([throttled_count], dtype=tf.float32),
                tf.zeros([current_ues - throttled_count], dtype=tf.float32)
            ], axis=0)

            # Hedef kullanıcıların talebini 2 Mbps tavanı ile kırp
            throttled_demands = tf.minimum(demands_bps, 2.0e6)
            demands_bps = tf.where(mask > 0.0, throttled_demands, demands_bps)

        # PRB İhtiyacı ve Yük Hesaplama
        required_prbs = demands_bps / prb_capacity_bps
        total_required_prbs = tf.math.reduce_sum(required_prbs)

        load_ratio = total_required_prbs / self.total_prb
        load_percentage = tf.clip_by_value(load_ratio * 100.0, 0.0, 100.0)

        return {
            "timestamp": time.time(),
            "active_ues": int(current_ues.numpy()),
            "cell_load_percent": round(float(load_percentage.numpy()), 2),
            "enforced_policy": active_policy
        }


if __name__ == "__main__":
    print("[SIONNA] Kapalı Çevrim Destekli 5G NR Yük Simülasyonu Başlatılıyor...")
    print(f"[SIONNA] TensorFlow Sürümü: {tf.__version__}")

    sim = SionnaCellLoadSimulator(state_file_path="active_policy.json")
    output_file = "current_load.json"

    try:
        while True:
            metrics = sim.compute_cell_load()

            print(f"[Ağ Durumu] Aktif UE: {metrics['active_ues']:02d} | "
                  f"Hücre Doluluğu: %{metrics['cell_load_percent']:05.2f} | "
                  f"Aktif Politika: {metrics['enforced_policy'].upper()}")

            # Atomic JSON yazma (Yazma sırasında Bridge Engine'in yarım okumasını önler)
            temp_file = output_file + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(metrics, f)
            os.replace(temp_file, output_file)

            time.sleep(5)

    except KeyboardInterrupt:
        print("\n[SIONNA] Simülasyon durduruldu.")
        if os.path.exists(output_file):
            os.remove(output_file)
