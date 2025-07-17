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
    
    def calculate_bleu(self, prediction: str, reference: str) -> float:
        if not prediction or not reference:
            return 0.0
        
        bleu = sacrebleu.sentence_bleu(prediction, [reference])
        return bleu.score
    
    def calculate_comet(self, source: str, prediction: str, reference: str) -> float:
        if not self.comet_model or not all([source, prediction, reference]):
            return -1.0
        
        data = [{"src": source, "mt": prediction, "ref": reference}]
        
        try:
            model_output = self.comet_model.predict(data, batch_size=1)
            return model_output.system_score
        except Exception as e:
            print(f"COMET evaluation error: {str(e)}")
            return -1.0
    
    def calculate_bert_similarity(self, prediction: str, reference: str) -> float:
        if not prediction or not reference:
            return 0.0
        
        pred_embedding = self.bert_model.encode([prediction])
        ref_embedding = self.bert_model.encode([reference])
        
        cos_sim = np.dot(pred_embedding[0], ref_embedding[0]) / (np.linalg.norm(pred_embedding[0]) * np.linalg.norm(ref_embedding[0]))
        
        return float(cos_sim)
    
    def evaluate_all(self, sources: List[str], predictions: List[str], references: List[str]) -> Dict:
        source_text = ' '.join(sources) if isinstance(sources, list) else str(sources)
        prediction_text = ' '.join(predictions) if isinstance(predictions, list) else str(predictions)
        reference_text = ' '.join(references) if isinstance(references, list) else str(references)
        
        results = {
            "bleu_score": self.calculate_bleu(prediction_text, reference_text),
            "bert_similarity": self.calculate_bert_similarity(prediction_text, reference_text)
        }
        
        comet_score = self.calculate_comet(source_text, prediction_text, reference_text)
        if comet_score != -1.0:
            results["comet_score"] = comet_score
        else:
            results["comet_score"] = None
        
        return results