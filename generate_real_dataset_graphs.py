import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Set beautiful style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_context("paper", font_scale=1.5)
sns.set_palette("deep")

# Load data
df = pd.read_csv('Final_Publication_Assets/Tables/all_results.csv')

# Filter exclusively for real NEU-DET dataset
df_neu = df[df['dataset'] == 'NEU-DET'].copy()

if not df_neu.empty:
    # 1. Real-World Execution Time Breakdown (Encoding vs Simulation)
    plt.figure(figsize=(12, 6))
    time_cols = ['encoding_time', 'simulation_time', 'reconstruction_time']
    
    # Melt the dataframe for seaborn grouped bar plot
    df_time = df_neu.melt(id_vars=['representation'], value_vars=time_cols, 
                          var_name='Phase', value_name='Time (s)')
    
    # Clean phase names
    df_time['Phase'] = df_time['Phase'].str.replace('_time', '').str.capitalize()
    
    sns.barplot(data=df_time, x='Phase', y='Time (s)', hue='representation', errorbar='sd', capsize=0.1)
    plt.title('Average Classical Processing Overhead (NEU-DET Dataset)')
    plt.ylabel('Time (seconds) per Image')
    plt.xlabel('Processing Phase')
    plt.yscale('log') # Log scale because simulation might be much longer than others
    plt.tight_layout()
    plt.savefig('Final_Publication_Assets/Visualizations/neudet_time_breakdown_FINAL.png', dpi=300)
    plt.close()

    # 2. Total Time Variance (Boxplot) across 1,440 images
    plt.figure(figsize=(8, 6))
    sns.boxplot(data=df_neu, x='representation', y='total_time', hue='representation')
    plt.title('Total Execution Time Variance (1,440 Real Images)')
    plt.ylabel('Total Time (s)')
    plt.xlabel('Quantum Representation')
    plt.tight_layout()
    plt.savefig('Final_Publication_Assets/Visualizations/neudet_total_time_variance_FINAL.png', dpi=300)
    plt.close()

    # 3. Quantum Resources strictly on NEU-DET (Bar chart)
    # Since all NEU-DET images were 4x4, 8-bit, the gates/depth are constant, so a simple bar chart is perfect.
    df_resources = df_neu[['representation', 'qubits', 'gate_count', 'circuit_depth']].drop_duplicates()
    df_resources_melt = df_resources.melt(id_vars=['representation'], var_name='Metric', value_name='Count')
    
    df_resources_melt['Metric'] = df_resources_melt['Metric'].str.replace('_', ' ').str.title()
    
    plt.figure(figsize=(10, 6))
    sns.barplot(data=df_resources_melt, x='Metric', y='Count', hue='representation')
    plt.title('Quantum Circuit Resources Required for NEU-DET Dataset')
    plt.ylabel('Count (Log Scale)')
    plt.xlabel('Resource Metric')
    plt.yscale('log')
        
    plt.tight_layout()
    plt.savefig('Final_Publication_Assets/Visualizations/neudet_resources_FINAL.png', dpi=300)
    plt.close()

    print("Generated real dataset specific plots!")
else:
    print("No NEU-DET data found.")
