#!/bin/bash
# Multi-grader: different models (gemma 27b x2, gemma 12b x3)
python eval.py \
  --judge-prompt emotion_judge_prompt.txt \
  --questions prompting_data/frac_puzzles.jsonl \
  --rejections rejections.jsonl \
  --depth 8 \
  --model-tested "openrouter/google/gemma-3-27b-it" \
  --grader-models "openrouter/x-ai/grok-4.1-fast:2,openrouter/google/gemma-2-9b-it:3" \
  --samples-tested 2 \
  --log-dir logs
