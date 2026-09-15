import json

raw = """{
  "a": "line 1
line 2"
}"""
try:
    print(json.loads(raw, strict=False))
except Exception as e:
    print(e)
