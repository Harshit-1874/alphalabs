# Global Dynamic Island Module

This module provides a modular, iOS-inspired Dynamic Island component for displaying AI trading notifications.

## Structure

```
global-dynamic-island/
├── index.ts                      # Main exports
├── types.ts                      # TypeScript type definitions
├── constants.ts                  # Size mappings and helper functions
├── animated-components.tsx       # Shared animation components (PulseRing, Waveform)
├── island-content.tsx           # Content switcher component
├── island-size-controller.tsx   # Size controller logic
└── content-renderers/           # Individual content renderers
    ├── index.ts
    ├── idle-content.tsx
    ├── analyzing-content.tsx
    ├── narrator-content.tsx
    ├── trade-content.tsx
    ├── alpha-content.tsx
    ├── celebration-content.tsx
    ├── connection-content.tsx
    └── live-session-content.tsx
```

## Usage

```tsx
import { GlobalDynamicIsland } from "@/components/ui/global-dynamic-island";

function App() {
  return (
    <div>
      <GlobalDynamicIsland 
        enableConfetti={true}
        confettiColors={["#22c55e", "#86efac"]}
      />
      {/* Your app content */}
    </div>
  );
}
```

## Content Renderers

Each content renderer is a separate module handling a specific island mode:

- **idle-content**: Default AI ready state
- **analyzing-content**: Shows AI scanning/analyzing with phase indicators
- **narrator-content**: Displays AI thoughts and reasoning
- **trade-content**: Shows trade entry details with price levels
- **alpha-content**: Highlights alpha opportunities detected
- **celebration-content**: Celebrates completed sessions with stats
- **connection-content**: Shows connection status
- **live-session-content**: Displays live session info with PnL

## Customization

You can provide custom renderers for any state:

```tsx
<GlobalDynamicIsland 
  renderTrade={(data, isExpanded) => (
    <CustomTradeView data={data} expanded={isExpanded} />
  )}
/>
```

## Animation Components

Shared animation primitives:

- `PulseRing`: Animated expanding ring for attention
- `Waveform`: Animated waveform for processing states

## Maintenance

When adding new island modes:

1. Add the mode type to `dynamic-island-store.ts`
2. Create a new content renderer in `content-renderers/`
3. Add the mode to size mapping in `constants.ts`
4. Update the switch statement in `island-content.tsx`
5. Export the new renderer from `content-renderers/index.ts`

