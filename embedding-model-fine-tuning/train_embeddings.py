import json                                           
from sentence_transformers import SentenceTransformer, InputExample, losses                                 
from torch.utils.data import DataLoader               
                                                        
print("Loading base model...")                        
model = SentenceTransformer('nomic-ai/nomic-embed-text-v1.5', trust_remote_code=True)                               
                                                    
print("Loading triplets...")                          
examples = []                                         
with open('/workspace/embedding_triplets.jsonl') as f:
    for line in f:                                    
        row = json.loads(line)                                                                    
        examples.append(InputExample(texts=[row['anchor'], row['positive']]))    

print(f"Loaded {len(examples)} training examples")    
                                                    
train_dataloader = DataLoader(examples, shuffle=True, batch_size=32)                                        
train_loss = losses.MultipleNegativesRankingLoss(model)            
                                                    
print("Starting training...")                         
model.fit(                                            
    train_objectives=[(train_dataloader, train_loss)],
    epochs=3,                                         
    warmup_steps=100,                                 
    output_path='/workspace/finance-embed-v1',        
    show_progress_bar=True                            
)                                                     
                                                    
print("Training complete!")                           
print("Model saved to /workspace/finance-embed-v1")   