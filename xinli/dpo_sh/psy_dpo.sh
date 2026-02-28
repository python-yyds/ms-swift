CUDA_VISIBLE_DEVICES=0,1,5,6 NPROC_PER_NODE=4 \
swift rlhf \
    --torch_dtype bfloat16 \
    --model /mnt/ai4s/models_storage/llm-models/Qwen3-8B \
    --model_type qwen3 \
    --template qwen3 \
    --dataset /mnt/ai4s/zhouhaojie/xinli/data_pre/high_score/rewrite_117/PsyDTCorpus_DPO.json \
    --dataset_num_proc 32 \
    --split_dataset_ratio 0.01 \
    --max_length 4096 \
    --warmup_ratio 0.05 \
    --per_device_train_batch_size 1 \
    --per_device_eval_batch_size 1 \
    --learning_rate 1e-6 \
    --num_train_epochs 2.0 \
    --gradient_accumulation_steps 32 \
    --eval_steps 100 \
    --save_steps 100 \
    --attn_impl flash_attention_2 \
    --neftune_noise_alpha 0 \
    --lora_rank 16 \
    --lora_alpha 32 \
    --beta 0.1 \
    --rpo_alpha 0 \
    --loss_scale ignore_empty_think \
    --report_to swanlab \
    --swanlab_token nD9wW6qFrHetvCQo0rfCm \
    --swanlab_exp_name psy_dpo \
    --use_liger_kernel True \
    --padding_free True \
    --add_version False \
    --output_dir /mnt/ai4s/zhouhaojie/liuzhanyang/21/nice/ms-swift/output/xinli/qwen38_dpo/psy_dpo \
    --logging_dir /mnt/ai4s/zhouhaojie/liuzhanyang/21/nice/ms-swift/output/xinli/qwen38_dpo/psy_dpo/ \
    --ignore_args_error True > /mnt/ai4s/zhouhaojie/liuzhanyang/21/nice/ms-swift/output/xinli/qwen38_dpo/psy_dpo/run.log 2>&1



CUDA_VISIBLE_DEVICES=0,1,5,6 NPROC_PER_NODE=4 \
swift rlhf \
    --torch_dtype bfloat16 \
    --model /mnt/ai4s/models_storage/llm-models/Qwen3-8B \
    --model_type qwen3 \
    --template qwen3 \
    --dataset /mnt/ai4s/zhouhaojie/xinli/data_pre/high_score/rewrite_117/PsyDTCorpus_DPO.json \
    --dataset_num_proc 32 \
    --split_dataset_ratio 0.01 \
    --max_length 4096 \
    --warmup_ratio 0.05 \
    --per_device_train_batch_size 1 \
    --per_device_eval_batch_size 1 \
    --learning_rate 1e-6 \
    --num_train_epochs 2.0 \
    --gradient_accumulation_steps 32 \
    --eval_steps 100 \
    --save_steps 100 \
    --attn_impl flash_attention_2 \
    --neftune_noise_alpha 0 \
    --lora_rank 16 \
    --lora_alpha 32 \
    --beta 0.1 \
    --rpo_alpha 1 \
    --loss_scale ignore_empty_think \
    --report_to swanlab \
    --swanlab_token nD9wW6qFrHetvCQo0rfCm \
    --swanlab_exp_name psy_dpo_rpo \
    --use_liger_kernel True \
    --padding_free True \
    --add_version False \
    --output_dir /mnt/ai4s/zhouhaojie/liuzhanyang/21/nice/ms-swift/output/xinli/qwen38_dpo/psy_dpo_rpo \
    --logging_dir /mnt/ai4s/zhouhaojie/liuzhanyang/21/nice/ms-swift/output/xinli/qwen38_dpo/psy_dpo_rpo/ \
    --ignore_args_error True > /mnt/ai4s/zhouhaojie/liuzhanyang/21/nice/ms-swift/output/xinli/qwen38_dpo/psy_dpo_rpo/run.log 2>&1




