# AutoCam - Advanced AI Broadcast Director for Assetto Corsa

AutoCam is a comprehensive camera and driver switching automation app for **Assetto Corsa**. It acts as an AI broadcast director, dynamically analyzing telemetry, gaps, and incidents on the track to provide a professional television-like broadcast experience for live streams, video captures, or replay watching.

Originally created by **Esotic** and based on **Minolin's ActionCam** concept, this version of AutoCam is enhanced with a modernized reji (director) algorithm, dynamic chase camera logic, local leaderboard fallback, and a redesigned in-game settings user interface.

---

## 🌟 Key Features & Enhancements

### 1. Professional Director (Reji) Mode
* **Position-Weighted Battle Scoring:** Prioritizes front-runner battles and leader groups. A tight gap at the front is prioritized over minor gaps at the back of the grid, mimicking real-life F1 broadcast logic.
* **Focus Retention:** Adds a focus preservation factor to the current car being watched, preventing rapid, disorienting camera jumps between cars.

### 2. Dynamic Chase Camera (New)
* **Chase Phase (0.3s - 0.8s Gap):** Switches to the chasing driver's cockpit/onboard camera to experience the thrill of the chase from the driver's perspective.
* **Attack/Side-by-Side Phase (< 0.3s Gap):** Instantly cuts to external Track/TV cameras when cars pull side-by-side or attempt an overtake, ensuring the action is fully visible.

### 3. Incident & Spin Detection
* **Incident Detection:** Telemetry is monitored in real-time. If a car drops below 25 km/h in a high-speed zone (above 60 km/h normal pace), the director immediately tags it as an incident.
* **Emergency Cut:** The camera immediately shifts to the crashed car on a TV camera and locks onto it for a configurable duration (default: 8 seconds) so you never miss a spin or crash.

### 4. Local Leaderboard Support
* **Independent Running Order:** Automatically falls back to fetching real-time positions from Assetto Corsa's internal API (`ac.getCarRealTimeLeaderboardPosition`) if an external broadcast stream app (like AppCom or AnnouncerBot) is not connected. Works fully offline and in local replays!

### 5. Redesigned In-Game Settings UI
* Modernized, clean, and user-friendly dark-themed settings card.
* Interactive spinners (value adjusters) and checkboxes for all major settings:
  * **Battle Gap (sec):** Set the time window to classify a battle.
  * **Front Priority (Decay):** Adjust how heavily front-runner battles are favored (lower value = higher front focus).
  * **Switch Delay (sec):** Set default viewing duration before switching.
  * **Incident Duration (sec):** Set lock-on duration for crashes.
  * **Dynamic Chase Cam:** Toggle between the dynamic onboard-to-TV camera logic.
  * **Force TV Cam on Battle:** Override cockpit cameras entirely during battles.
  * **Save Configuration:** Save all modified settings directly to `AutoCam.ini` from within the game.

### 6. OBS Studio Integration
* Automatically connects to OBS Websocket to control streaming, trigger profile changes, and react to race phases.

---

## ⚙️ Installation

1. Clone or download this repository.
2. Copy the `AutoCam` folder into your Assetto Corsa directory:
   `...\Assetto Corsa\apps\python\AutoCam`
3. Open **Content Manager** or the Assetto Corsa launcher.
4. Go to **Settings > Assetto Corsa > Apps** and check the box next to **AutoCam** to enable it.
5. In-game, open the right sidebar menu and activate the **AutoCam** app to display the settings window.

---

## 🛠️ Configuration Settings (`AutoCam.ini`)

You can edit these parameters either via the in-game UI (and press **Save Configuration**) or manually inside the `AutoCam.ini` file:

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `AutoCamActive` | `1` | Enable/disable AutoCam upon loading. |
| `battleGap` | `0.5` | Max gap in seconds between cars to trigger battle tracking. |
| `positionDecay` | `0.92` | Front-priority factor. Decreasing this (e.g. to `0.88`) increases focus on P1-P5. |
| `incidentDetection` | `1` | Toggle incident/spin detection on/off. |
| `incidentMaxSpeed` | `25.0` | Target speed (km/h) below which a car is considered crashed. |
| `forceTrackCamOnCloseBattles` | `1` | Forces Track/TV camera modes during battles. |
| `closeBattleThreshold` | `0.35` | Gap threshold below which TV camera is forced in battles. |

---

## 🏷️ Tags
`assetto-corsa` `assetto-corsa-app` `python` `sim-racing` `broadcast-director` `auto-cam` `camera-control` `racing-director` `hud` `obs-websocket`

---

## 📜 Credits & References
* **Original Author:** Dave / **Esotic** - [Auto Cam V1.6 on Overtake.gg (formerly RaceDepartment)](https://www.overtake.gg/downloads/auto-cam.28562/)
* **Original Concept:** **Minolin** - [ActionCam Concept on Assetto Corsa Forums](https://www.assettocorsa.net/forum/index.php?threads/concept-actioncam.31665/)
* Designed to work seamlessly in combination with broadcasting tools like:
  * **BCast:** [BCast App for Broadcasting](https://www.assettocorsa.net/forum/index.php?threads/bcast-app-for-broadcasting-v1-12.32536/)
  * **ACTV:** [ACTV Leaderboard App](https://www.racedepartment.com/downloads/actv.7889/)
