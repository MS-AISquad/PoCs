import json
import sys
import re
import os
from pathlib import Path
from typing import List, Optional
from translator import GeminiTranslator
from evaluator import TranslationEvaluator


def split_sentences(text: str) -> List[str]:
    # split on ". " as long as the period is not part of an acronym (e.g. or S.B.)
    # or a one letter initial (John E. Smith)
    sentences = re.split(r'(?<=(?<!\w[ \.]\w)[.!?])\s+', text.strip())
    return [s for s in sentences if s]


def read_file(file_path: str) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        sys.exit(1)


def get_file_path(prompt: str, must_exist: bool = True) -> Optional[str]:
    while True:
        path = input(prompt).strip()
        if not path and not must_exist:
            return None
        if not path:
            print("Please enter a file path.")
            continue
        if must_exist and not os.path.exists(path):
            print(f"File not found: {path}")
            continue
        return path


def get_translation_direction() -> tuple:
    print("\nSelect translation direction:")
    print("1. Spanish to English (es-en)")
    print("2. English to Spanish (en-es)")
    
    while True:
        choice = input("\nEnter your choice (1 or 2): ").strip()
        if choice == '1':
            return 'es-en', 'Spanish', 'English'
        elif choice == '2':
            return 'en-es', 'English', 'Spanish'
        else:
            print("Invalid choice. Please enter 1 or 2.")


def main():
    print("=== Gemini Translation Tool ===\n")
    
    input_file = get_file_path("Enter the path to your input text file: ")
    
    direction, source_lang_full, target_lang_full = get_translation_direction()
    
    print("\nDo you have a reference translation file for evaluation?")
    has_reference = input("Enter 'y' for yes or 'n' for no: ").strip().lower() == 'y'
    
    reference_file = None
    if has_reference:
        reference_file = get_file_path("\nEnter the path to your reference translation file: ")
    
    output_name = input("\nEnter a name for your output files (without extension): ").strip()
    if not output_name:
        output_name = "results"
    
    print("\nTranslate sentence by sentence (one API call each)?")
    translate_by_sentence = input("Enter 'y' for yes or 'n' for no: ").strip().lower() == 'y'
    
    print(f"\nReading input file: {input_file}")
    source_text = read_file(input_file)
    source_sentences = split_sentences(source_text)
    print(f"Found {len(source_sentences)} sentences to translate")
    
    reference_sentences = None
    if reference_file:
        print(f"Reading reference file: {reference_file}")
        reference_text = read_file(reference_file)
        reference_sentences = split_sentences(reference_text)
        print(f"Found {len(reference_sentences)} reference sentences")
    
    try:
        translator = GeminiTranslator()
        print(f"\nTranslating from {source_lang_full} to {target_lang_full}...")
        if translate_by_sentence:
            translations = translator.translate_batch(source_sentences, source_lang_full, target_lang_full)
        else:
            translations = translator.translate_text(source_text, source_lang_full, target_lang_full)
            translations = split_sentences(translations)
        print(f"Translation complete!")
        
        results = {
            "translation_direction": direction,
            "model": "gemini-2.5-flash",
            "source_sentences": source_sentences,
            "translations": translations
        }
        
        original_file = f"{output_name}_original.txt"
        with open(original_file, 'w', encoding='utf-8') as f:
            f.write(source_text)
        print(f"\nOriginal text saved to: {original_file}")
        
        translated_file = f"{output_name}_translated.txt"
        with open(translated_file, 'w', encoding='utf-8') as f:
            f.write(' '.join(translations))
        print(f"Translated text saved to: {translated_file}")
        
        if reference_sentences:
            print("\nEvaluating translations...")
            evaluator = TranslationEvaluator()
            evaluation = evaluator.evaluate_all(source_sentences, translations, reference_sentences)
            results["evaluation"] = evaluation
            
            eval_file = f"{output_name}_evaluation.txt"
            with open(eval_file, 'w', encoding='utf-8') as f:
                f.write("Translation Evaluation Results\n")
                f.write("=============================\n\n")
                f.write(f"Translation Direction: {direction}\n")
                f.write(f"Model: gemini-2.5-flash\n")
                f.write(f"Number of sentences: {len(source_sentences)}\n\n")
                f.write("Evaluation Metrics:\n")
                f.write(f"BLEU Score: {evaluation['bleu_score']:.2f}\n")
                f.write(f"BERT Similarity: {evaluation['bert_similarity']:.4f}\n")
                if evaluation['comet_score'] is not None:
                    f.write(f"COMET Score: {evaluation['comet_score']:.4f}\n")
                
                f.write("\n\nSentence-level Scores:\n")
                for i, score in enumerate(evaluation['sentence_scores']):
                    f.write(f"\nSentence {i+1}:\n")
                    f.write(f"  BLEU: {score['bleu']:.2f}\n")
                    f.write(f"  BERT: {score['bert_similarity']:.4f}\n")
                    if score['comet'] is not None:
                        f.write(f"  COMET: {score['comet']:.4f}\n")
            
            print(f"Evaluation results saved to: {eval_file}")
        
        json_file = f"{output_name}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\nComplete results saved to: {json_file}")
        
        print("\nTranslation process completed successfully!")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
    