Command for lambda zip:

rm -rf package lambda.zip

/opt/homebrew/bin/python3.11 -m pip install \
  --platform manylinux2014_aarch64 \
  --target package \
  --implementation cp \
  --python-version 3.11 \
  --only-binary=:all: \
  --no-compile \
  --upgrade \
  -r requirements.txt

cp -r *.py routes package/

cd package

zip -r ../lambda.zip .


Ollama version: 
qwen3:14b

Local Ollama config:

When running FastAPI directly on the Mac, the backend defaults to:

OPENAI_MODEL=qwen3:14b
OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://127.0.0.1:11434/v1

When running FastAPI through Docker Compose, use the Compose default:

OPENAI_BASE_URL=http://host.docker.internal:11434/v1
