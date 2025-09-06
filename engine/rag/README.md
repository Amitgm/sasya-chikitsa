# Retrieval-Augmented Generation (RAG)

This repository contains notebooks for creating embeddings, building a vector database, and running RAG (Retrieval-Augmented Generation) using both **Groq API** and **Hugging Face**.  

---

## 📂 Files in this Repository  

### 1. `Embedding_creation.ipynb`  
- Handles preprocessing of cleaned data.  
- Creates embeddings.  
- Inserts chunks into the vector database for retrieval.  

---

### 2. `Rag_with_groq.ipynb`  
- Runs the RAG pipeline using the **Groq API**.  
- Requires a **Groq API key**:  
  - You can create one by signing up at [Groq](https://groq.com).  
  - An existing API key is already placed in the **Amit** folder of the shared drive inside the `.env` file.  
- Requires the **`chroma_capstone_db_new`** vector database.  
- ✅ To run this notebook:  
  1. Place the `.env` file in the same folder.  
  2. Ensure the vector database is available.  
  3. Execute the notebook cells.  

---

### 3. `Rag_huggingface.ipynb`  
- Similar to `Rag_with_groq.ipynb`.  
- Does **not** require a Groq API key.  
- Simply run the notebook to start the RAG pipeline.  

### 4. Running with Ollama

- There are two files that have been created for running ollama with RAG : rag_with_ollama_fastapi.py and rag_with_ollama.py
- There are two files that are required which supports the running of ollama RAG program files: The requirements.txt and      chroma_capstone_db_new.
- Create a folder in your local desktop and place the four files under your folder. 
- Create a virtual environment using a python version 3.10 or greater.
- once virtual environment is created, cd into your virtual environment file/scripts and activate your virtual environment
- After activation, cd.. back into your local parent folder and run the command in your command prompt pip install -r requirements.txt
- Once all the packages are installed, you can now run both rag_with_ollama.py, rag_with_ollama_fastapi.py

---

## ⚙️ Requirements  
- Python 3.10+  
- Install dependencies:  
  ```bash
  pip install -r requirements.txt




## <TODO> How to call the rag independently when hosted on OpenShift


## <TODO> How to call the rag independently when hosted on local machine

## <TODO> How to setup the local environment for development

