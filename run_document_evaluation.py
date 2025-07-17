import json
import os
from pathlib import Path
from evaluator import TranslationEvaluator
from scraper import Reader
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np


def evaluate_document_folder(folder_path: str, evaluator: TranslationEvaluator):
    folder_results = {}
    outputs_dir = Path(folder_path) / "outputs"
    inputs_dir = Path(folder_path) / "inputs"
    
    if not outputs_dir.exists():
        print(f"No outputs directory found in {folder_path}")
        return folder_results
    
    # Find all _translated.txt files
    translated_files = list(outputs_dir.glob("*_translated.txt"))
    
    for translated_file in translated_files:
        print(f"\nProcessing {translated_file.name}...")
        
        # Read the translated text
        with open(translated_file, 'r', encoding='utf-8') as f:
            translated_text = f.read()
        
        # Get the base name by removing _translated.txt
        base_name = translated_file.stem.replace('_translated', '')
        
        # Read the original Spanish text file
        original_file = outputs_dir / f"{base_name}_original.txt"
        if original_file.exists():
            with open(original_file, 'r', encoding='utf-8') as f:
                source_text = f.read()
        else:
            print(f"Could not find original file: {original_file.name}")
            continue
        
        # Find the corresponding English reference PDF
        # The pattern is usually: Spanish PDF has ESP, English PDF has ENG
        if 'ESP' in base_name:
            reference_name = base_name.replace('ESP', 'ENG')
        elif 'Spanish' in base_name:
            reference_name = base_name.replace('Spanish', '').replace('  ', ' ').strip()
        else:
            reference_name = base_name
        
        # Try to find the English PDF
        reference_file = None
        for pdf_file in inputs_dir.glob("*.pdf"):
            if 'ENG' in pdf_file.stem or ('Spanish' not in pdf_file.stem and 'ESP' not in pdf_file.stem):
                if reference_name in pdf_file.stem or pdf_file.stem in reference_name:
                    reference_file = pdf_file
                    break
        
        if not reference_file:
            # Try a more flexible search
            english_pdfs = [f for f in inputs_dir.glob("*.pdf") if 'ENG' in f.stem or ('Spanish' not in f.stem and 'ESP' not in f.stem)]
            if english_pdfs:
                reference_file = english_pdfs[0]  # Take the first English PDF
        
        if not reference_file:
            print(f"Could not find English reference PDF for {translated_file.name}")
            continue
        
        print(f"Using reference: {reference_file.name}")
        
        try:
            # Read the reference PDF using Reader class
            reader = Reader(str(reference_file))
            reference_text = ' '.join(reader.text) if isinstance(reader.text, list) else reader.text
            
            # Evaluate at document level
            evaluation = evaluator.evaluate_all([source_text], [translated_text], [reference_text])
            
            folder_results[translated_file.name] = {
                "source_file": base_name,
                "reference_file": reference_file.name,
                "scores": evaluation
            }
            
        except Exception as e:
            print(f"Error evaluating {translated_file.name}: {str(e)}")
            continue
    
    return folder_results


