import typer
import asyncio
from pathlib import Path
import srsly
from inspect_ai.dataset import FieldSpec, json_dataset
import re
import random
from dotenv import load_dotenv
from inspect_ai import Task, eval, task
from inspect_ai.model import ChatMessageUser, ChatMessageAssistant, get_model
from inspect_ai.scorer import Score, Scorer, Target, scorer
from inspect_ai.solver import (
    Generate,
    Solver,
    TaskState,
    chain,
    generate,
    solver,
)
from inspect_ai.solver._fork import fork
from pydantic import BaseModel
from inspect_ai.model import GenerateConfig
from pydantic import ValidationError


# ── Scorers ──────────────────────────────────────────────────────────────────

@scorer(metrics=[])
def emotion_scorer(template, model) -> Scorer:
    """Score only the final assistant turn.

    Parses the grader's JSON response into an EmotionAnswer and returns
    a single scalar rating. Use this for the simplest single-turn eval.
    """
    grading_config = GenerateConfig()

    class EmotionAnswer(BaseModel):
        evidence: str
        reasoning: str
        rating: int

    grader_model = get_model(model=model, config=grading_config)

    async def score(state: TaskState, _target: Target) -> Score:
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


@scorer(metrics=[])
def emotion_scorer_per_turn(template: str, model: str) -> Scorer:
    """Score every assistant turn independently.

    Iterates over all assistant messages in the conversation, grades each
    one, and returns a dict of {turn_0: rating, turn_1: rating, ...} in
    the Score value. Full evidence/reasoning goes into metadata.
    """
    grading_config = GenerateConfig()
    grader_model = get_model(model=model, config=grading_config)

    class EmotionAnswer(BaseModel):
        evidence: str
        reasoning: str
        rating: int

    async def score(state: TaskState, _target: Target) -> Score:
        ratings = {}
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
def multi_grader_emotion_scorer(template: str, graders: list[tuple[str, int]]) -> Scorer:
    """Score each assistant turn with multiple grader models.

    Each turn is graded by every (model, count) pair in `graders`.
    All grades run concurrently via asyncio.gather, then averaged.
    Returns per-turn averages in Score value, individual grader
    results in metadata.

    Args:
        template: Scoring prompt template with {output} placeholder.
        graders: List of (model_name, count) tuples, e.g.
                 [("anthropic/claude-sonnet-4-20250514", 2),
                  ("openrouter/google/gemma-3-27b-it", 5)]
    """
    models = [(get_model(name), count) for name, count in graders]

    class EmotionAnswer(BaseModel):
        evidence: str
        reasoning: str
        rating: int

    async def grade_once(grader, prompt):
        """Run a single grading call and parse the JSON response."""
        result = await grader.generate(prompt)
        try:
            raw = re.search(r'\{.*\}', result.completion, re.S).group(0)
            emotion = EmotionAnswer.model_validate_json(raw)
            return {"rating": emotion.rating, "evidence": emotion.evidence, "reasoning": emotion.reasoning}
        except (ValidationError, AttributeError) as ex:
            return {"rating": None, "evidence": None, "reasoning": f"parse error: {ex}"}

    async def score(state: TaskState, _target: Target) -> Score:
        ratings = {}
        details = {}
        turn_idx = 0

        for msg in state.messages:
            if msg.role != "assistant":
                continue

            prompt = template.format(output=msg.text)
            tasks = [grade_once(m, prompt) for m, count in models for _ in range(count)]
            results = await asyncio.gather(*tasks)

            turn_key = f"turn_{turn_idx}"
            valid = [r["rating"] for r in results if r["rating"] is not None]
            ratings[turn_key] = sum(valid) / len(valid) if valid else None
            details[turn_key] = {"grader_results": results, "average": ratings[turn_key]}
            turn_idx += 1

        return Score(value=ratings, metadata=details, explanation=f"Scored {turn_idx} turns with {len(tasks)} graders each")

    return score


