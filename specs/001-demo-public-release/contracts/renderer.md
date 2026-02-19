# Contract: Renderer Module

**Consumer**: `src/app.js`, `src/ui/controls.js`
**Provider**: `src/viz/renderer.js`, `src/viz/transitions.js`, `src/viz/minimap.js`
**Library**: deck.gl (ScatterplotLayer, HeatmapLayer, OrbitView)

## Renderer Interface

Manages the deck.gl instance rendering articles, questions, and heatmap.

```typescript
// src/viz/renderer.js

interface RendererConfig {
  container: HTMLElement;         // DOM element to mount into
  onViewportChange: (region: Region) => void;  // Notify when pan/zoom changes
  onCellClick: (gx: number, gy: number) => void;
}

interface PointData {
  id: string;
  x: number;
  y: number;
  z: number;                     // PCA-3 for 3D transitions
  type: "article" | "question";
  color: [number, number, number, number];  // RGBA
  radius: number;
}

interface Renderer {
  // Initialize deck.gl with container
  init(config: RendererConfig): void;

  // Update visible points (triggers transition if data changes)
  setPoints(points: PointData[]): void;

  // Update heatmap overlay from knowledge estimates
  setHeatmap(estimates: CellEstimate[], region: Region): void;

  // Update grid labels
  setLabels(labels: GridLabel[]): void;

  // Get current viewport in normalized coordinates
  getViewport(): Region;

  // Animate to a new region (domain switch)
  // Duration in ms; returns promise that resolves on completion
  transitionTo(region: Region, duration?: number): Promise<void>;

  // Destroy deck.gl instance
  destroy(): void;
}
```

**Transition contract (FR-005, FR-020)**:
- When `setPoints()` is called with new coordinates, deck.gl
  interpolates per-point from old → new position over 1000ms
- deck.gl config: `transitions: { getPosition: { duration: 1000, easing: cubicInOut } }`
- Points not in the new set fade opacity from 1→0 over the same duration
- Points new to the set fade opacity from 0→1

**Heatmap contract (FR-003)**:
- `setHeatmap()` renders a HeatmapLayer using the same coordinate system
- Color palette MUST be color-blind safe (FR-023): viridis or cividis
- Heatmap updates within 500ms of new estimates (SC-002)

## Transitions Interface

Handles 3D rotation and per-point animation orchestration.

```typescript
// src/viz/transitions.js

interface TransitionConfig {
  duration: number;              // ms (default: 1000, max: 1000 per SC-003)
  use3D: boolean;                // Whether to use PCA-3 depth rotation
  easing: (t: number) => number; // Easing function
}

interface Transitions {
  // Determine if 3D rotation is needed between two domains
  // Based on spatial overlap of regions
  needs3D(sourceRegion: Region, targetRegion: Region): boolean;

  // Prepare point positions for 3D transition
  // Assigns z-coordinates from PCA-3 data
  prepare3DPositions(
    points: PointData[],
    targetPoints: PointData[]
  ): { source: PointData[], target: PointData[] };
}
```

**3D trigger heuristic**: Use 3D rotation when source and target regions
have <30% spatial overlap (IoU < 0.3). Otherwise, use simple pan/zoom.

## Minimap Interface

Navigation overview graphic (FR-009).

```typescript
// src/viz/minimap.js

interface Minimap {
  // Initialize with full embedding bounds and domain regions
  init(container: HTMLElement, domains: Domain[]): void;

  // Highlight the active domain's region
  setActive(domainId: string): void;

  // Highlight the current viewport within the active domain
  setViewport(viewport: Region): void;

  // Register click handler for domain switching
  onClick(handler: (domainId: string) => void): void;
}
```

**Visual contract**:
- Shows full embedding space (0–1 on both axes)
- Domain regions drawn as labeled rectangles
- Active domain highlighted with accent color
- Current viewport shown as a smaller rectangle within active domain
- Clicking a domain rectangle triggers domain switch (US2)
