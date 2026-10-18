# 📡 5G Core Dynamic QoS and Bandwidth Management (O-RAN & Closed-Loop Automation)

**[ EN ]** *Engineered and simulated for the **IEEE 5G/6G Innovation Testbed**, demonstrating state-of-the-art closed-loop network automation, dynamic network slicing, and proactive congestion control.*

![IEEE](https://img.shields.io/badge/Developed_for-IEEE_5G%2F6G_Innovation_Testbed-00629B?style=for-the-badge&logo=ieee&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9+-blue.svg?logo=python&logoColor=white)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.15-orange.svg?logo=tensorflow)
![3GPP](https://img.shields.io/badge/3GPP-Release_16-brightgreen.svg)
![License](https://img.shields.io/badge/License-MIT-gray.svg)

This repository hosts a Proof of Concept (PoC) for a **Closed-Loop Network Automation** system tailored for 5G/6G Standalone (SA) architectures. By integrating physical layer (PHY) channel simulations with 3GPP Service-Based Architecture (SBA) signaling, the system dynamically orchestrates subscriber Quality of Service (QoS) and Maximum Bit Rate (MBR) profiles to prevent cell congestion before it degrades the overall user experience.

## 📑 Table of Contents
1. [Core Motivation & Architecture](#-core-motivation--architecture)
2. [Technical Module Deep-Dive](#-technical-module-deep-dive)
3. [System Workflow (Sequence Diagram)](#-system-workflow)
4. [Testbed Benchmark & Performance Analysis](#-testbed-benchmark--performance-analysis)
5. [Installation & Local Deployment](#-installation--local-deployment)
6. [Future Roadmap](#-future-roadmap)

---

## 💡 Core Motivation & Architecture

In legacy cellular networks, QoS parameters are statically provisioned. However, in high-density environments (e.g., stadium events, disaster zones, or peak urban hours), static allocations inevitably lead to Radio Resource Control (RRC) drops and severe network congestion.

Inspired by the **RAN Intelligent Controller (RIC)** paradigm within **O-RAN**, this system introduces an intelligent decision-making bridge. It continuously monitors the physical PRB (Physical Resource Block) utilization of the gNodeB. Upon detecting a predefined congestion threshold (e.g., 80%), the system autonomously triggers the 5G Core's Policy Control Function (PCF) to throttle low-priority/best-effort traffic, ensuring zero-interruption service for mission-critical and VIP network slices.

---

## ⚙️ Technical Module Deep-Dive

### 1. Physical Layer Simulator (`sim_sionna.py`)
Powered by TensorFlow, this module models a highly deterministic RF environment:
* **Channel Physics:** Implements the `UMa` (Urban Macrocell) channel model with Rayleigh fading and variable pathloss matrices.
* **Capacity Algorithm:** Instead of arbitrary load generation, it calculates spectral efficiency via the **Shannon-Hartley Theorem** ($C = B \log_2(1+SNR)$). Real-time PRB utilization is scientifically derived across a 100 MHz bandwidth configuration.

### 2. QoS Decision Engine (`bridge_engine.py`)
The autonomous brain of the operation, designed to prevent core network overloads:
* **Stateful Execution:** The engine tracks current subscriber states. It only dispatches HTTP POST requests to the Core when a threshold state *changes*, strictly preventing **Signaling Storms**.
* **Real-time CSV Logging:** Automatically dumps timestamped load metrics and policy actions into `benchmark_log.csv` for data science and plotting applications.

### 3. Core Network SBI Simulator (`mock_pcf_server.py`)
* **3GPP TS 29.512 Compliance:** Simulates the `Npcf_SMPolicyControl` RESTful API endpoint.
* Parses incoming JSON payloads (targeting specific SUPIs, applying 5QI rules, and adjusting MBR Uplink/Downlink) to emulate User Plane Function (UPF) rate-limiting.

---

## 🔄 System Workflow

```mermaid
sequenceDiagram
    participant PHY as NVIDIA Sionna (gNodeB Sim)
    participant Bridge as Decision Engine
    participant Core as Mock PCF (5G Core)

    loop Every 5 Seconds
        PHY->>PHY: Calculate Pathloss, Fading & SNR
        PHY->>PHY: Derive PRB Utilization %
        PHY->>Bridge: I/O Write (current_load.json)
        
        Note over Bridge: Load: 86% | Congestion Threshold: 80%
        
        alt Threshold Exceeded & State Changed
            Bridge->>Core: HTTP POST /npcf-smpolicy/v1/policies
            Note over Core: Target: SUPI-003 | Action: Throttle to 2 Mbps
            Core-->>Bridge: 201 Created (Policy Enforced on UPF)
        end
    end


# 1. Clone the repository
git clone [https://github.com/ardaozgur16/5G-Dynamic-QoS-Project.git](https://github.com/ardaozgur16/5G-Dynamic-QoS-Project.git)
cd 5G-Dynamic-QoS-Project

# 2. Install required dependencies
pip install -r requirements.txt

# 3. Launch the topology using 3 separate terminal windows:

# Terminal 1 (Start the Core Network PCF):
cd core_mock && python mock_pcf_server.py

# Terminal 2 (Start the PHY Simulator):
cd sim && python sim_sionna.py

# Terminal 3 (Start the QoS Bridge & Data Logger):
cd bridge && python bridge_engine.py

# 4. Generate the Benchmark Report (After running the system for ~2 mins):
cd bridge && python benchmark_plotter.py
