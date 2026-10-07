import os
import sys
from pathlib import Path
import pandas as pd
from src.experiments.runner import ExperimentRunner
from config.settings import get_image_paths, DEFECT_CATEGORIES, PROJECT_ROOT, RESULTS_EXPERIMENTS_PATH

print("Starting full dataset evaluation...")

p = RESULTS_EXPERIMENTS_PATH / "all_results.csv"
evaluated = set()
if p.exists():
    df = pd.read_csv(p)
    for _, row in df.iterrows():
        evaluated.add((str(row["image_name"]), str(row["representation"])))

runner = ExperimentRunner()
total = 1440 * 2
done = len(evaluated)
print(f"Found {done} experiments completed. {total - done} remaining.")

for cls in DEFECT_CATEGORIES:
    images = get_image_paths(cls, max_images=None)
    for img_path in images:
        img_name = img_path.name
        
        for rep in ["FRQI", "NEQR"]:
            if (img_name, rep) in evaluated:
                continue
                
            try:
                image = runner.processor.load_image(img_path)
                result = runner.run_single_experiment(
                    image=image,
                    image_name=img_name,
                    size=(4, 4),
                    bits=8,
                    shots=1024,
                    representation=rep,
                    category=cls,
                    dataset="NEU-DET",
                    use_statevector=False
                )
                
                existing = runner.results_manager.load_results_csv(p)
                all_res = existing + [result.to_dict()]
                runner.results_manager.save_results_csv(all_res, p)
                
                print(f"Completed {rep} for {img_name}")
            except Exception as e:
                print(f"Error on {img_name} {rep}: {e}")

print("All remaining images have been evaluated!")
