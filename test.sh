#!/bin/bash
python eval.py \
  --judge-prompt emotion_judge_prompt.txt \
  --questions frac_puzzles.jsonl \
  --rejections rejections.jsonl \
  --depth 2 \
  --model-tested "openrouter/google/gemma-3-27b-it" \
  --grader-model "anthropic/claude-sonnet-4-20250514" \
  --samples-tested 5 \
  --every-turn
