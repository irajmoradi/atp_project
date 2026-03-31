#!/bin/bash
# Normal: 1 grader, 1 response, per-turn scoring
python eval.py \
  --judge-prompt emotion_judge_prompt.txt \
  --questions prompting_data/frac_puzzles.jsonl \
  --rejections rejections.jsonl \
  --depth 8 \
  --model-tested "openrouter/google/gemma-3-27b-it" \
  --grader-model "openrouter/google/gemma-3-27b-it" \
  --samples-tested 2 \
  --every-turn \
  --log-dir logs
