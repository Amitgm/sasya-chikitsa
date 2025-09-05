import chromadb
import chromadb.utils.embedding_functions as embedding_functions
from langchain_huggingface import HuggingFaceEmbeddings

# chroma_client = chromadb.HttpClient(host='0.0.0.0', port=8000)
chroma_client = chromadb.HttpClient(host="localhost", port=8000)

chroma_client.heartbeat()
print("ChromaDB client connected successfully.")

print("Available collections:", chroma_client.list_collections())

embedding = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-large-instruct",model_kwargs={"device": "mps"})
# embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
#     model_name="intfloat/multilingual-e5-large-instruct"
# )

# Expected Collections in the database:
# Paddy_Dhan
# Tomato
try:
    collection_name = "Tomato"
    collection = chroma_client.get_collection(name=collection_name, embedding_function=embedding)
    collection.count()
    print(f"Collection '{collection_name}' accessed successfully.")
    print(f"Number of items in the collection: {collection.count()}")

    # 4. Perform a query.
    results = collection.query(query_texts=["tomato diseases"], n_results=5)

    print("\nQuery Results:")
    print(results)

except ValueError as e:
    print(f"\nError getting collection: {e}")
    print(
        "Please make sure the collection name is correct and it exists in the database."
    )
    print("Check the 'Available collections' list printed above.")
