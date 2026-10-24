"""AirLLM komplett offline ausführen.

Aufruf:
    .venv/bin/python run_offline.py <lokaler-modellordner> "Deine Frage"

Der Modellordner muss vorher (mit Internet) heruntergeladen worden sein, z. B.:
    .venv/bin/hf download Qwen/Qwen2.5-0.5B-Instruct --local-dir models/Qwen2.5-0.5B-Instruct
"""
import os
import sys

# Muss vor dem Import von transformers/airllm gesetzt werden.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

from airllm import AutoModel  # noqa: E402


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    model_dir, prompt = sys.argv[1], sys.argv[2]
    if not os.path.isdir(model_dir):
        sys.exit(f"Modellordner nicht gefunden: {model_dir}")

    model = AutoModel.from_pretrained(model_dir)
    tokens = model.tokenizer([prompt], return_tensors="pt", return_attention_mask=False,
                             truncation=True, max_length=512, padding=False)
    out = model.generate(tokens["input_ids"].to(model.device), max_new_tokens=64,
                         use_cache=True, return_dict_in_generate=True)
    print(model.tokenizer.decode(out.sequences[0], skip_special_tokens=True))


if __name__ == "__main__":
    main()
