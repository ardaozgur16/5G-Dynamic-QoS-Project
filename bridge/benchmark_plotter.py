import pandas as pd
import matplotlib.pyplot as plt
import os

def generate_benchmark_report():
    file_path = "benchmark_log.csv"
    if not os.path.exists(file_path):
        print("[ERROR] 'benchmark_log.csv' not found. Run the testbed services first!")
        return

    # Verileri oku
    df = pd.read_csv(file_path, names=["Timestamp", "Load_Percent", "QoS_Policy"])
    
    if df.empty:
        print("[ERROR] 'benchmark_log.csv' is empty.")
        return

    # Süreyi sıfırdan başlat ve dakika cinsine çevir (IEEE paper için daha temiz görünür)
    df["Elapsed_Minutes"] = (df["Timestamp"] - df["Timestamp"].iloc[0]) / 60.0

    # Grafik Ayarları (IEEE standartlarına uygun stil)
    plt.figure(figsize=(10, 5), dpi=300)
    plt.rcParams.update({'font.size': 11, 'font.family': 'sans-serif'})

    # Hücre Yük Çizgisi
    plt.plot(df["Elapsed_Minutes"], df["Load_Percent"], label="Cell PRB Utilization (%)", color='#1f77b4', linewidth=2)

    # Histerezis Karar Eşikleri (%80 Tıkanıklık, %70 Toparlanma)
    plt.axhline(y=80, color='#d62728', linestyle='--', linewidth=1.5, label="Congestion Threshold (80%)")
    plt.axhline(y=70, color='#2ca02c', linestyle=':', linewidth=1.5, label="Recovery Threshold (70%)")

    # Kısıtlanan Noktaları Vurgula (Throttled Samples)
    throttled_data = df[df["QoS_Policy"] == "throttled"]
    if not throttled_data.empty:
        plt.scatter(throttled_data["Elapsed_Minutes"], throttled_data["Load_Percent"], 
                    color='#d62728', s=35, alpha=0.8, zorder=5, label="Throttled State (2 Mbps MBR)")

    plt.title("Closed-Loop Dynamic QoS Control Performance on IEEE 5G/6G Testbed", fontsize=12, pad=12)
    plt.xlabel("Elapsed Time (Minutes)", fontsize=11)
    plt.ylabel("PRB Utilization (%)", fontsize=11)
    plt.ylim(0, 105)
    
    plt.legend(loc="lower right", frameon=True, facecolor='white', framealpha=0.9)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()

    output_img = "benchmark_report_graph.png"
    plt.savefig(output_img, dpi=300)
    print(f"[SUCCESS] IEEE benchmark report graph generated: '{output_img}'")

if __name__ == "__main__":
    generate_benchmark_report()
