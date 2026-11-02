// Use the /vitest entry: the plain '@testing-library/jest-dom' import needs a global `expect`.
import '@testing-library/jest-dom/vitest';
import {afterEach} from 'vitest';
import {cleanup} from '@testing-library/react';

// Without globals enabled, Testing Library does not unmount between tests on its own.
afterEach(cleanup);

// jsdom has no ResizeObserver, which Recharts' <ResponsiveContainer> requires.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= ResizeObserverStub;
