# Touch Mouse Assistive Interface 🦾🖱️

**Engineered a real-time accessibility ecosystem enabling amputees to control PCs via a hybrid touch-voice interface.**

## 📌 Project Overview
This project addresses the challenge upper-limb amputees face with standard computer mice. We developed a system that transforms a tablet into a specialized touchpad, utilizing **UDP** for low-latency communication and **Google Cloud Speech-to-Text** for multimodal control (Touch + Voice).

### Key Technical Achievements
* **Low-Latency Networking:** Implemented a high-throughput **UDP** communication layer achieving **sub-50ms response times** for seamless cursor navigation.
* **Cross-Platform Architecture:** Developed a **Flutter & Dart** client (`/mobile_app`) with custom gesture recognition algorithms optimized for prosthetic constraints.
* **Cloud AI Integration:** Integrated **Google Cloud Speech-to-Text** to enable complex command execution via voice.

---

## 📂 Repository Structure

The project is divided into two main components:

| Directory | Description |
|---|---|
| **`/mobile_app`** | Contains the **Flutter** source code for the tablet application (Client). Handles touch processing, voice recording, and UDP packet transmission. |
| **`/pc_server`** | Contains the **PC Receiver** software (Server). Listens on a specific UDP port, parses incoming data, and injects mouse/keyboard events into the OS. |

---

## 🚀 Getting Started

### Prerequisites
* **Flutter SDK** (for the mobile app)
* **Python 3.x / C# .NET** (depending on the server version used)
* A local Wi-Fi network (Tablet and PC must be on the same network).

### Installation
1.  **Clone the repo:**
    ```bash
    git clone [https://github.com/neryaco77-pixel/Touch-Mouse-Prosthetic.git](https://github.com/neryaco77-pixel/Touch-Mouse-Prosthetic.git)
    ```
2.  **Run the PC Server:**
    Navigate to `/pc_server` and run the script to start listening for packets.
3.  **Run the Mobile App:**
    Navigate to `/mobile_app` and run:
    ```bash
    flutter run
    ```

---

## 👨‍💻 Authors
* **Nerya Cohen**
* **Chen Giller**
* **Supervisor:** Prof. Shlomi Arnon (BGU)