@scorer(metrics=[])
def branch_emotion_scorer(template: str, model: str) -> Scorer:
    """Score every candidate across every turn from branching generation.

    Reads candidates from metadata['branches'] (written by branching_generate),
    grades all of them in parallel, and reports the picked candidate's rating
    in Score value while storing all candidate scores in metadata.

    Args:
        template: Scoring prompt template with {output} placeholder.
        model: Grader model name.
    """
    grader = get_model(model)

    class EmotionAnswer(BaseModel):
        evidence: str
        reasoning: str
        rating: int

    async def grade(text):
        """Grade a single candidate text."""
        result = await grader.generate(template.format(output=text))
        try:
            raw = re.search(r'\{.*\}', result.completion, re.S).group(0)
            e = EmotionAnswer.model_validate_json(raw)
            return {"rating": e.rating, "evidence": e.evidence, "reasoning": e.reasoning}
        except (ValidationError, AttributeError) as ex:
            return {"rating": None, "evidence": None, "reasoning": f"parse error: {ex}"}

    async def score(state: TaskState, _target: Target) -> Score:
        branches = state.metadata.get("branches", {})
        ratings = {}
        details = {}

        for turn_key, branch in branches.items():
            graded = await asyncio.gather(*[grade(c) for c in branch["candidates"]])
            picked = branch["picked"]

            ratings[turn_key] = graded[picked]["rating"]
            details[turn_key] = {
                "picked": picked,
                "candidates": [
                    {"text": text, **scores}
                    for text, scores in zip(branch["candidates"], graded)
                ],
            }

        return Score(value=ratings, metadata=details, explanation=f"Scored {len(branches)} turns, each with {len(branch['candidates'])} candidates")

    return score


# ── Solvers ──────────────────────────────────────────────────────────────────

@solver
def rejection(rejections: list) -> Solver:
    """Append a random rejection as a user message.

    Randomly picks one rejection from the list and appends it to
    state.messages as a ChatMessageUser, simulating a user pushing
    back on the model's response.

    Args:
        rejections: List of rejection strings to sample from.
    """
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        rejection_string = random.choice(rejections)
        state.messages.append(ChatMessageUser(content=rejection_string))
        return state
    return solve


def build_rejection_solver(rejections: list, depth: int = 2) -> Solver:
    """Build a solver with `depth` rejection-generate cycles.

    Produces depth+1 total assistant turns: one initial generate,
    then `depth` rounds of (reject -> generate).

    Args:
        rejections: List of rejection strings.
        depth: Number of rejection-generate cycles after the first turn.
    """
    steps = [generate()]
    for _ in range(depth):
        steps.append(rejection(rejections))
        steps.append(generate())
    return chain(*steps)


@solver
def branching_generate(n: int = 3) -> Solver:
    """Generate n candidate responses in parallel using inspect's fork().

    Drop-in replacement for generate(). Forks the conversation n ways,
    picks the first candidate to continue, and stores all candidates
    in metadata['branches'][turn_key] for later scoring.

    Args:
        n: Number of parallel candidate generations per turn.
    """
    async def solve(state: TaskState, _generate: Generate) -> TaskState:
        if "branches" not in state.metadata:
            state.metadata["branches"] = {}

        turn_idx = len(state.metadata["branches"])
        forked_states = await fork(state, [generate() for _ in range(n)])
        candidates = [s.output.completion for s in forked_states]

        picked = 0
        state.metadata["branches"][f"turn_{turn_idx}"] = {
            "candidates": candidates,
            "picked": picked,
        }
        state.messages.append(ChatMessageAssistant(content=candidates[picked]))
        state.output = forked_states[picked].output
        return state

    return solve


def build_branching_solver(rejections: list, depth: int = 2, n: int = 3) -> Solver:
    """Build a solver with branching generation and rejection cycles.

    Same structure as build_rejection_solver, but each generate step
    produces n candidates instead of 1. All candidates are stored in
    metadata for the branch_emotion_scorer to grade.

    Args:
        rejections: List of rejection strings.
        depth: Number of rejection-generate cycles after the first turn.
        n: Number of candidates per generation step.
    """
    steps = [branching_generate(n)]
    for _ in range(depth):
        steps.append(rejection(rejections))
        steps.append(branching_generate(n))
    return chain(*steps)


# ── Helpers ──────────────────────────────────────────────────────────────────

def parse_grader_models(spec: str) -> list[tuple[str, int]]:
    """Parse a grader spec string into (model, count) tuples.

    Accepts comma-separated entries. Each entry is either 'model:count'
    or just 'model' (count defaults to 1). Splits on the last colon so
    model names containing slashes work fine.

    Examples:
        'anthropic/claude-sonnet-4-20250514:2,openrouter/google/gemma-3-27b-it:5'
        'anthropic/claude-sonnet-4-20250514'
    """
    pairs = []
    for part in spec.split(","):
        part = part.strip()
        if ":" in part:
            idx = part.rfind(":")
            model_name = part[:idx]
            count = int(part[idx + 1:])
        else:
            model_name = part
            count = 1
        pairs.append((model_name, count))
    return pairs


