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