# Since `output/vx-xxx/checkpoint-xxx` is trained by swift and contains an `args.json` file,
# there is no need to explicitly set `--model`, `--system`, etc., as they will be automatically read.
swift export \
    --adapters output/xinli/qwen38_dpo/psy_sft/checkpoint-162 \
    --merge_lora true