# ── CLI ──────────────────────────────────────────────────────────────────────

def main(
    judge_prompt: str = typer.Option("emotion_judge_prompt.txt", help="Path to the judge prompt template file"),
    questions: str = typer.Option("frac_puzzles.jsonl", help="Path to the questions JSONL file"),
    rejections: str = typer.Option("rejections.jsonl", help="Path to the rejections JSONL file"),
    depth: int = typer.Option(2, help="Number of rejection-generate cycles"),
    model_tested: str = typer.Option("openrouter/google/gemma-3-27b-it", help="Model to evaluate"),
    grader_model: str = typer.Option("anthropic/claude-sonnet-4-20250514", help="Model used for grading (simple mode)"),
    grader_models: str = typer.Option(None, help="Multi-grader spec: 'model:count,model:count'"),
    samples_tested: int = typer.Option(5, help="Number of samples to evaluate"),
    num_responses: int = typer.Option(1, help="Candidates per turn (>1 enables branching)"),
    num_grades: int = typer.Option(1, help="Number of grades per grader model"),
    every_turn: bool = typer.Option(False, help="Score every assistant turn individually"),
    log_dir: str = typer.Option("logs", help="Directory for eval logs"),
):
    """Run an emotion-elicitation eval with configurable solver and scorer.

    Simple mode (defaults):
        python eval.py --questions frac_puzzles.jsonl

    Per-turn scoring:
        python eval.py --every-turn

    Multi-grader (multiple models or repeated grades):
        python eval.py --grader-models 'anthropic/claude-sonnet-4-20250514:2,openrouter/google/gemma-3-27b-it:5'
        python eval.py --num-grades 3

    Branching (n candidates per turn):
        python eval.py --num-responses 3

    Wildchat:
        python eval.py --questions wildchat.jsonl --every-turn --depth 3
    """
    load_dotenv()

    # ── Validate mutually exclusive modes ──
    use_branching = num_responses > 1
    use_multi_grader = grader_models is not None or num_grades > 1
    if use_branching and use_multi_grader:
        typer.echo("Error: --num-responses and --grader-models/--num-grades are mutually exclusive.", err=True)
        raise typer.Exit(code=1)

    rubric = Path(judge_prompt).read_text()
    rejection_list = list(srsly.read_jsonl(rejections))
    eval_dataset = json_dataset(questions, FieldSpec(input="prompt"))

    # ── Resolve grader config for metadata ──
    if grader_models is not None:
        resolved_graders = parse_grader_models(grader_models)
    elif num_grades > 1:
        resolved_graders = [(grader_model, num_grades)]
    else:
        resolved_graders = [(grader_model, 1)]

    # ── Store CLI config for log reproducibility ──
    run_config = {
        "judge_prompt": judge_prompt,
        "questions": questions,
        "rejections": rejections,
        "depth": depth,
        "model_tested": model_tested,
        "graders": [{"model": m, "count": c} for m, c in resolved_graders],
        "samples_tested": samples_tested,
        "num_responses": num_responses,
        "every_turn": every_turn,
        "log_dir": log_dir,
        "mode": "branching" if use_branching else "multi_grader" if use_multi_grader else "simple",
    }

    # ── Pick solver ──
    if use_branching:
        task_solver = build_branching_solver(rejection_list, depth, n=num_responses)
    else:
        task_solver = build_rejection_solver(rejection_list, depth)

    # ── Pick scorer ──
    if use_branching:
        task_scorer = branch_emotion_scorer(rubric, model=grader_model)
    elif grader_models is not None:
        task_scorer = multi_grader_emotion_scorer(rubric, graders=resolved_graders)
    elif num_grades > 1:
        task_scorer = multi_grader_emotion_scorer(rubric, graders=resolved_graders)
    elif every_turn:
        task_scorer = emotion_scorer_per_turn(rubric, model=grader_model)
    else:
        task_scorer = emotion_scorer(rubric, model=grader_model)

    @task
    def run_eval() -> Task:
        return Task(
            dataset=eval_dataset,
            solver=task_solver,
            scorer=task_scorer,
            metadata=run_config,
        )

    log = eval(run_eval(), model=model_tested, limit=samples_tested, log_dir=str(log_dir))


if __name__ == "__main__":
    typer.run(main)