def create_visualizations(all_results):
    """Create visualization plots for the evaluation results"""
    
    # Prepare data for visualization
    data = []
    for folder, folder_results in all_results.items():
        for file_name, result in folder_results.items():
            scores = result['scores']
            data.append({
                'Document': folder.replace('_pages', ' pages'),
                'BLEU': scores['bleu_score'],
                'BERT': scores['bert_similarity'] * 100,  # Convert to percentage
                'COMET': scores['comet_score'] * 100 if scores['comet_score'] else 0  # Convert to percentage
            })
    
    df = pd.DataFrame(data)
    
    # Set style
    sns.set_style("whitegrid")
    plt.rcParams['figure.figsize'] = (14, 10)
    
    # Create a figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Document-Level Translation Evaluation Results\n(Spanish to English)', fontsize=16, fontweight='bold')
    
    # 1. Bar plot comparing all metrics across documents
    ax1 = axes[0, 0]
    df_melted = df.melt(id_vars='Document', var_name='Metric', value_name='Score')
    sns.barplot(data=df_melted, x='Document', y='Score', hue='Metric', ax=ax1)
    ax1.set_title('Comparison of All Metrics Across Documents', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Score (%)', fontsize=10)
    ax1.set_xlabel('Document', fontsize=10)
    ax1.legend(title='Metric')
    
    # Add value labels on bars
    for container in ax1.containers:
        ax1.bar_label(container, fmt='%.1f', fontsize=8)
    
    # 2. Radar chart for each document
    ax2 = plt.subplot(2, 2, 2, projection='polar')
    
    # Prepare data for radar chart
    categories = ['BLEU', 'BERT', 'COMET']
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    angles += angles[:1]  # Complete the circle
    
    # Plot radar chart for each document
    for idx, row in df.iterrows():
        values = [row['BLEU'], row['BERT'], row['COMET']]
        values += values[:1]  # Complete the circle
        ax2.plot(angles, values, 'o-', linewidth=2, label=row['Document'])
        ax2.fill(angles, values, alpha=0.15)
    
    ax2.set_theta_offset(np.pi / 2)
    ax2.set_theta_direction(-1)
    ax2.set_xticks(angles[:-1])
    ax2.set_xticklabels(categories)
    ax2.set_ylim(0, 100)
    ax2.set_title('Metric Performance Radar Chart', fontsize=12, fontweight='bold', pad=20)
    ax2.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    ax2.grid(True)
    
    # 3. Heatmap of scores
    ax3 = axes[1, 0]
    heatmap_data = df.set_index('Document')[['BLEU', 'BERT', 'COMET']]
    sns.heatmap(heatmap_data, annot=True, fmt='.1f', cmap='YlOrRd', ax=ax3, cbar_kws={'label': 'Score (%)'})
    ax3.set_title('Heatmap of Evaluation Scores', fontsize=12, fontweight='bold')
    ax3.set_xlabel('')
    
    # 4. Line plot showing trend across document sizes
    ax4 = axes[1, 1]
    
    # Extract page numbers for ordering
    df['Pages'] = df['Document'].str.extract('(\d+)').astype(int)
    df_sorted = df.sort_values('Pages')
    
    ax4.plot(df_sorted['Pages'], df_sorted['BLEU'], 'o-', label='BLEU', linewidth=2, markersize=8)
    ax4.plot(df_sorted['Pages'], df_sorted['BERT'], 's-', label='BERT', linewidth=2, markersize=8)
    ax4.plot(df_sorted['Pages'], df_sorted['COMET'], '^-', label='COMET', linewidth=2, markersize=8)
    
    ax4.set_xlabel('Document Size (pages)', fontsize=10)
    ax4.set_ylabel('Score (%)', fontsize=10)
    ax4.set_title('Score Trends by Document Size', fontsize=12, fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # Add value labels
    for metric, marker in [('BLEU', 'o'), ('BERT', 's'), ('COMET', '^')]:
        values = df_sorted[metric].values
        pages = df_sorted['Pages'].values
        for x, y in zip(pages, values):
            ax4.annotate(f'{y:.1f}', (x, y), textcoords="offset points", xytext=(0,5), ha='center', fontsize=8)
    
    plt.tight_layout()
    plt.savefig('translation_evaluation_visualization.png', dpi=300, bbox_inches='tight')
    print("\nVisualization saved to: translation_evaluation_visualization.png")
    
    plt.show()


def main():
    evaluator = TranslationEvaluator()
    
    base_path = "/Users/owner/Desktop/Gemini POC/PoCs/documents"
    folders = ["8_pages", "10_pages", "16_pages", "26_pages"]
    
    all_results = {}
    
    for folder in folders:
        folder_path = os.path.join(base_path, folder)
        print(f"\n{'='*60}")
        print(f"Evaluating {folder}")
        print(f"{'='*60}")
        
        results = evaluate_document_folder(folder_path, evaluator)
        all_results[folder] = results
    
    output_file = "document_evaluation_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n\nDetailed results saved to: {output_file}")
    
    summary_file = "document_evaluation_summary.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("Document-Level Translation Evaluation Summary\n")
        f.write("=" * 60 + "\n")
        f.write("All translations are Spanish to English\n")
        f.write("=" * 60 + "\n\n")
        
        for folder, folder_results in all_results.items():
            f.write(f"\n{folder.upper()}\n")
            f.write("-" * 40 + "\n")
            
            if not folder_results:
                f.write("No results for this folder\n")
                continue
            
            for file_name, result in folder_results.items():
                f.write(f"\nTranslated file: {file_name}\n")
                f.write(f"Source document: {result['source_file']}\n")
                f.write(f"Reference (English PDF): {result['reference_file']}\n")
                
                scores = result['scores']
                f.write(f"BLEU Score: {scores['bleu_score']:.2f}\n")
                f.write(f"BERT Similarity: {scores['bert_similarity']:.4f}\n")
                if scores['comet_score'] is not None:
                    f.write(f"COMET Score: {scores['comet_score']:.4f}\n")
                else:
                    f.write("COMET Score: N/A\n")
    
    print(f"Summary saved to: {summary_file}")
    
    # Create visualizations
    print("\nCreating visualizations...")
    create_visualizations(all_results)
    
    print("\nEvaluation complete!")


if __name__ == "__main__":
    main()