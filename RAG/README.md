The following folder contains 3 files

1) Embedding_creation.ipynb
2) Rag_with_groq.ipynb
3) Rag_huggingface.ipynb

Embedding_Creation.ipynb: 
contains code for further data preprocessing of cleaned data, ready to be inserted  and chunk insertion into the vector db

Rag_with_groq.ipynb:

Runs the RAG using the Groq API. The Groq API key needs to be created by visiting groq.com and creating an account for the Groq API key. However, an already created  API key is already placed in the Amit folder of the shared drive in the .env file. The file also requires the chroma_capstone_db_new vector database to fetch relevant results from the queries from the database. 

Using the .env file and vector database, run the Rag_with_groq notebook in the same folder. 

Rag_huggingface.ipynb:

Similar to Rag_with_groq.ipynb, this does not require a grok api key. Just simply run this file





