import React, { useEffect, useState } from 'react';
import { Image as ImageIcon, ChevronLeft, ChevronRight } from 'lucide-react';

const DEFECT_CLASSES = ['all', 'crazing', 'inclusion', 'patches', 'pitted_surface', 'rolled-in_scale', 'scratches'];

export default function DatasetExplorer() {
  const [summary, setSummary] = useState<any>(null);
  const [images, setImages] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [split, setSplit] = useState('train');
  const [page, setPage] = useState(0);
  const [selectedImage, setSelectedImage] = useState<any>(null);
  const limit = 24;

  useEffect(() => {
    fetch('/api/dataset/summary').then(r => r.json()).then(setSummary).catch(console.error);
  }, []);

  useEffect(() => {
    setLoading(true);
    fetch(`/api/dataset/images?split=${split}&defect_class=${filter}&limit=${limit}&offset=${page * limit}`)
      .then(r => r.json())
      .then(d => {
        setImages(d.images || []);
        setTotal(d.total || 0);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [filter, split, page]);

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div>
        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-100 to-slate-400 mb-1">Dataset Explorer</h1>
        <p className="text-slate-400">NEU Surface Defect Database — {summary?.total_images || '...'} images across {summary?.n_classes || '...'} defect classes</p>
      </div>

      {/* Stats bar */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {[
            { label: 'Total', value: summary.total_images },
            { label: 'Classes', value: summary.n_classes },
            { label: 'Train', value: summary.train_total },
            { label: 'Validation', value: summary.validation_total },
            { label: 'Dimensions', value: summary.original_dimensions || '200×200' },
          ].map(({ label, value }) => (
            <div key={label} className="bg-surface border border-border rounded-xl px-4 py-3">
              <div className="text-lg font-bold text-slate-200">{value}</div>
              <div className="text-xs text-slate-500 uppercase font-medium">{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex bg-surface border border-border rounded-lg p-1">
          {['train', 'validation'].map(s => (
            <button key={s} onClick={() => { setSplit(s); setPage(0); }}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all capitalize ${split === s ? 'bg-blue-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'}`}
            >{s}</button>
          ))}
        </div>

        <div className="flex flex-wrap gap-2">
          {DEFECT_CLASSES.map(cls => (
            <button key={cls} onClick={() => { setFilter(cls); setPage(0); }}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all capitalize ${
                filter === cls
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-500/50'
                  : 'bg-surface border border-border text-slate-400 hover:text-slate-200'
              }`}
            >{cls === 'all' ? 'All Classes' : cls.replace(/[_-]/g, ' ')}</button>
          ))}
        </div>

        <div className="ml-auto text-sm text-slate-500">
          Showing {images.length} of {total} images
        </div>
      </div>

      {/* Image grid */}
      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="aspect-square bg-surface rounded-xl animate-pulse border border-border" />
          ))}
        </div>
      ) : images.length === 0 ? (
        <div className="h-48 flex items-center justify-center text-slate-500 border border-dashed border-slate-700 rounded-xl bg-surface/30">
          <div className="text-center">
            <ImageIcon size={32} className="mx-auto mb-2 text-slate-700" />
            <p>No images found for this filter combination.</p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {images.map((img, i) => (
            <div key={i}
              onClick={() => setSelectedImage(img)}
              className="group relative bg-surface border border-border rounded-xl overflow-hidden hover:-translate-y-1 transition-all shadow-md hover:shadow-blue-500/10 cursor-pointer"
            >
              <div className="aspect-square bg-slate-900 overflow-hidden">
                <img src={img.url} alt={img.name} className="object-cover w-full h-full opacity-80 group-hover:opacity-100 group-hover:scale-105 transition-all duration-300" />
              </div>
              <div className="p-2 bg-surface border-t border-border/50">
                <div className="text-xs font-semibold text-slate-300 capitalize truncate">{img.defect_class.replace(/[_-]/g, ' ')}</div>
                <div className="text-[10px] text-slate-500 font-mono truncate">{img.name}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3">
          <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}
            className="p-2 rounded-lg bg-surface border border-border text-slate-400 hover:text-white disabled:opacity-30 transition-colors">
            <ChevronLeft size={18} />
          </button>
          <span className="text-sm text-slate-400">Page {page + 1} of {totalPages}</span>
          <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1}
            className="p-2 rounded-lg bg-surface border border-border text-slate-400 hover:text-white disabled:opacity-30 transition-colors">
            <ChevronRight size={18} />
          </button>
        </div>
      )}

      {/* Image viewer modal */}
      {selectedImage && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-8" onClick={() => setSelectedImage(null)}>
          <div className="bg-surface border border-border rounded-2xl p-6 max-w-2xl w-full shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-lg font-bold text-slate-200 capitalize">{selectedImage.defect_class.replace(/[_-]/g, ' ')}</h3>
                <p className="text-sm text-slate-400 font-mono">{selectedImage.name}</p>
              </div>
              <button onClick={() => setSelectedImage(null)} className="text-slate-500 hover:text-white text-xl">×</button>
            </div>
            <div className="bg-slate-900 rounded-xl overflow-hidden border border-slate-800">
              <img src={selectedImage.url} alt={selectedImage.name} className="w-full" />
            </div>
            <div className="flex justify-between items-center mt-4">
              <span className="text-sm text-slate-400">200 × 200 px • {selectedImage.split} split</span>
              <a href={`/quantum?image=${selectedImage.name}&class=${selectedImage.defect_class}`}
                className="px-4 py-2 bg-blue-600/20 text-blue-400 border border-blue-500/50 rounded-lg text-sm font-medium hover:bg-blue-600/30 transition-colors">
                Open in Quantum Lab →
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
