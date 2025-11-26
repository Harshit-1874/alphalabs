// Carousel data and constants
export const historicalPrices = [
  42150, 42185, 42170, 42225, 42255, 42250,
  42290, 42325, 42305, 42360, 42395, 42415,
  42380, 42450, 42475, 42490,
];

export const liveDeltaSequence = [15, 5, 7, -12, 8, 4, -3, 10, 0, 7];

export const livePriceClamp = (value: number) => Math.max(42100, Math.min(42900, value));

export const generateTimeLabels = (count: number) => {
  const labels: string[] = [];
  const now = new Date();
  for (let i = count - 1; i >= 0; i -= 1) {
    const time = new Date(now.getTime() - i * 60000);
    labels.push(time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }));
  }
  return labels;
};

export const carouselItems = [
  {
    id: 'sim-replay',
    title: 'Fast Historical Replay',
    subtitle: 'Watch your model make decisions across past markets in accelerated time.',
    bullets: [
      'Candle by candle replay to reveal model behavior',
      'Adjustable replay speed',
      'Shows orders as the model generates them',
    ],
    imageAlt: 'Placeholder GIF of fast moving candle chart',
    action: { label: 'Preview replay', slug: '/arena/preview' },
    visual: 'candles',
  },
  {
    id: 'score-snapshot',
    title: 'Model Thinking and Decisions',
    subtitle: 'See reasoning lines and trade intentions in real time during simulation.',
    bullets: [
      'Full decision trace',
      'Why and when the agent enters or exits',
      'Easy debugging for strategy refinement',
    ],
    imageAlt: 'Placeholder of log lines with decisions',
    action: { label: 'View example', slug: '/example-results' },
    visual: 'pdf',
  },
  {
    id: 'indicator-buffet',
    title: 'Complete Market Data Feed',
    subtitle: 'AlphaLab provides your agent with structured signals.',
    bullets: [
      'Price and indicators included',
      'Volume and volatility metrics',
      'Sentiment and news summaries',
    ],
    imageAlt: 'Chips or tiles representing indicators',
    action: { label: 'See data inputs', slug: '/indicators' },
    visual: 'indicators',
  },
  {
    id: 'modes-compare',
    title: 'Live Paper Trading',
    subtitle: 'Let your model trade simulated orders using live market data.',
    bullets: [
      'Dummy cash environment',
      'Hourly or periodic decision intervals',
      'Safe place to test model reactions',
    ],
    imageAlt: 'Placeholder of live feed ticker and simulated orders',
    action: { label: 'Start paper trading', slug: '/paper-trading' },
    visual: 'modes',
  },
];

