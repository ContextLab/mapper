# Knowledge Map Demo - Complete Package

This package contains everything you need to create a web-based knowledge map visualization for your experiment.

## 📦 What's Included

1. **knowledge_map_demo.html** - Complete working demo
   - Single HTML file
   - No dependencies or API keys needed
   - Ready to deploy on GitHub Pages
   - Mobile responsive

2. **implementation_guide.md** - Comprehensive guide
   - Technical approach explanation
   - How to integrate your actual data
   - Enhancement suggestions
   - Deployment instructions

3. **generate_embeddings.py** - Python script
   - Extract questions from experiment.js
   - Generate embeddings
   - Prepare data for web demo
   - Easy to customize

## 🚀 Quick Start

### Option 1: Try the Demo Immediately

Open `knowledge_map_demo.html` in your browser. It works with sample biology questions and demonstrates all features.

### Option 2: Use Your Actual Data

```bash
# Install dependencies
pip install sentence-transformers scikit-learn numpy

# Generate embeddings from your experiment
python generate_embeddings.py --input path/to/experiment.js --output my_questions.json

# Copy the JSON content into the HTML file
# Replace the questionsData array

# Deploy to GitHub Pages
# Your live demo at: https://[username].github.io/knowledge-map-demo
```

## 🎯 Key Features

✅ **No API Keys Required** - Everything runs in the browser
✅ **Single File** - Easy to host and share
✅ **Fast & Responsive** - Works on all devices
✅ **Smooth Animations** - Professional look and feel
✅ **Pre-computed Embeddings** - Instant visualization
✅ **Interactive** - Hover, zoom, and explore

## 📊 How It Works

1. **Questions**: Users answer multiple-choice questions
2. **Embeddings**: Questions are represented as vectors in high-dimensional space
3. **Projection**: Dimensionality reduction to 2D for visualization
4. **Visualization**: Interactive graph showing conceptual relationships
5. **Analysis**: Color-coded by correctness, reveals knowledge structure

## 🔧 Customization

### Change Colors
Edit the CSS gradients and color variables in the HTML file.

### Modify Questions
Replace the `questionsData` array with your own questions and embeddings.

### Adjust Layout
Modify the CSS classes for different spacing, fonts, or animations.

### Add Features
The code is well-commented and modular for easy extension.

## 📈 From Experiment to Web Demo

Your workflow:
```
experiment.js (questions)
    ↓
generate_embeddings.py (process)
    ↓
questions_with_embeddings.json (data)
    ↓
knowledge_map_demo.html (visualization)
    ↓
GitHub Pages (deploy)
```

## 🎨 Example Screenshots

The demo includes:
- Clean, modern interface with gradient header
- Progress bar showing quiz completion
- Multiple-choice questions with hover effects
- Animated 2D knowledge map
- Statistics dashboard (correct, accuracy, total)
- Responsive design for mobile/tablet/desktop

## 📚 Technical Details

**Embeddings**: Pre-computed using sentence-transformers
**Projection**: PCA or t-SNE to 2D coordinates
**Visualization**: HTML5 Canvas with smooth animations
**Interactivity**: Vanilla JavaScript (no frameworks)
**Size**: ~15KB (demo), ~25-80KB with real data

## 🔗 Integration with Your Research

This implementation is designed to match your paper:
- "Text embedding models yield high-resolution insights into conceptual knowledge"
- Uses same embedding approach
- Compatible with Khan Academy question format
- Can visualize knowledge state from quiz responses

## 💡 Next Steps

1. **Review** the demo to understand the user experience
2. **Extract** questions from your experiment.js
3. **Generate** embeddings using the Python script
4. **Integrate** the data into the HTML file
5. **Customize** colors and styling
6. **Test** on multiple devices
7. **Deploy** to GitHub Pages
8. **Share** with participants or in your paper

## 🆘 Troubleshooting

**Q: The embeddings look too clustered**
A: Try t-SNE instead of PCA, or adjust perplexity parameter

**Q: Questions aren't parsing correctly**
A: Customize the regex in `extract_questions_from_js()` function

**Q: Want to add more questions**
A: Just append to the questionsData array with the same structure

**Q: Need better dimensionality reduction**
A: Consider using UMAP (install umap-learn) for better preservation

## 📖 Further Reading

- Your paper: "Text embedding models yield high-resolution insights..."
- Sentence-BERT: https://www.sbert.net/
- UMAP: https://umap-learn.readthedocs.io/
- GitHub Pages: https://pages.github.com/

## 📧 Questions?

Feel free to customize and extend this demo for your research needs. The code is designed to be readable and modular.

---

**Happy Mapping! 🗺️**
