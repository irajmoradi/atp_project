#!/bin/bash
# Branching: 3 candidates per turn, single grader
python eval.py \
  --judge-prompt emotion_judge_prompt.txt \
  --questions prompting_data/frac_puzzles.jsonl \
  --rejections rejections.jsonl \
  --depth 8 \
  --model-tested "openrouter/google/gemma-3-27b-it" \
  --grader-model "openrouter/google/gemma-3-27b-it" \
  --num-responses 3 \
  --samples-tested 2 \
  --log-dir logs
