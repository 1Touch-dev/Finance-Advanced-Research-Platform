from sentence_transformers import SentenceTransformer, util                                                 
                                                        
model = SentenceTransformer('/workspace/finance-embed-v1', trust_remote_code=True)    
                                                        
queries = ["Apple revenue growth Q3"]                 
docs = [                                              
      "AAPL reported $89B revenue in Q3 2024",          
      "Microsoft reported $56B revenue in Q3 2024",     
      "The weather is nice today"                       
  ]                                                     
                                                        
query_emb = model.encode(queries)                     
doc_emb = model.encode(docs)                          
                                                        
scores = util.cos_sim(query_emb, doc_emb)             
print("Query:", queries[0])                           
print("\nScores (higher = more relevant):")           
for doc, score in zip(docs, scores[0]):               
    print(f"  {score:.4f}: {doc}")     