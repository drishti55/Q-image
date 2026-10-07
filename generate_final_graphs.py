import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Set beautiful style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_context("paper", font_scale=1.5)
sns.set_palette("deep")

# Load data
df = pd.read_csv('Final_Publication_Assets/Tables/all_results.csv')

# Clean inf values
df['psnr'] = df['psnr'].replace(float('inf'), 100.0)
df['psnr'] = df['psnr'].replace('inf', 100.0)

# 1. Resource vs Resolution
plt.figure(figsize=(10, 6))
df_res = df[(df['dataset'] == 'synthetic') & (df['shots'] == 1000)]
if not df_res.empty:
    # Sort by resolution size
    df_res['res_val'] = df_res['image_width']
    df_res = df_res.sort_values('res_val')
    
    plt.subplot(1, 2, 1)
    sns.lineplot(data=df_res, x='resolution', y='qubits', hue='representation', marker='o', linewidth=3, markersize=10)
    plt.title('Total Qubits vs Resolution')
    plt.ylabel('Qubit Count')
    plt.xlabel('Resolution')
    
    plt.subplot(1, 2, 2)
    sns.lineplot(data=df_res, x='resolution', y='circuit_depth', hue='representation', marker='s', linewidth=3, markersize=10)
    plt.title('Circuit Depth vs Resolution')
    plt.ylabel('Depth')
    plt.xlabel('Resolution')
    plt.yscale('log')
    
    plt.tight_layout()
    plt.savefig('Final_Publication_Assets/Visualizations/resource_vs_resolution_FINAL.png', dpi=300)
    plt.close()

# 2. Quality vs Shots
plt.figure(figsize=(12, 5))
df_shots = df[(df['dataset'] == 'synthetic') & (df['resolution'] == '4x4') & (df['intensity_precision'] == 8) & (df['shots'] >= 100)]
if not df_shots.empty:
    df_shots = df_shots.sort_values('shots')
    
    plt.subplot(1, 2, 1)
    sns.lineplot(data=df_shots, x='shots', y='mse', hue='representation', marker='o', linewidth=3, markersize=10)
    plt.title('Reconstruction Error (MSE) vs Shots')
    plt.ylabel('Mean Squared Error (Lower is Better)')
    plt.xlabel('Measurement Shots')
    plt.xscale('log')
    
    plt.subplot(1, 2, 2)
    sns.lineplot(data=df_shots, x='shots', y='psnr', hue='representation', marker='s', linewidth=3, markersize=10)
    plt.title('PSNR vs Shots (Capped at 100dB)')
    plt.ylabel('PSNR (dB) (Higher is Better)')
    plt.xlabel('Measurement Shots')
    plt.xscale('log')
    
    plt.tight_layout()
    plt.savefig('Final_Publication_Assets/Visualizations/quality_vs_shots_FINAL.png', dpi=300)
    plt.close()

# 3. Category Analysis (NEU-DET)
plt.figure(figsize=(12, 6))
df_neu = df[df['dataset'] == 'NEU-DET']
if not df_neu.empty:
    # Average across categories
    df_grouped = df_neu.groupby(['defect_category', 'representation'])['mse'].mean().reset_index()
    
    sns.barplot(data=df_grouped, x='defect_category', y='mse', hue='representation')
    plt.title('Average MSE by Defect Category (NEU-DET Database)')
    plt.ylabel('Mean Squared Error')
    plt.xlabel('Defect Category')
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig('Final_Publication_Assets/Visualizations/category_analysis_FINAL.png', dpi=300)
    plt.close()

print("NEW GRAPHS GENERATED SUCCESSFULLY!")
