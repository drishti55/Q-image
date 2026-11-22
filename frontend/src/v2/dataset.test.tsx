import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import App from '../App';
import { filterImages, type DatasetImage } from './pages/DatasetGallery';

class RO { observe() {} unobserve() {} disconnect() {} }
vi.stubGlobal('ResizeObserver', RO);
afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.stubGlobal('ResizeObserver', RO); window.history.pushState({}, '', '/'); });

const CL = ['crazing', 'inclusion', 'patches', 'pitted_surface', 'rolled-in_scale', 'scratches'];
const images: DatasetImage[] = CL.flatMap((c, ci) => [1, 2, 3].map((i) => ({
  path: `${i === 3 ? 'validation' : 'train'}/images/${c}/${c}_${i}.jpg`, name: `${c}_${i}.jpg`, class: c,
  folder: (i === 3 ? 'validation' : 'train') as DatasetImage['folder'], split_seed0: (i === 3 ? 'test' : i === 2 ? 'val' : 'train') as DatasetImage['split_seed0'],
  index: i, block: 0, sha256: `${ci}${i}`.padEnd(64, '0'), width: 200, height: 200, frac_correct: i === 3 ? 0.5 : null,
})));
const data = { manifest_id: 'neu-test', classes: CL, n: images.length, split_id: 's0', n_models: 163, images };

function mockApi() {
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (url.startsWith('/api/v4/dataset')) return { ok: true, status: 200, json: async () => data };
    if (url.startsWith('/api/v2/health')) return { ok: true, status: 200, json: async () => ({ analysis_present: true, api_version: '2', n_selected: 88 }) };
    return { ok: false, status: 404, statusText: 'Not Found', json: async () => ({ detail: 'Not Found' }) };
  }));
}

describe('dataset gallery', () => {
  it('filters by class and folder', () => {
    expect(filterImages(images, 'all', 'all')).toHaveLength(18);
    expect(filterImages(images, 'patches', 'all')).toHaveLength(3);
    expect(filterImages(images, 'all', 'validation')).toHaveLength(6);
    expect(filterImages(images, 'scratches', 'train').map((x) => x.index)).toEqual([1, 2]);
  });

  it('shows every image, filters by class, opens the viewer and steps with the arrow keys', async () => {
    mockApi();
    window.history.pushState({}, '', '/dataset');
    render(<App />);
    await waitFor(() => expect(screen.getByTestId('dataset-count').textContent).toContain('18'));
    fireEvent.click(screen.getByRole('button', { name: 'Patches' }));
    expect(screen.getByTestId('dataset-count').textContent).toContain('3');
    fireEvent.click(screen.getByTitle('patches_1.jpg · Patches'));
    expect(screen.getByRole('dialog', { name: 'Image patches_1.jpg' })).toBeTruthy();
    fireEvent.keyDown(window, { key: 'ArrowRight' });
    expect(screen.getByRole('dialog', { name: 'Image patches_2.jpg' })).toBeTruthy();
    fireEvent.keyDown(window, { key: 'ArrowLeft' });
    fireEvent.keyDown(window, { key: 'ArrowLeft' });
    expect(screen.getByRole('dialog', { name: 'Image patches_3.jpg' })).toBeTruthy();
    expect(screen.getByText('50%')).toBeTruthy();
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByRole('dialog')).toBeNull();
  });
});
