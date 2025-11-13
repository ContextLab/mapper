# Knowledge Map Demo - Implementation Guide

## Overview
This prototype demonstrates a single-file HTML implementation of a knowledge map visualization based on your lab's "Text embedding models yield high-resolution insights into conceptual knowledge" paper. The demo can be hosted directly on GitHub Pages without any API keys or backend services.

## What's Implemented

### 1. Quiz Interface
- Khan Academy-style multiple choice questions
- Smooth animations and transitions
- Progress tracking
- Responsive design (mobile, tablet, desktop)
- Previous/Next navigation

### 2. Knowledge Map Visualization
- 2D projection of conceptual space
- Color-coded by correctness (green=correct, red=incorrect, gray=unanswered)
- Animated node appearance
- Connection lines between related concepts
- Interactive hover effects
- Real-time statistics

### 3. Pre-computed Embeddings
- Questions include 5D embeddings stored as JSON
- Simple projection to 2D for visualization (weighted combination of dimensions)
- No external API calls needed

## Technical Approach

### Embedding Strategy
**Current Implementation:**
- Pre-computed 5D embeddings stored directly in the HTML
- Simple linear projection to 2D for visualization
- Embeddings can be generated offline using:
  - Sentence-BERT
  - Universal Sentence Encoder
  - OpenAI embeddings (run once, store results)

**To Use Your Actual Data:**
1. Extract question text from `experiment.js`
2. Generate embeddings using your preferred model
3. Apply dimensionality reduction (PCA/UMAP) or store full embeddings
4. Store reduced 2D coordinates or higher-dimensional embeddings in JSON

### Advantages of This Approach
✅ No API keys needed
✅ Works offline after initial load
✅ Fast - all computation client-side
✅ Easy to host on GitHub Pages
✅ Fully self-contained single file
✅ Responsive across all devices
✅ Smooth animations

## Integrating Your Actual Experiment

### Step 1: Extract Questions from experiment.js
```javascript
// Your experiment.js likely has questions in a structure like:
const questions = [
    {
        question: "...",
        choices: ["A", "B", "C", "D"],
        correct: 1
    }
];
```

### Step 2: Generate Embeddings
```python
# Python script to generate embeddings
from sentence_transformers import SentenceTransformer
import json
import numpy as np
from sklearn.decomposition import PCA

# Load model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Your questions
questions = [...]  # Load from experiment.js

# Generate embeddings
embeddings = model.encode([q['question'] for q in questions])

# Option A: Store 2D projections (smaller file)
pca = PCA(n_components=2)
embeddings_2d = pca.fit_transform(embeddings)

# Option B: Store full embeddings for more flexibility
# You can do dimensionality reduction in JavaScript

# Save as JSON
output = []
for i, q in enumerate(questions):
    output.append({
        'question': q['question'],
        'options': q['choices'],
        'correctIndex': q['correct'],
        'embedding': embeddings_2d[i].tolist()  # or embeddings[i].tolist()
    })

with open('questions_with_embeddings.json', 'w') as f:
    json.dump(output, f)
```

### Step 3: Integrate into HTML
Replace the `questionsData` array in the HTML with your generated data.

## Advanced Enhancements

### 1. Better Dimensionality Reduction (JavaScript)
Currently using simple linear projection. For better results:

```javascript
// Option A: Use UMAP.js
// Include: <script src="https://cdn.jsdelivr.net/npm/umap-js@1.3.3/lib/umap-js.min.js"></script>
const umap = new UMAP.UMAP();
const embedding = umap.fit(highDimEmbeddings);

// Option B: Use TensorFlow.js PCA
// Include: <script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs"></script>
// More accurate PCA implementation
```

### 2. Topic Clustering
Enhance visualization by grouping related concepts:
```javascript
// Add colored regions for different topics
const topicColors = {
    'cell_organelles': '#FF6B6B',
    'photosynthesis': '#4ECDC4',
    'genetics': '#45B7D1',
    'molecular_biology': '#FFA07A'
};
```

