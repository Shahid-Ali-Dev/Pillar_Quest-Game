# **Pillar Quest: Leap of Fate**

**Pillar Quest: Leap of Fate** is a 2D platformer game where you guide a daring red cube across floating pillars, overcome enemies, and reach the checkpoint flag to advance to the next level. With carefully tuned double-jump mechanics and challenging gaps, the game offers a fast-paced, precision-platforming experience.

⚠ **Note:** This project was developed entirely with AI assistance. While functional and optimized, there may be flaws, unexpected behaviors, or areas for improvement due to the AI-driven development process.

---

## 🎮 **Gameplay Overview**
- **Objective:** Jump from pillar to pillar, avoid enemies, and reach the checkpoint flag at the end of the stage to proceed to the next level.
- **Mechanics:**
  - **Double Jump:** Press the jump key twice for an extended reach.
  - **Coyote Time:** Small grace period for jumps after stepping off a ledge.
  - **Checkpoints:** Reaching the flag sets a respawn point and triggers the level transition.
  - **Enemies:** Patrolling cubes that can knock you off if touched.
  - **Respawn System:** Respawn at the last activated checkpoint; if none, respawn at the start.
  - **Pause Menu:** Toggle pause (disabled during game over/win).

---

## 🕹 **Controls**
| Key       | Action                  |
|-----------|-------------------------|
| `← / →`   | Move left / right        |
| `Space`   | Jump / Double Jump       |
| `P`       | Pause / Resume           |
| `R`       | Restart Level            |
| `ESC`     | Quit Game                |

---

## ⚙ **Installation & Setup**
1. Make sure you have Python 3.8+ installed.
2. Install **Pygame**:
   ```bash
   pip install pygame
