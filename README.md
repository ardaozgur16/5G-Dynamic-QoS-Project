# 📡 5G Core Dynamic QoS and Bandwidth Management (O-RAN & Closed-Loop Automation)

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg?logo=python&logoColor=white)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.15-orange.svg?logo=tensorflow)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?logo=docker&logoColor=white)
![5G](https://img.shields.io/badge/3GPP-Release_16-brightgreen.svg)
![License](https://img.shields.io/badge/License-MIT-gray.svg)

This project is a Proof of Concept (PoC) that brings the vision of **Network Slicing** and **Closed-Loop Automation** in 5G and 6G networks to life. The system simulates the real-time utilization of physical Radio Resource Blocks (PRBs) at the base station (gNodeB). When it detects a risk of network congestion, it intervenes via standard 3GPP signaling to the 5G Core, dynamically restricting the bandwidth of low-priority subscribers to stabilize the network.

## 📑 Table of Contents
1. [Core Motivation](#-core-motivation)
2. [System Architecture & Workflow](#-system-architecture--workflow)
3. [Technical Depth of Modules](#-technical-depth-of-modules)
4. [Installation and Execution](#-installation-and-execution)
5. [Configuration Guide](#-configuration-guide)
6. [Example Output (Logs)](#-example-output)
7. [Future Roadmap](#-future-roadmap)

---

## 💡 Core Motivation
In traditional cellular networks, Quality of Service (QoS) policies are largely "static" (fixed based on subscriber data). However, when cell capacity reaches its limits—during a stadium concert, a disaster scenario, or peak traffic hours—static rules often lead to network collapse. 

Inspired by the **RIC (RAN Intelligent Controller)** concept in modern **O-RAN (Open RAN)** architectures, this project makes the network "smart." A bridge engine continuously monitors physical radio conditions and detects congestion at an 80% threshold—before hardware limits are breached. It then downgrades the QoS profile of non-VIP/best-effort devices, allowing the network to breathe.

---

## 🏗️ System Architecture & Workflow

Sequence diagram illustrating the asynchronous interaction of system components:

```mermaid
sequenceDiagram
    participant PHY as NVIDIA Sionna (gNodeB Simulator)
    participant Bridge as Bridge Engine (Decision Engine)
    participant Core as Mock PCF (5G Core)

    loop Every 5 Seconds
        PHY->>PHY: Pathloss, Fading & SNR Calculation
        PHY->>PHY: PRB Utilization via Shannon Formula
        PHY->>Bridge: File Write (current_load.json)
        
        Note over Bridge: Bridge reads JSON. Cell load: 85%
        Note over Bridge: policies.yaml checked (Threshold: 80%)
        
        alt Threshold Exceeded & State Changed
            Bridge->>Core: HTTP POST (Npcf_SMPolicyControl)
            Note over Core: QoS Update targetting SUPI Received
            Note over Core: Rate Limiting Command Sent to UPF (2 Mbps)
            Core-->>Bridge: 201 Created (Success)
        end
    end
