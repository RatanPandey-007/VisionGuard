# VisionGuard Edge

**Affordable Offline AI Quality Inspection for Indian MSMEs**
*Developed for MSME Idea Hackathon 6.0 | Presentation Date: 25 August 2026*

---

## 1. Project Overview & Context

Micro, Small, and Medium Enterprises (MSMEs) in India contribute over 30% of the country's GDP but face significant hurdles in adopting Industry 4.0 automation. Typical industrial automated optical inspection (AOI) systems cost upwards of ₹5–15 Lakhs, necessitating specialized GPUs, continuous cloud connectivity, and complete replacement of manual inspection lines.

**VisionGuard Edge** is a software-first, offline-capable **retrofit quality inspection prototype** that turns off-the-shelf cameras (webcams, USB cameras, or low-cost ESP32-CAMs) into AI quality inspectors for under ₹5,000. It processes all frame inferences locally on ordinary factory laptop CPUs, ensuring sensitive factory yield data remains entirely offline and securely on-site.

---

## 2. Key Differentiators

1. **Affordable:** Costs < 1% of traditional conveyor AOI systems through camera-retrofit architecture.
2. **Offline-First:** Runs entirely locally on CPUs without cloud connection.
3. **Explainable AI:** Displays visual defect overlays showing coordinates, angles, and confidence metrics instead of binary output.
4. **Retrofit Ready:** Slides onto existing QC workbench tables or jigs.
5. **Real-time Analytics:** Aggregates logs into an offline SQLite database to display quality yields, failure rates, and defect distribution types.

---

## 3. Project Architecture

```text
VisionGuard/
│
├── app/
│   ├── __init__.py
│   ├── camera.py        # Camera abstraction layer (Webcam, USB, static Demo mode)
│   ├── detector.py      # Dual engine: YOLOv8 COCO + OpenCV PCB component analyzer
│   ├── database.py      # SQLite logging layer (creates database, logs events, handles metrics)
│   ├── report.py        # PDF compilation compiler using ReportLab
│   └── main.py          # Dashboard UI & Inspection Console (Streamlit)
│
├── data/
│   ├── demo_samples/    # Programmatic sample images for offline Pitch mode
│   ├── inspections/     # Archived inspection BGR crop visual files
│   └── database.sqlite  # Inspection history records DB
│
├── models/              # YOLOv8 weights storage (yolov8n.pt cache)
├── reports/             # Compiled inspection PDF reports
├── requirements.txt     # Python dependency libraries
├── run.py               # Launcher script
└── README.md            # Documentation manuel
```

---

## 4. Getting Started

### Prerequisites
- Python 3.12 (or higher) installed.
- System webcam (e.g. laptop integrated webcam) or USB camera.

### Fast Startup
Run the launcher script in the root directory:
```bash
python run.py
```
This script will automatically verify dependencies, create the database, compile the demo sample images, and start the Streamlit server. Open the local address in your browser:
* Local URL: `http://localhost:8501`

---

## 5. Live Pitch Demonstration Script

Use this 1-minute demo block to show judges:
1. **Landing Overview:** Open the landing tab to describe the MSME problem statement.
2. **Verify Offline AI Engine:** Select the **Quality Scanner** tab. Wave a household object (e.g. cell phone, mug) in front of the camera, choose "General YOLO Detection" to demonstrate local real-time object classification running on the laptop CPU.
3. **Run PCB Quality Check:** Switch back to "PCB Component Check".
   - Turn on **Demo Mode** to simulate the conveyor line. The system will cycle through simulated PCB boards.
   - **Case 1 (PASS):** Showcases `01_perfect_pcb_a` returning `🟢 PASS` with ~98.7% confidence (components straight, 3/3 found).
   - **Case 2 (FAIL - Missing):** Showcases `03_defect_missing_chip` returning `🔴 FAIL` due to only 2 component contours detected.
   - **Case 3 (FAIL - Angular tilt):** Showcases `04_defect_misaligned_chip` detecting a `🔴 FAIL` (Component Misaligned) because a chip is rotated at an angle of 25.0 degrees.
4. **Download Report:** Click the `Download Report PDF` button to show the compiled document.
5. **View Dashboard:** Click `Analytics Dashboard` to review dynamic quality yield metrics and failure rate bar graphs.

---

## 6. Incubation Funding & Development Roadmap

If selected for the MSME Idea Hackathon 6.0, the incubation funding will be allocated as follows:

| Development Phase | Projected Timeline | Target Milestones | Estimated budget Alloc |
| --- | --- | --- | --- |
| **Phase 1: Dataset & YOLO Training** | Month 1–2 | Collect 5,000 high-res MSME PCB defect images. Fine-tune custom YOLOv8-nano model. | ₹40,000 |
| **Phase 2: Hardware Reto-Jig** | Month 3 | Build table mount with adjustable lighting diffuser dome and conveyor guide rails. | ₹25,000 |
| **Phase 3: Edge Unit PCB Design** | Month 4–5 | Integrate Raspberry Pi 4 / Nvidia Jetson Nano on custom motherboard interface. | ₹60,000 |
| **Phase 4: Pilot Test & Retrain** | Month 6 | Deploy beta jigs at 2 local MSME PCB assembly assembly units in India. | ₹25,000 |
| **Total Allocation** | **6 Months** | **Production-Ready retrofitted commercial system** | **₹1.50 Lakhs** |

---

## 7. Judge Q&A Cheat Sheet

#### Q1: Why use custom OpenCV logic instead of ONLY training YOLO for PCB defects right now?
* **Answer:** Building a deep learning model for PCB defects requires thousands of highly specific training images, which are unavailable at the prototype stage. Standard OpenCV color masking and contour detection match how industrial vision systems worked for decades: they run in under 5ms on basic CPU hardware, measure exact rotations in degrees, count parts, and don't suffer from neural network "hallucinations." Once production data is gathered, we will train a custom lightweight YOLO model to run alongside it.

#### Q2: What happens if ambient factory lighting changes?
* **Answer:** Computer vision algorithms are sensitive to light. This is why VisionGuard is designed as a *physical retrofit jig* rather than just software. The future commercial hardware includes an affordable acrylic light-diffuser dome with a constant-voltage LED ring (budget: ₹1,500). This isolates the capture area from ambient workshop light drift.

#### Q3: Why run on Edge CPU? Why not stream to a Cloud GPU?
* **Answer:** Industrial MSMEs often operate in workshops with inconsistent internet connection. Streaming high-resolution, uncompressed video frames (e.g. 10MB/sec) to the cloud stalls production lines when bandwidth drops, raises bandwidth cost, and introduces latency (100–300ms vs. 15ms local). Edge processing ensures data privacy (preventing leaks of intellectual manufacture designs) and zero external subscription overhead.

#### Q4: How is this "retrofit-friendly"?
* **Answer:** We do not replace the conveyor or assembly bench. The operator mounts our camera arm above their existing jig. By sending the PASS/FAIL signal to a basic electronic relay (via GPIO on our edge controller), we can stop the conveyor belt or trigger an acoustic alarm without modifying their principal line machinery.
