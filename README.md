# Odd-Even Sort Algorithm Visualizer

An interactive, real-time visualization of the **Odd-Even Transposition Sort** algorithm built with Python and Pygame CE. Watch the algorithm sort arrays step-by-step with full control over speed, array size, and execution mode — with live performance metrics tracked to CSV.

---

## Features

- **Dual execution modes** — Sequential and Parallel odd-even sort, switchable at runtime
- **Real-time visualization** — Animated bars with color-coded comparison, swap, and sorted states using a cyberpunk space-nebula palette
- **PCM audio synthesis** — Synthesized sine-wave sound effects for comparisons, swaps, phase transitions, and sort completion
- **Live performance dashboard** — Tracks comparisons, swaps, and cycle count in real time
- **CSV metrics logging** — Automatically saves session data (array size, mode, comparisons, swaps, cycles) to `odd_even_sort_metrics.csv`
- **Particle effects** — Background star field and spark particles on swap events
- **Interactive scrubber** — Step backward and forward through sort history
- **Responsive controls** — Play/pause, speed control, array reshuffle, sound toggle, and mode switching via on-screen buttons

---

## Algorithm Overview

**Odd-Even Transposition Sort** is a parallel comparison-based sorting algorithm inspired by Bubble Sort. It operates in alternating phases:

- **Odd Phase** — Compare and (if needed) swap every pair at odd indices: `(1,2), (3,4), (5,6), …`
- **Even Phase** — Compare and (if needed) swap every pair at even indices: `(0,1), (2,3), (4,5), …`

These two phases alternate until the array is fully sorted. In the **parallel** mode, all comparisons within a single phase happen simultaneously — a key property that makes this algorithm well-suited to parallel hardware like systolic arrays and GPU pipelines.

| Mode       | Time Complexity | Space Complexity |
|------------|----------------|-----------------|
| Sequential | O(n²)          | O(1)            |
| Parallel   | O(n)           | O(n)            |

---

## Tech Stack

| Library       | Version  | Purpose                                  |
|---------------|----------|------------------------------------------|
| pygame-ce     | 2.5.7    | Rendering, input handling, audio mixing  |
| Pillow        | 12.2.0   | Image utilities                          |
| Python        | 3.14     | Core runtime                             |

---

## Prerequisites

- Python 3.10 or higher
- Windows, macOS, or Linux

---

## Installation

**1. Clone the repository**

```bash
git clone https://github.com/your-username/odd-even-sort-visualizer.git
cd odd-even-sort-visualizer
```

**2. Create and activate a virtual environment**

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

---

## Running the Application

```bash
python main.py
```

On Windows, you can also use the provided batch script:

```bash
run.bat
```

---

## Controls

| Control             | Action                                        |
|---------------------|-----------------------------------------------|
| **Play / Pause**    | Start or pause the sorting animation          |
| **Step Forward**    | Advance one comparison step                   |
| **Step Back**       | Rewind one comparison step (scrubber)         |
| **Shuffle**         | Generate a new random array and reset         |
| **Speed Slider**    | Adjust animation speed (slow → fast)          |
| **Mode Toggle**     | Switch between Sequential and Parallel mode   |
| **Sound Toggle**    | Enable / disable PCM audio effects            |
| **Size Buttons**    | Change array size (small → large)             |

---

## Color Legend

| Color         | Meaning                              |
|---------------|--------------------------------------|
| 🟡 Yellow      | Elements currently being compared    |
| 🔴 Coral Red   | Elements being swapped               |
| 🔵 Cyan        | Current selection / insertion marker |
| 🟢 Neon Green  | Fully sorted elements                |
| 🟣 Purple      | Odd phase active pairs               |
| 🔵 Blue        | Even phase active pairs              |
| ⬜ Grey        | Unsorted, idle elements              |

---

## Metrics & Output

Every completed sort run automatically appends a row to **`odd_even_sort_metrics.csv`**:

```csv
Timestamp,Array Size,Mode,Comparisons,Swaps,Cycles
2026-06-17 14:16:16,12,Parallel,55,24,5
```

This file can be opened in Excel, Google Sheets, or analyzed with pandas for performance comparisons across modes and array sizes.

---

## Project Structure

```
Odd-Even Sort Algorithm/
├── main.py                      # Full application source (visualizer, algorithm, UI)
├── requirements.txt             # Python dependencies
├── run.bat                      # Windows launch script
├── odd_even_sort_metrics.csv    # Auto-generated performance log
└── .venv/                       # Virtual environment (not committed to source control)
```

---

## How It Works Internally

`main.py` is structured around several key components:

- **`SortItem`** — A comparable wrapper around array values, enabling instrumented comparisons
- **`oddeven_seq_generator`** — Python generator that yields each step of the sequential algorithm
- **`oddeven_parallel_generator`** — Generator yielding parallel-phase steps with concurrent pair tracking
- **`Bar`** — Animated UI element representing a single array value, with smooth interpolation
- **`SoundEffects`** — Class-level PCM audio synthesizer producing sine-wave tones at specific frequencies
- **`Button`** — Hover-aware UI button with callback support
- **`StarParticle` / `SparkParticle`** — Particle system for background ambience and swap effects

---

## Recommended Use Cases

- **Computer Science education** — Demonstrating parallel vs. sequential sorting trade-offs
- **Algorithm analysis** — Generating comparison/swap counts across different input sizes
- **Parallel computing illustration** — Showing how synchronous phases enable O(n) sort time

---

## License

This project is for educational purposes. See individual library licenses in `.venv/Lib/site-packages/` for third-party terms.

---

## Acknowledgements

- [pygame-ce](https://github.com/pygame-community/pygame-ce) — Community Edition of pygame with active development
- [Pillow](https://python-pillow.org/) — Python Imaging Library fork
- Odd-Even Transposition Sort — Originally described for parallel processor arrays in computer architecture research
