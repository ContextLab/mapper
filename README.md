# Knowledge Mapper

An interactive visualization that maps your conceptual knowledge across 250,000 Wikipedia articles. Answer questions to watch a real-time heatmap of your strengths and gaps emerge.

**[Try the live demo](https://contextlab.github.io/mapper/)** | **[Read the paper](https://psyarxiv.com/dh3q2)**

## How It Works

1. **Choose a domain** (e.g., Physics, Neuroscience, Mathematics) from the landing page
2. **Answer adaptive questions** — each one tests conceptual understanding, terminology, and reasoning
3. **Watch the map update** — correct answers turn nearby regions green; wrong answers reveal red gaps
4. **Explore freely** — zoom, pan, and click on articles to see Wikipedia content

Under the hood, text embedding models place every article into a high-dimensional vector space, then project it onto a 2D map where related concepts cluster together. As you answer questions, a Bayesian estimator interpolates your knowledge across the map using radial basis functions — so demonstrating expertise in one area provides evidence about related topics nearby.

## Features

- **19 knowledge domains** with hierarchical sub-domains (e.g., Physics → Astrophysics, Quantum Physics)
- **~950 adaptive quiz questions** generated from Wikipedia source articles
- **Real-time heatmap** powered by radial basis function interpolation
- **Knowledge insights** — see your strongest/weakest concepts and get learning suggestions
- **Social sharing** — export your knowledge map as an image or share a link
- **Fully client-side** — no data leaves your browser; progress saved to localStorage

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
├── index.html          ← HTML entry point (layout, styles, modals)
├── src/                ← Application source code (see src/README.md)
│   ├── app.js          ← Entry point: init, routing, event wiring
│   ├── domain/         ← Domain data loading and registry
│   ├── learning/       ← Adaptive quiz engine (Bayesian estimation)
│   ├── state/          ← Application state and persistence
│   ├── ui/             ← UI components (controls, quiz, insights, share)
│   ├── utils/          ← Math, accessibility, feature detection
│   └── viz/            ← Canvas rendering (heatmap, minimap, particles)
├── data/               ← Pre-computed domain bundles (JSON)
│   └── domains/        ← Per-domain question + article + label bundles
├── scripts/            ← Data pipeline scripts (see scripts/README.md)
├── public/             ← Static assets copied to dist/
└── tests/              ← Visual regression tests
```

## Data Pipeline

The `scripts/` directory contains the Python pipeline that generates the data powering the frontend. It processes 250K Wikipedia articles through:

1. Embedding with `google/embeddinggemma-300m`
2. UMAP dimensionality reduction to 2D
3. Optimal-transport density flattening
4. Domain region definition and RAG-based article assignment
5. Question generation via GPT-5-nano
6. Coordinate projection and cell label precomputation

See [`scripts/README.md`](scripts/README.md) for full pipeline documentation.

## Citation

```bibtex
@article{manning2025mapper,
  title={Text embedding models yield high-resolution insights into conceptual knowledge},
  author={Manning, Jeremy R},
  year={2025},
  url={https://psyarxiv.com/dh3q2}
}
```

## License

[CC BY-NC-SA 4.0](LICENSE) — Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International

## Contributing

This is a research project from the [Contextual Dynamics Lab](https://www.context-lab.com/) at Dartmouth College. For questions or collaboration inquiries, please [open an issue](https://github.com/ContextLab/mapper/issues).
