import typer
from pathlib import Path
import srsly
from inspect_ai.dataset import Sample, json_dataset
from inspect_ai.dataset import FieldSpec, json_dataset
import re
import sys
from functools import partial
from pathlib import Path
from pprint import pprint
from typing import Any, Literal
import os
import random
from anthropic import Anthropic
from dotenv import load_dotenv
from inspect_ai import Task, eval, task
from inspect_ai.dataset import Dataset, Sample, example_dataset, hf_dataset, json_dataset
from inspect_ai.model import ChatMessageSystem, ChatMessageUser, get_model
from inspect_ai.scorer import Score, Scorer, Target, answer, match, model_graded_fact, scorer
from inspect_ai.solver import (
    Choices,
    Generate,
    Solver,
    TaskState,
    chain,
    chain_of_thought,
    generate,
    self_critique,
    solver,
)
from pydantic import BaseModel
from inspect_ai import Task, task
from inspect_ai.model import GenerateConfig, ResponseSchema
from inspect_ai.solver import generate
from inspect_ai.util import json_schema
from pydantic import ValidationError
import re
from openai import OpenAI


@scorer(metrics=[])
def emotion_scorer_per_turn(template: str, model: str) -> Scorer:
    grading_config = GenerateConfig()
    grader_model = get_model(model=model, config=grading_config)

    class EmotionAnswer(BaseModel):
        evidence: str
        reasoning: str
        rating: int

    async def score(state: TaskState, _target: Target) -> Score:
        # Ratings go in value (flat dict of scalars for inspect metrics)
        ratings = {}
        # Full details go in metadata (nested dicts are fine here)
        details = {}

        turn_idx = 0
        for msg in state.messages:
            if msg.role == "assistant":
                turn_key = f"turn_{turn_idx}"
                scoring_prompt = template.format(output=msg.text)
                result = await grader_model.generate(scoring_prompt)

                try:
                    json_scrape = re.search(r'\{.*\}', result.completion, re.S).group(0)
                    emotion = EmotionAnswer.model_validate_json(json_scrape)

                    ratings[turn_key] = emotion.rating
                    details[turn_key] = {
                        "rating": emotion.rating,
                        "evidence": emotion.evidence,
                        "reasoning": emotion.reasoning,
                    }
                except (ValidationError, AttributeError) as ex:
                    ratings[turn_key] = None
                    details[turn_key] = {
                        "rating": None,
                        "evidence": None,
                        "reasoning": f"parse error: {ex}",
                    }

                turn_idx += 1

        return Score(
            value=ratings,
            metadata=details,
            explanation=f"Scored {turn_idx} assistant turns",
        )

    return score


@scorer(metrics=[])
def emotion_scorer(template, model) -> Scorer:
    grading_config = GenerateConfig()

    class EmotionAnswer(BaseModel):
        evidence: str
        reasoning: str
        rating: int
    grader_model = get_model(
        model=model,
        config=grading_config
    )
    async def score(state: TaskState, _target: Target) -> Score:
        # Scores the output in some wya
        scoring_prompt = template.format(output=state.output.completion)
        result = await grader_model.generate(scoring_prompt)
        try:
            json_scrape = re.search(r'\{.*\}', result.completion, re.S).group(0)
            emotion = EmotionAnswer.model_validate_json(json_scrape)
            return Score(value=emotion.rating, answer=emotion.evidence, explanation=emotion.reasoning)
        except ValidationError as ex:
            return Score(
                value={"rating": None},
                answer=result.completion,
                explanation=f"error parsing {ex}"
                
            )
    return score

@solver
def rejection(rejections: list) -> Solver:
    """
    Returns a solve function which adds a user message at the end of the state.messages list with
    a random rejection.

    Args:
        rejections: A list of rejections

    Returns:
        solve : A solve function which adds a user message with a randomly selected rejection
    """

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        
        rejection_string = random.choice(rejections)
        state.messages.append(ChatMessageUser(content=rejection_string))
        return state
    return solve


def build_rejection_solver(rejections: list, depth: int = 2) -> Solver:
    """Build a solver with `depth` rejection-generate cycles.
    
    Total assistant turns = depth + 1
    (initial generate, then `depth` rounds of reject + generate)
    """
    steps = [generate()]
    for _ in range(depth):
        steps.append(rejection(rejections))
        steps.append(generate())
    return chain(*steps)




def main(
    judge_prompt: str = typer.Option("emotion_judge_prompt.txt", help="Path to the judge prompt template file"),
    questions: str = typer.Option("frac_puzzles.jsonl", help="Path to the questions JSONL file"),
    rejections: str = typer.Option("rejections.jsonl", help="Path to the rejections JSONL file"),
    depth: int = typer.Option(2, help="Number of rejection-generate cycles"),
    model_tested: str = typer.Option("openrouter/google/gemma-3-27b-it", help="Model to evaluate"),
    grader_model: str = typer.Option("anthropic/claude-sonnet-4-20250514", help="Model used for grading"),
    samples_tested: int = typer.Option(5, help="Number of samples to evaluate"),
    every_turn: bool = typer.Option(False, help="Score every assistant turn individually"),
):
    
    load_dotenv()
    rubric = Path(judge_prompt).read_text()
    rejection_list = list(srsly.read_jsonl(rejections))
    eval_dataset = json_dataset(
    questions,
    FieldSpec(
        input="prompt",
        metadata=["difficulty"]
    ),    
)
    grading_config = GenerateConfig()
    if every_turn == True:
        func = emotion_scorer_per_turn
    else:
        func = emotion_scorer
    @task
    def fraction() -> Task:
        return Task(
            dataset=eval_dataset,
            solver=build_rejection_solver(rejection_list, depth),
            scorer=func(rubric, model=grader_model),
        )
    log = eval(fraction(), model=model_tested, limit=samples_tested, log_dir=str("logs"))
    
if __name__ == "__main__":
    typer.run(main)