### 3. Dynamic Knowledge Tracking
Show how knowledge "evolves" as user progresses:
```javascript
// Animate map growth question by question
// Show prediction vs actual performance
```

### 4. Comparison Mode
Compare user's map to expert performance:
```javascript
// Overlay expert knowledge map
// Highlight gaps in understanding
```

### 5. Interactive Features
- Click nodes to see question details
- Zoom/pan functionality
- Filter by topic or correctness
- Export map as image

## Connecting to Your Notebook (7_knowledge-maps.ipynb)

Your notebook likely uses:
1. Text embeddings (sentence-transformers, OpenAI, etc.)
2. UMAP or t-SNE for dimensionality reduction
3. Matplotlib/Plotly for visualization

To replicate this in the web demo:

### Extract the Key Components:
```python
# From your notebook
import pickle

# After running your analysis
reduced_embeddings = umap_model.fit_transform(embeddings)
question_metadata = [...]  # Your question data

# Save for web
web_data = {
    'questions': questions,
    'embeddings': reduced_embeddings.tolist(),
    'topics': topics,
    'correct_answers': correct_answers
}

with open('knowledge_map_data.json', 'w') as f:
    json.dump(web_data, f)
```

### Use in HTML:
```javascript
// Load the JSON data directly into the HTML
const knowledgeMapData = {
    // ... paste the JSON content here
};
```

## Browser-Based Embedding Generation (Advanced)

If you want to compute embeddings entirely in the browser:

```html
<!-- Include TensorFlow.js and Universal Sentence Encoder -->
<script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs"></script>
<script src="https://cdn.jsdelivr.net/npm/@tensorflow-models/universal-sentence-encoder"></script>

<script>
async function generateEmbeddings() {
    const model = await use.load();
    const embeddings = await model.embed(questions);
    return embeddings.array();
}
</script>
```

**Caveat:** This downloads ~50MB model on first load. Better to pre-compute.

## Performance Optimization

### For Large Question Sets (100+ questions):
1. **Lazy loading**: Load questions in batches
2. **Canvas optimization**: Use requestAnimationFrame for smooth rendering
3. **WebGL**: For complex visualizations with many nodes
4. **Web Workers**: Compute embeddings/projections in background

### File Size Considerations:
- Current demo: ~15KB
- With 50 questions + embeddings: ~25KB
- With 200 questions: ~80KB
- Still easily under GitHub Pages limits

## Deployment to GitHub Pages

1. Create repository: `knowledge-map-demo`
2. Add HTML file as `index.html`
3. Enable GitHub Pages in repository settings
4. Access at: `https://[username].github.io/knowledge-map-demo`

## Next Steps

### To Productionize:
1. ✅ Extract questions from your `experiment.js`
2. ✅ Generate embeddings using your preferred model
3. ✅ Apply dimensionality reduction (match your notebook)
4. ✅ Replace questionsData in HTML
5. ✅ Customize colors/styling to match your lab branding
6. ✅ Test on mobile devices
7. ✅ Deploy to GitHub Pages

### Optional Enhancements:
- Add more sophisticated topic detection
- Include video snippets (like in your experiment)
- Show learning trajectory over time
- Compare multiple users' knowledge maps
- Add export functionality (PNG/PDF)

## References

Your paper implementation:
- Experiment: `github.com/ContextLab/efficient-learning-khan/exp/`
- Analysis: `github.com/ContextLab/efficient-learning-khan/code/notebooks/`

Key libraries that could enhance this:
- UMAP.js: Fast dimensionality reduction
- D3.js: Advanced visualizations
- TensorFlow.js: In-browser ML
- Chart.js: Statistics visualizations

## Questions & Customization

Feel free to:
- Adjust colors, fonts, animations
- Add your university branding
- Modify question format
- Change visualization style
- Add additional metrics

The code is well-commented and modular for easy customization!
