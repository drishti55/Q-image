/* eslint-disable @typescript-eslint/no-explicit-any */
import type { ReactNode } from 'react';

export type Cell = { r: number; c: number };
export const GIVEN: Cell[] = [{ r: 0, c: 0 }, { r: 0, c: 1 }, { r: 1, c: 0 }, { r: 1, c: 1 }];

/** One stage of the selected pixel's journey through an algorithm. `short` is shown inside the pixel cell. */
export type TraceItem = { key: string; label: string; value: string; short?: string };

export type Ctx = {
  d: any;                       // V3 playground data (GET /api/v3/playground)
  o: Record<string, string>;    // algorithm options (bits, fmap, shots)
  sel: number;                  // selected given pixel 0..3
  px: { r: number; c: number; v: number };
};

export type Step = {
  title: string;
  explain: string;              // what is happening
  why: string;                  // why the operation is needed
  formula?: ReactNode;
  out?: ReactNode;              // actual calculated output (real values)
  interp: string;               // classical or quantum interpretation
  stage?: string;               // TraceItem key highlighted in the pixel journey
  grid?: 'demo' | 'padded';
  hl?: 'selected' | 'given' | 'none';
  body: ReactNode;              // centre visual
};

export type Algo = {
  id: string;
  family: 'classical' | 'quantum';
  name: string;
  blurb: string;
  options?: { key: string; label: string; values: [string, string][]; def: string }[];
  steps: (c: Ctx) => Step[];
  trace: (c: Ctx) => TraceItem[];
};

export const f4 = (v: number) => v.toFixed(4);
export const bin8 = (v: number) => v.toString(2).padStart(8, '0');
export const theta = (v: number) => (Math.PI / 2) * (v / 255);
