# Notes

![Sasya Chikitsa Data Flow Diagram](./images/sasya-chikitsa-data-flow.png)

*Data flow architecture showing how the plant disease detection system processes images and provides AI-powered analysis*

## Commands to run the python file

```bash
# initialize the folder with uv
uv init

# change the version of python to 3.11 in .python-version and pyproject.toml

# create the virtual environment NOT ALL DEPENDENCIES ARE LISTED IN COMMAND BELOW.
uv fastapi typing asyncio uvicorn python-multipart

# activate the python env
source .venv/bin/activate

# run the code
# .venv/bin/python /Users/rajranja/Documents/github/cds-9-group-6/sasya-chikitsa/server/api/server.py
# python -m api.agent_api

cd sasya-chikitsa/engine
# reload if required
uvicorn api.agent_api:app --host 0.0.0.0 --port 8080 --reload 


podman run -it --rm -p 8080:8080 -e OLLAMA_HOST=http://192.168.0.110:11434 localhost/engine-arm64:v2

jq -n \
--arg msg "Please analyze this Apple leaf image" \
--arg sid "session-1" \
--arg img "$(cat resources/images_for_test/leaf_base64.txt)" \
--arg txt "Spots near edges" \
'{message:$msg, session_id:$sid, image_b64:$img, text:$txt}' \
| curl -sS -X POST http://127.0.0.1:8000/chat-stream \
-H "Content-Type: application/json" \
--data-binary @-


jq -n \
--arg msg "Please analyze this Apple leaf image" \
--arg sid "session-1" \
--arg img "$(cat resources/images_for_test/leaf_base64.txt)" \
--arg txt "Spots near edges" \
'{message:$msg, session_id:$sid, image_b64:$img, text:$txt}' \
| curl -sS -X POST http://engine-sasya-chikitsa.apps.cluster-mx6z7.mx6z7.sandbox5315.opentlc.com/chat-stream \
-H "Content-Type: application/json" \
--data-binary @-




# to create the requirement file automatically from 

uv pip compile pyproject.toml -o requirements.txt

❯ uv tree
```


```bash
#start the llama 3.1 8b model container


# start the agentic api
podman run -it --rm -p 8080:8080 -e OLLAMA_HOST=http://192.168.0.110:11434 localhost/engine-arm64:v2

```


```bash
# install mlflow in your local setup
uv add mlflow
# or
pip install mlflow

# check pyproject.toml file for "mlflow>=3.3.2",
cat pyproject.toml G "mlflow"                         




```
