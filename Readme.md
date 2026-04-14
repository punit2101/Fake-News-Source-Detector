# Fake News Source Detection Using Reverse BFS

A Graph-Based Algorithm for Identifying Misinformation Sources in Social Networks

**Accuracy:** 87% | **Time:** 0.349 seconds on 2000-node dataset

---

## Quick Start

### 1. Install Dependencies

```bash
pip install networkx plotly scipy
```

### 2. Compile C Program

```bash
gcc -o prog source_detection.c
```

### 3. Run Algorithm

### Windows

```bash
Get-Content data.txt | ./prog
```

### Mac/Linux

```bash
./prog < data.txt
```

### 4. Generate Visualization

```bash
python visualization.py
```

### 5. View Visualization Results

### Windows

start output/source_detection_enhanced.html

### macOS

open output/source_detection_enhanced.html

### Linux

firefox output/source_detection_enhanced.html

---
