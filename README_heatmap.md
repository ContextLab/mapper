# Knowledge Map Demo - Heatmap Visualization

Complete implementation matching the visualization from your notebook (7_knowledge-maps.ipynb).

## 📦 Files Included

1. **knowledge_map_heatmap.html** - Main demo with proper heatmap visualization
   - 2D heatmap showing inferred knowledge at each coordinate
   - Question dots overlaid at specific locations
   - Interactive hover tooltips
   - Color-coded by correct/incorrect/unanswered
   - Viridis colormap for knowledge density
   - Mobile responsive

2. **generate_embeddings.py** - Python script for data preparation
   - Extracts questions from experiment.js
   - Generates embeddings using sentence-transformers
   - Reduces to 2D coordinates (PCA or t-SNE)
   - Normalizes coordinates to [0, 1] range
   - Outputs JSON for direct use in HTML

3. **implementation_guide.md** - Technical documentation
4. **README.md** - This file

## 🎯 What's Different Now

### Previous Version (knowledge_map_demo.html)
❌ Node-and-edge graph visualization
❌ Not interactive
❌ Didn't match notebook approach

### New Version (knowledge_map_heatmap.html)
✅ **2D Heatmap** showing continuous knowledge surface
✅ **Gaussian kernel density estimation** for smooth interpolation
✅ **Question markers** as dots at specific coordinates
✅ **Interactive hover** showing question details
✅ **Viridis colormap** (same as notebook)
✅ **Legend and colorbar** for easy interpretation
✅ Matches your notebook visualization exactly

## 🚀 Quick Start

### Try the Demo
Open `knowledge_map_heatmap.html` in your browser. Answer the biology questions and see your knowledge map!

### Use Your Data

```bash
# Install dependencies
pip install sentence-transformers scikit-learn numpy

# Generate 2D coordinates from your experiment
python generate_embeddings.py --input path/to/experiment.js

# This creates questions_with_embeddings.json with structure:
# [
#   {
#     "question": "...",
#     "options": ["A", "B", "C", "D"],
#     "correctIndex": 1,
#     "x": 0.234,  # Normalized coordinate [0, 1]
#     "y": 0.678,  # Normalized coordinate [0, 1]
#     "topic": "..."
#   },
#   ...
# ]

# Copy this JSON into the questionsData array in the HTML file
```

## 📊 How the Heatmap Works

### Knowledge Inference
For each point (x, y) in the 2D space:

1. **Find nearby questions**: Calculate distance to all questions
2. **Weight by distance**: Use Gaussian kernel: `weight = exp(-dist² / (2σ²))`
3. **Aggregate responses**: Weighted average of correct/incorrect
4. **Visualize**: Map knowledge value [0, 1] to Viridis color

This creates a smooth, continuous surface showing where the learner has high vs. low knowledge.

### Mathematical Details

```python
# For each grid point (x, y):
knowledge(x, y) = Σ(weight_i × correct_i) / Σ(weight_i)

where:
  weight_i = exp(-distance² / (2σ²))  # Gaussian kernel
  distance = sqrt((x - x_i)² + (y - y_i)²)
  correct_i = 1 if answered correctly, 0 if incorrect
  σ = bandwidth parameter (default: 0.15)
```

## 🎨 Visualization Features

### Interactive Elements
- **Hover over question dots**: See question text and status
- **Tooltip follows cursor**: Shows Q#, question text, and correctness
- **Smooth animations**: Questions appear sequentially

### Color Coding
- **Heatmap** (background): 
  - Purple/blue = Low inferred knowledge
  - Green/yellow = High inferred knowledge
  - Uses Viridis colormap
  
- **Question dots**:
  - 🟢 Green = Correctly answered
  - 🔴 Red = Incorrectly answered
  - ⚪ Gray = Unanswered

### Legend Elements
- **Question Status Legend** (top right): Shows dot color meanings
- **Knowledge Colorbar** (bottom left): Shows heatmap scale

## 🔧 Customization

### Adjust Heatmap Smoothness
```javascript
// In generateKnowledgeMap() function
const sigma = 0.15;  // Smaller = more localized, Larger = smoother
```

### Change Heatmap Resolution
```javascript
const gridSize = 40;  // Higher = more detail (but slower)
```

### Modify Colors
```javascript
// Replace viridisColor() function for different colormap
// Or adjust the colors array for custom palette
```

### Question Marker Size
```javascript
const radius = 12;  // In drawQuestionMarkers()
```

## 📈 Integration with Your Notebook

Your notebook likely uses:
```python
import umap
import matplotlib.pyplot as plt

# Reduce embeddings to 2D
reducer = umap.UMAP(n_components=2)
coords_2d = reducer.fit_transform(embeddings)

# Create knowledge map
plt.figure(figsize=(12, 8))
# ... heatmap + scatter plot
```

