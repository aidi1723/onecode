# Training Asset Boundary

OneCode is the deterministic rule engine and execution gateway.

Do not store YiZiJue-LM distillation data, cleaned training data, model checkpoints, LoRA adapters, or GGUF files in this repository.

The YiZiJue-LM small-model workspace is:

`<local-user-path>`

Use that workspace for:

- distillation raw data
- cleaned datasets
- Qwen SFT messages files
- training reports
- LoRA adapters
- GGUF or other deployment artifacts

OneCode may expose rule-engine APIs used by the small-model pipeline, but generated training assets must remain outside the OneCode project tree.
