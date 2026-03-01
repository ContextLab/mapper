# Knowledge Mapper

An interactive visualization that maps your conceptual knowledge across 250,000 Wikipedia articles and 5,000+ Khan Academy videos. Answer questions to watch a real-time heatmap of your strengths and gaps emerge, then get personalized video recommendations to fill knowledge gaps.

**[Try the live demo](https://contextlab.github.io/mapper/)** | **[Read the paper](https://osf.io/preprints/psyarxiv/dh3q2)**

## How It Works

1. **Choose a domain** (e.g., Physics, Neuroscience, Computer Science) from the landing page
2. **Answer adaptive questions** -- each one tests conceptual understanding, terminology, and reasoning
3. **Watch the map update** -- correct answers turn nearby regions green; wrong answers reveal red gaps
4. **Get video recommendations** -- Khan Academy videos are suggested based on your weakest areas
5. **Explore freely** -- zoom, pan, hover video trajectories, and click articles for Wikipedia content

Under the hood, text embedding models place every article, question, and video transcript into a shared high-dimensional vector space, then project them onto a 2D map where related concepts cluster together. Density flattening via optimal transport ensures even spatial coverage. As you answer questions, a Bayesian estimator interpolates your knowledge across the map using radial basis functions.

## Features

- **50 knowledge domains** including Physics, Biology, Mathematics, Computer Science, Philosophy, and more
- **2,500 adaptive quiz questions** generated via Claude Opus 4.6 from Wikipedia source articles
- **5,400+ Khan Academy videos** with knowledge-gap-based recommendations
- **Real-time heatmap** powered by Gaussian Process interpolation with Matern 3/2 kernel
- **Video discovery panel** -- left sidebar with toggleable video visibility, scrollable list, and map trajectory highlighting
- **Video trajectories** -- hover a video dot to see its topic path across the map; click to play
- **Knowledge insights** -- see your strongest/weakest concepts and learning suggestions
- **Social sharing** -- export your knowledge map as an image with grid lines and colorbar
- **Keyboard shortcuts** -- press A/B/C/D to answer, with modifier-key awareness to avoid conflicts
- **Fully client-side** -- no data leaves your browser; progress saved to localStorage

## Quick Start

```bash
git clone https://github.com/ContextLab/mapper.git
cd mapper
npm install
npm run dev
```

Open [http://localhost:5173/mapper/](http://localhost:5173/mapper/) in your browser.

### Production Build

```bash
npm run build   # outputs to dist/
npm run preview # preview the production build locally
```

## Project Structure

```
mapper/
├── index.html          # HTML entry point (layout, styles, modals)
├── src/                # Application source code
│   ├── app.js          # Entry point: init, routing, event wiring
│   ├── domain/         # Domain data loading and registry
│   ├── learning/       # Adaptive quiz engine + video recommender
│   ├── state/          # Application state and persistence
│   ├── ui/             # UI components (controls, quiz, insights, share, video panel/modal)
│   ├── utils/          # Math, accessibility, feature detection
│   └── viz/            # Canvas rendering (heatmap, minimap, particles)
├── data/               # Pre-computed data bundles
│   ├── domains/        # 50 per-domain JSON bundles + index.json
│   └── videos/         # Video catalog + transcripts + embeddings
├── scripts/            # Python data pipeline
├── tests/              # Unit tests (vitest) + E2E tests (Playwright)
└── public/             # Static assets
```

## Data Pipeline

The `scripts/` directory contains the Python pipeline that generates the data powering the frontend:

1. **Embed articles** using `google/embeddinggemma-300m` (768-dim vectors)
2. **Generate questions** via Claude Opus 4.6 (50 per domain, 2,450 total)
3. **Embed questions** using the same model (for coordinate consistency)
4. **Transcribe videos** via Whisper on GPU cluster (5,400+ Khan Academy transcripts)
5. **Embed transcripts** -- both full-document and sliding-window (512 words, 50-word stride)
6. **Joint UMAP projection** -- project articles + questions + transcripts TOGETHER to 2D
7. **Density flattening** via approximate optimal transport (`mu=0.85`)
8. **Apply coordinates** to all domain bundles and video catalog
9. **Compute bounding boxes** from question positions (5th-95th percentile)

## Testing

```bash
npx vitest run        # 82 unit tests (estimator, sampler, recommender, stability)
npx playwright test   # 9 E2E test specs (quiz flow, video recs, sharing, edge cases)
```

## Citation

```bibtex
@article{fitzpatrick2025mapper,
  title={Text embedding models yield detailed conceptual knowledge maps derived from short multiple-choice quizzes},
  author={Fitzpatrick, Paxton C. and Heusser, Andrew C. and Manning, Jeremy R.},
  year={2025},
  url={https://psyarxiv.com/dh3q2}
}
```

## License

[CC BY-NC-SA 4.0](LICENSE) -- Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International

## Contributing

This is a research project from the [Contextual Dynamics Lab](https://www.context-lab.com/) at Dartmouth College. For questions or collaboration inquiries, please [open an issue](https://github.com/ContextLab/mapper/issues).
