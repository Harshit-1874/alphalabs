'use client';

import { LivePriceChart } from './live-price-chart';
import { PDFPreview } from './pdf-preview';
import { IndicatorChips } from './indicator-chips';
import { ModesCompare } from './modes-compare';

type SlideVisualProps = {
  type: string;
};

export function SlideVisual({ type }: SlideVisualProps) {
  switch (type) {
    case 'candles':
      return <LivePriceChart />;
    case 'pdf':
      return <PDFPreview />;
    case 'indicators':
      return <IndicatorChips />;
    case 'modes':
      return <ModesCompare />;
    default:
      return null;
  }
}

