# Data Model: Fix Mobile Mode

**Feature**: 007-fix-mobile-mode | **Date**: 2026-03-10

## Overview

This feature involves no data model changes. All fixes are CSS layout and minor JS DOM manipulation changes. No new entities, no storage changes, no state changes.

## DOM Structure Changes

### Header (index.html)

**Before**:
```
header#app-header
├── .header-left (logo + domain-selector)
└── .header-right (ALL buttons in single scrollable container)
```

**After**:
```
header#app-header
├── .header-left (logo + domain-selector) — unchanged
├── .header-actions (reset, download, upload) — NEW scrollable container
└── .header-right (trophy, video, share, tutorial, info) — existing, now only right-group buttons
```

### Quiz Panel (unchanged structure)

```
#quiz-panel
├── .drawer-pull > .drawer-pull-bar — centering fixed via defensive CSS
├── progress bar — hidden when closed via existing !important rule
└── .quiz-content — padding applied here, not on panel
```