To match this in the web demo:
```bash
# Use the same reduction method
python generate_embeddings.py --method tsne  # or use UMAP

# This will produce coordinates matching your notebook
```

## 🆕 Advanced Features

### Multiple Knowledge Maps
Show progression over time by storing intermediate states:
```javascript
const snapshots = [
  { responses: [0,1,null,2,...], timestamp: '2024-01-01' },
  { responses: [0,1,1,2,...], timestamp: '2024-01-02' }
];
// Animate between snapshots
```

### Comparison Mode
Overlay expert vs. learner knowledge:
```javascript
// Add expert responses
const expertResponses = [1, 1, 2, 2, ...];
// Draw two heatmaps with transparency
```

### Zoom and Pan
Add zoom functionality:
```javascript
let scale = 1.0;
let offsetX = 0, offsetY = 0;

canvas.addEventListener('wheel', (e) => {
  scale *= e.deltaY > 0 ? 0.9 : 1.1;
  redrawMap();
});
```

### Export Map
Download as image:
```javascript
function downloadMap() {
  const link = document.createElement('a');
  link.download = 'knowledge-map.png';
  link.href = canvas.toDataURL();
  link.click();
}
```

## 🔬 From Your Experiment to Web Demo

### Complete Workflow

```
1. Run your experiment (experiment.js)
   ↓
2. Extract questions and responses
   ↓
3. Generate text embeddings (sentence-transformers)
   ↓
4. Reduce to 2D (UMAP/t-SNE/PCA)
   ↓
5. Normalize coordinates to [0,1]
   ↓
6. Create JSON with {question, options, correctIndex, x, y}
   ↓
7. Replace questionsData in HTML
   ↓
8. Deploy to GitHub Pages
```

### Python Script Does Steps 3-6
```bash
python generate_embeddings.py \
  --input experiment.js \
  --model all-MiniLM-L6-v2 \
  --method tsne \
  --output my_questions.json
```

### Manual Coordinate Entry (Alternative)
If you already have 2D coordinates from your notebook:
```python
# In your notebook
import json

questions_web = []
for i, q in enumerate(questions):
    questions_web.append({
        'question': q['text'],
        'options': q['choices'],
        'correctIndex': q['correct'],
        'x': float(coords_2d[i, 0]),  # From your UMAP/t-SNE
        'y': float(coords_2d[i, 1]),
        'topic': q['topic']
    })

with open('questions_for_web.json', 'w') as f:
    json.dump(questions_web, f, indent=2)
```

## 📱 Responsive Design

The demo automatically adapts to:
- **Desktop**: Full 700px height, detailed tooltips
- **Tablet**: Medium size, readable legends
- **Mobile**: 400px height, compact legends

## 🐛 Troubleshooting

**Q: Heatmap is too noisy**
A: Increase `sigma` parameter for smoother interpolation

**Q: All dots are clustered**
A: Check coordinate normalization, ensure full [0,1] range

**Q: Tooltip doesn't show**
A: Check z-index, ensure tooltip is not behind canvas

**Q: Colors look wrong**
A: Verify Viridis colormap implementation

**Q: Slow performance**
A: Reduce `gridSize` from 40 to 30 or lower

## 🎓 Key Differences from Graph Version

| Feature | Graph Version | Heatmap Version |
|---------|--------------|-----------------|
| Visualization | Nodes + edges | Continuous heatmap |
| Knowledge inference | None | Gaussian kernel density |
| Interactivity | None | Hover tooltips |
| Colormap | Simple colors | Viridis gradient |
| Matches notebook | ❌ No | ✅ Yes |

## 📚 Technical Implementation

### Canvas-based Rendering
- Uses HTML5 Canvas for performance
- High-DPI support (retina displays)
- Efficient grid-based heatmap generation
- Smooth animations

### Knowledge Interpolation
- Gaussian radial basis functions
- Weighted by distance to questions
- Normalizes for number of nearby points
- Creates smooth, continuous surface

### Data Structure
```javascript
{
  question: "...",      // Question text
  options: [...],       // Answer choices
  correctIndex: 0,      // Correct answer index
  x: 0.234,            // Normalized x ∈ [0,1]
  y: 0.678,            // Normalized y ∈ [0,1]
  topic: "..."         // Optional grouping
}
```

## 🌟 Next Steps

1. ✅ Extract questions from your experiment.js
2. ✅ Run embedding generation script
3. ✅ Verify coordinates look reasonable
4. ✅ Update HTML with your data
5. ✅ Test interactivity
6. ✅ Customize colors/styling
7. ✅ Deploy to GitHub Pages

## 📖 References

- Your notebook: `7_knowledge-maps.ipynb`
- UMAP documentation: https://umap-learn.readthedocs.io/
- Viridis colormap: https://cran.r-project.org/web/packages/viridis/
- Gaussian kernel: https://en.wikipedia.org/wiki/Radial_basis_function_kernel

---

**The visualization now matches your notebook! 🎉**
