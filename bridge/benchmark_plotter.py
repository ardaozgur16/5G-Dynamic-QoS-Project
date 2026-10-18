import pandas as pd
import matplotlib.pyplot as plt
import os

def generate_benchmark_report():
    file_path = "benchmark_log.csv"
    if not os.path.exists(file_path):
        print("Önce sistemi çalıştırıp benchmark_log.csv dosyasının dolmasını bekleyin!")
        return

    # Verileri oku
    df = pd.read_csv(file_path, names=["Timestamp", "Load_Percent", "QoS_Policy"])
    df["Timestamp"] = df["Timestamp"] - df["Timestamp"].iloc[0] # Süreyi sıfırdan başlat
    
    # Grafik Ayarları
    plt.figure(figsize=(12, 6))
    plt.plot(df["Timestamp"], df["Load_Percent"], label="Anlık Hücre Doluluğu (%)", color='blue', linewidth=2)
    plt.axhline(y=80, color='red', linestyle='--', label="Tıkanıklık Eşiği (%80)")

    # Throttled (Kısıtlanmış) olan bölgeleri grafikte kırmızı renkle vurgula
    throttled_data = df[df["QoS_Policy"] == "throttled"]
    plt.scatter(throttled_data["Timestamp"], throttled_data["Load_Percent"], color='red', s=50, zorder=5, label="QoS Kısıtlaması Aktif (2 Mbps)")

    plt.title("5G Core Dinamik QoS Performans ve Analiz (Benchmark) Raporu", fontsize=14)
    plt.xlabel("Zaman (Saniye)", fontsize=12)
    plt.ylabel("gNodeB PRB Doluluk Oranı (%)", fontsize=12)
    plt.legend(loc="lower right")
    plt.grid(True, linestyle=':', alpha=0.7)
    
    # Raporu kaydet
    plt.savefig("benchmark_report_graph.png", dpi=300)
    print("✅ Benchmark Raporu oluşturuldu: 'benchmark_report_graph.png' dosyasını inceleyin.")
    plt.show()

if __name__ == "__main__":
    generate_benchmark_report()