# Use vector database

We are using Chromadb as vector database. There are two different flavours of it:
* Chromadb with data preloaded
* Empty Chromadb where the user needs to mount the suitable data.

## How to run the vector database in the local 

* based on the chip arch pull one of the available image:
  * for macbook
  
  ```bash 
  podman pull quay.io/rajivranjan/chromadb-with-data-arm64:v1
  ```

  * for non-macbook
  ```bash
  podman pull quay.io/rajivranjan/chromadb-with-data-amd64:v1
  ```

* test the connectivity and data collection

```bash
podman run -p 8000:8000 quay.io/rajivranjan/chromadb-with-data-arm64:v1

python test_chromadb.py
```