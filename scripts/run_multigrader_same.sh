#!/bin/bash
# Multi-grader: same model grading 3 times per turn
python eval.py \
  --judge-prompt emotion_judge_prompt.txt \
  --questions prompting_data/frac_puzzles.jsonl \
  --rejections rejections.jsonl \
  --depth 8 \
  --model-tested "openrouter/google/gemma-3-27b-it" \
  --grader-model "openrouter/google/gemma-3-27b-it" \
  --num-grades 3 \
  --samples-tested 2 \
  --log-dir logs
