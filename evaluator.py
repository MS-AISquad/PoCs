import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import sacrebleu
from comet import download_model, load_from_checkpoint
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import torch
import numpy as np


class TranslationEvaluator:
    def __init__(self):
        self.bert_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        try:
            model_path = download_model("Unbabel/wmt22-comet-da")
            self.comet_model = load_from_checkpoint(model_path)
        except Exception as e:
            print(f"Warning: COMET model loading failed: {str(e)}")
            self.comet_model = None
    
    def calculate_bleu(self, predictions: List[str], references: List[str]) -> float:
        if not predictions or not references:
            return 0.0
        
        refs = [[ref] for ref in references]
        bleu = sacrebleu.corpus_bleu(predictions, refs)
        return bleu.score
    
    def calculate_comet(self, sources: List[str], predictions: List[str], references: List[str]) -> float:
        if not self.comet_model or not all([sources, predictions, references]):
            return -1.0
        
        data = []
        for src, mt, ref in zip(sources, predictions, references):
            data.append({"src": src, "mt": mt, "ref": ref})
        
        try:
            model_output = self.comet_model.predict(data, batch_size=8)
            return model_output.system_score
        except Exception as e:
            print(f"COMET evaluation error: {str(e)}")
            return -1.0
    
    def calculate_bert_similarity(self, predictions: List[str], references: List[str]) -> float:
        if not predictions or not references:
            return 0.0
        
        pred_embeddings = self.bert_model.encode(predictions)
        ref_embeddings = self.bert_model.encode(references)
        
        similarities = []
        for pred_emb, ref_emb in zip(pred_embeddings, ref_embeddings):
            cos_sim = np.dot(pred_emb, ref_emb) / (np.linalg.norm(pred_emb) * np.linalg.norm(ref_emb))
            similarities.append(cos_sim)
        
        return float(np.mean(similarities))
    
    def evaluate_all(self, sources: List[str], predictions: List[str], references: List[str]) -> Dict:
        results = {
            "bleu_score": self.calculate_bleu(predictions, references),
            "bert_similarity": self.calculate_bert_similarity(predictions, references)
        }
        
        comet_score = self.calculate_comet(sources, predictions, references)
        if comet_score != -1.0:
            results["comet_score"] = comet_score
        else:
            results["comet_score"] = None
        
        # Calculate sentence-level scores
        sentence_scores = []
        for i, (src, pred, ref) in enumerate(zip(sources, predictions, references)):
            sentence_bleu = sacrebleu.sentence_bleu(pred, [ref]).score
            
            pred_emb = self.bert_model.encode([pred])
            ref_emb = self.bert_model.encode([ref])
            sentence_bert = float(np.dot(pred_emb[0], ref_emb[0]) / (np.linalg.norm(pred_emb[0]) * np.linalg.norm(ref_emb[0])))
            
            sentence_comet = None
            if self.comet_model:
                try:
                    comet_data = [{"src": src, "mt": pred, "ref": ref}]
                    comet_output = self.comet_model.predict(comet_data, batch_size=1)
                    sentence_comet = comet_output.scores[0]
                except Exception:
                    sentence_comet = None
            
            sentence_scores.append({
                "bleu": sentence_bleu,
                "bert_similarity": sentence_bert,
                "comet": sentence_comet
            })
        
        results["sentence_scores"] = sentence_scores
        return results