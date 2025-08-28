Project Notebooks

This repository contains three Jupyter notebooks that demonstrate data preprocessing, embedding creation, and Retrieval-Augmented Generation (RAG) using Groq API and Hugging Face models.

📂 Files Overview
1. Embedding_creation.ipynb

Handles preprocessing of cleaned data.

Creates embeddings and inserts chunks into the Chroma vector database for later retrieval.

2. Rag_with_groq.ipynb

Runs RAG using the Groq API.

Requirements:

A Groq API key, which can be created by registering at groq.com
.

However, a pre-generated API key is already stored in the Amit folder of the shared drive inside the .env file.

The notebook also requires access to the chroma_capstone_db_new vector database.

✅ To run:

Place the .env file and chroma_capstone_db_new vector database in the same folder as the notebook.

Execute the notebook cells sequentially.
