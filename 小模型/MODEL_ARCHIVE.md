# Model Archive Record

## Qwen2.5-Coder-1.5B-Instruct HF Snapshot

Archived to N100:

`n100:~/yizijue-model-archive/Qwen2.5-Coder-1.5B-Instruct-hf`

Remote files:

- `config.json`
- `generation_config.json`
- `merges.txt`
- `model.safetensors`
- `tokenizer.json`
- `tokenizer_config.json`
- `vocab.json`

Model weight SHA256:

`c1b9b30e907950516ba3c646bdf570d8084c25a6410a0cdca80cf04b11bc13a8  model.safetensors`

Archive size on N100:

`2.9G`

Original local cache path before cleanup:

`/Users/aidi/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-1.5B-Instruct`

Restore command when training is needed:

```bash
mkdir -p ~/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-1.5B-Instruct/snapshots/2e1fd397ee46e1388853d2af2c993145b0f1098a
rsync -az n100:~/yizijue-model-archive/Qwen2.5-Coder-1.5B-Instruct-hf/ \
  ~/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-1.5B-Instruct/snapshots/2e1fd397ee46e1388853d2af2c993145b0f1098a/
```

Note: the restored directory will contain real files, not HuggingFace cache symlinks. It can still be passed directly as a local model path to training tools.