CUDA_VISIBLE_DEVICES=0,1,5,6 NPROC_PER_NODE=4 \
swift rlhf \
    --torch_dtype bfloat16 \
    --model /mnt/ai4s/models_storage/llm-models/Qwen3-4B-Instruct-2507 \
    --model_type qwen3 \
    --template qwen3 \
    --dataset /mnt/ai4s/zhouhaojie/xinli/data_pre/high_score/rewrite_117/PsyDTCorpus_DPO.json \
    --dataset_num_proc 32 \
    --split_dataset_ratio 0.01 \
    --max_length 4096 \
    --warmup_ratio 0.05 \
    --per_device_train_batch_size 1 \
    --per_device_eval_batch_size 1 \
    --learning_rate 1e-6 \
    --num_train_epochs 2.0 \
    --gradient_accumulation_steps 32 \
    --eval_steps 100 \
    --save_steps 100 \
    --attn_impl flash_attention_2 \
    --neftune_noise_alpha 0 \
    --lora_rank 16 \
    --lora_alpha 32 \
    --beta 0.1 \
    --rpo_alpha 0 \
    --loss_scale ignore_empty_think \
    --report_to swanlab \
    --swanlab_token nD9wW6qFrHetvCQo0rfCm \
    --swanlab_exp_name psy_dpo_4b \
    --use_liger_kernel True \
    --padding_free True \
    --add_version False \
    --output_dir /mnt/ai4s/zhouhaojie/liuzhanyang/21/nice/ms-swift/output/xinli/qwen34_dpo/psy_dpo \
    --logging_dir /mnt/ai4s/zhouhaojie/liuzhanyang/21/nice/ms-swift/output/xinli/qwen34_dpo/psy_dpo/ \
    --ignore_args_error True > /mnt/ai4s/zhouhaojie/liuzhanyang/21/nice/ms-swift/output/xinli/qwen34_dpo/psy_dpo/run.log 2>&1



CUDA_VISIBLE_DEVICES=0,1,5,6 NPROC_PER_NODE=4 \
swift rlhf \
    --torch_dtype bfloat16 \
    --model /mnt/ai4s/models_storage/llm-models/Qwen3-4B-Instruct-2507 \
    --model_type qwen3 \
    --template qwen3 \
    --dataset /mnt/ai4s/zhouhaojie/xinli/data_pre/high_score/rewrite_117/PsyDTCorpus_DPO.json \
    --dataset_num_proc 32 \
    --split_dataset_ratio 0.01 \
    --max_length 4096 \
    --warmup_ratio 0.05 \
    --per_device_train_batch_size 1 \
    --per_device_eval_batch_size 1 \
    --learning_rate 1e-6 \
    --num_train_epochs 2.0 \
    --gradient_accumulation_steps 32 \
    --eval_steps 100 \
    --save_steps 100 \
    --attn_impl flash_attention_2 \
    --neftune_noise_alpha 0 \
    --lora_rank 16 \
    --lora_alpha 32 \
    --beta 0.1 \
    --rpo_alpha 1 \
    --loss_scale ignore_empty_think \
    --report_to swanlab \
    --swanlab_token nD9wW6qFrHetvCQo0rfCm \
    --swanlab_exp_name psy_dpo_rpo_4b \
    --use_liger_kernel True \
    --padding_free True \
    --add_version False \
    --output_dir /mnt/ai4s/zhouhaojie/liuzhanyang/21/nice/ms-swift/output/xinli/qwen34_dpo/psy_dpo_rpo \
    --logging_dir /mnt/ai4s/zhouhaojie/liuzhanyang/21/nice/ms-swift/output/xinli/qwen34_dpo/psy_dpo_rpo/ \
    --ignore_args_error True > /mnt/ai4s/zhouhaojie/liuzhanyang/21/nice/ms-swift/output/xinli/qwen34_dpo/psy_dpo_rpo/run.log 2>&1