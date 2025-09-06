import pandas as pd
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.chat_models import ChatOllama
from fastapi import FastAPI
from pydantic import BaseModel
# import uvicorn
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ollama_rag:
    # Creating the Prompt Template

    prompt_template = """
        You are an agricultural assistant specialized in answering questions about plant diseases.  
        Your task is to provide answers strictly based on the provided context when possible.  

        Each document contains the following fields:  
        - DistrictName  
        - StateName  
        - Season_English  
        - Month  
        - Disease  
        - QueryText  
        - KccAns (this is the official response section from source documents)

        Guidelines for answering:
        1. If a relevant answer is available in KccAns, use that with minimal changes.
        2. Use DistrictName, StateName, Season_English, Month, and Disease only to help interpret the question and select the correct KccAns, but **do not include these details in the final answer unless the question explicitly asks for them**.  
        3. If the answer is not available in the context, then rely on your own agricultural knowledge to provide the best possible answer.  
        4. Do not invent or assume information when KccAns is present; only fall back to your own knowledge when the context has no suitable answer.  

        CONTEXT:
        {context}

        QUESTION:
        {question}

        OUTPUT:
        """

    def __init__(self, llm_name,temperature=0.1):
        logger.debug("Initializing ollama_rag class.")
        ollama_host = os.getenv("OLLAMA_HOST")
        logger.debug(f"OLLAMA_HOST={ollama_host}")

        if ollama_host:
            self.llm = ChatOllama(
                model=os.getenv("OLLAMA_MODEL", llm_name),
                temperature=temperature,
                base_url=ollama_host,
            )
            logger.info(f"Using Ollama model: {self.llm}")
        else:
            logger.info("OLLAMA_HOST not set.")
            raise RuntimeError(
                "No chat model configured. Set OLLAMA_HOST (and optionally OLLAMA_MODEL) or run Ollama and set OLLAMA_MODEL."
            )
        # self.llm = ChatOllama(
        #     temperature=1,
        #     # model_name="llama-3.1-8b",
        #     model_name=llm_name,
        #     max_tokens=600,
        #     top_p=0.90,
        #     #     frequency_penalty=1,
        #     #     presence_penalty=1,
        # )

        self.PROMPT = PromptTemplate(
            template=self.prompt_template, input_variables=["context", "question"]
        )

        self.chain_type_kwargs = {"prompt": self.PROMPT}

    def call_embeddings(self, embedding_model, collection_name):
        embedding = HuggingFaceEmbeddings(
            # model_name="intfloat/multilingual-e5-large-instruct",
            # model_kwargs={"device": "cuda"},
            model_name=embedding_model
        )

        self.chroma_db = Chroma(
            persist_directory="./chroma_capstone_db_new",
            embedding_function=embedding,
            # collection_name="Tomato"  # Specify which collection to load
            collection_name=collection_name,
        )

    def call_retriever(self):
        # creating the retriever

        chroma_retriever = self.chroma_db.as_retriever(
            search_type="mmr", search_kwargs={"k": 6, "fetch_k": 12}
        )

        # chroma_retriever.get_relevant_documents(question)

        # calling the retriever
        self.h_retrieval_QA1 = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=chroma_retriever,
            input_key="query",
            return_source_documents=True,
            chain_type_kwargs=self.chain_type_kwargs,
        )

    def run_query(self, query_request):
        answer = self.h_retrieval_QA1.invoke({"query": query_request})["result"]

        return answer


ollama_rag_object = ollama_rag(llm_name="llama-3.1-8b",temperature=1)

ollama_rag_object.call_embeddings(
    embedding_model="intfloat/multilingual-e5-large-instruct", collection_name="Tomato"
)

ollama_rag_object.call_retriever()

print(
    "common prescriptions for Tomatoes",
    ollama_rag_object.run_query(
        query_request="give me some common prescriptions for Tomatoes"
    ),
)


# @app.post("/ask")
# def run_query(request:Queryrequest):

#     answer = h_retrieval_QA1.invoke({"query": request.query})["result"]

#     return answer

# if __name__ == "__main__":

#     uvicorn.run("rag_with_ollama:app", host="0.0.0.0", port=5050, reload=True)
