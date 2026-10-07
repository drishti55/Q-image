import csv
from pathlib import Path
import sys
sys.path.insert(0, str(Path('.')))

from src.metrics.evaluator import ExperimentResult, ResultsManager
from src.visualization.plotter import ResultPlotter

rm = ResultsManager()
raw_results = rm.load_results_csv('results/experiments/all_results.csv')

def fix_row(r):
    for k, v in r.items():
        if isinstance(v, str):
            if v == 'inf':
                r[k] = 100.0
            elif v == 'nan':
                r[k] = 0.0
            else:
                try:
                    r[k] = int(v)
                except ValueError:
                    try:
                        r[k] = float(v)
                    except ValueError:
                        pass
    return ExperimentResult(**r)

fixed_results = [fix_row(r) for r in raw_results]

plotter = ResultPlotter()
print("Plotting resource_vs_resolution...")
plotter.plot_resource_vs_resolution([r for r in fixed_results if r.dataset == 'synthetic' and r.shots == 1000])
print("Plotting precision_comparison...")
plotter.plot_precision_comparison([r for r in fixed_results if r.dataset == 'synthetic' and r.shots == 1000])
print("Plotting quality_vs_shots...")
plotter.plot_quality_vs_shots([r for r in fixed_results if r.dataset == 'synthetic' and r.intensity_precision == 8])
print("Plotting category_analysis...")
plotter.plot_category_analysis([r for r in fixed_results if r.dataset == 'NEU-DET'])

print("Done plotting.")
