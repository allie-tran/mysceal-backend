from typing import Any, AsyncGenerator, Dict, List

from openai import BaseModel
from pydantic import RootModel
from pyrate_limiter import asyncio

from llm.prompts import ANSWER_MODEL_CHOOSING_PROMPT
from query_parse.question import question_classification
from query_parse.types.requests import (
    Data,
)
from question_answering.text import answer_text_only, get_specific_description
from question_answering.video import answer_visual_only
from results.models import (
    AnswerListResult,
    AnswerResult,
    TripletEventResults,
)
from rich import print
from transcripts.main import get_answer_from_transcript
from llm import llm_model

class AnswerModel(BaseModel):
    enabled: bool = True
    top_k: int = 10


class AnswerModelOption(RootModel):
    root: Dict[str, AnswerModel]

    def get(self, key: str, default: Any = None):
        return self.root.get(key, default)


class RetryException(Exception):
    pass
async def get_answer_models(data: Data, question: str) -> AnswerModelOption:
    prompt = ANSWER_MODEL_CHOOSING_PROMPT.format(question=question)
    answer_models = AnswerModelOption({"text": AnswerModel(), "visual": AnswerModel()})
    tries = 0
    while tries < 3:
        res = llm_model.generate_from_text(data, prompt)  # type: ignore
        try:
            if not res:
                raise Exception("Empty response")
            answer_models = AnswerModelOption.model_validate(res["answer_models"])
            break
        except Exception:
            print(res)
            tries += 1
            if tries == 3:
                print("[red]Failed to get the answer models[/red]")
                break
            await asyncio.sleep(0)
        finally:
            pass
    return answer_models



async def get_answer_tasks(
    data: Data,
    text: str,
    results: TripletEventResults,
    relevant_fields: List[str],
) -> List[AnswerResult]:
    question_type = await question_classification(data, text)
    print("[yellow]Question Type[/yellow]", question_type)
    match question_type:
        case "frequency" | "time":
            options = {"text": AnswerModel(), "visual": AnswerModel(enabled=False)}
        case _:
            options = await get_answer_models(data, text)

    print("[yellow]Answering the question with configs[/yellow]", options)
    text_model = options.get("text") or AnswerModel()
    visual_model = options.get("visual") or AnswerModel()

    k = text_model.top_k
    k = min(k, len(results.events))
    if k == -1:
        k = len(results.events)
    k = max(1, k)
    k = max(visual_model.top_k, k)

    textual_descriptions = []
    for event in results.events[:k]:
        textual_descriptions.append(
            get_specific_description(data, event.main, relevant_fields)
        )

    if not textual_descriptions:
        print(f"[red]No textual descriptions found for k={k}[/red]")
        return []

    print(
        f"[green]Textual description sample out of k={k}[/green]",
        textual_descriptions[0],
    )
    transcript = ""
    answers = []
    if data == Data.CASTLE:
        transcript = get_answer_from_transcript(data, text)
        print(transcript)
        if transcript and transcript.get("answer") is not None:
            print("[green]Transcript found[/green]")
            answers.append(AnswerResult(
                text=transcript["answer"],
                explanation=[transcript.get("explanation", "No explanation provided")],
                evidence=[],
                source="transcript"
            ))
        else:
            print("[red]No transcript found[/red]")

    answers += answer_visual_only(data, text, textual_descriptions, results, 5)
    answers += answer_text_only(data, text, textual_descriptions, k)
    return answers


async def filter_answers(
    data: Data,
    text: str,
    all_answers: AnswerListResult
):
    final_answers = AnswerListResult()
    formatted = []
    for answer in all_answers.export():
        formatted.append(
            f"""Answer: {answer.text}
Explanation: {", ".join(answer.explanation)}
Evidence: {answer.evidence}
Source: {answer.source if answer.source else "unknown"}"""
        )
    formatted_answers = "\n\n".join(formatted)

    prompt = f"""Here are some answers from multiple sources for the question: {text}
{formatted_answers}

Please provide a final answer based on the above answers. Depending on the question, some sources (visual, transcript, text/metadata) might be more reliable than others. Please take that into account when providing the final answer.

If the answer is from the transcript, provide the timestamp in the explanation in the format of day X, HH:MM, [camera]. If the answer is from the visual content, provide the event id in the evidence (as a list of integers).

Return in the same format, with just one answer:
```json
{{
    "answer": "your final answer here, keep it brief and concise",
    "explanation": "brief explanation for your final answer"
    "evidence": list[int] # list of event ids or event objects that support your answer, if any
}}
```

If the answer is not found, return an empty string as the answer. What would be the logical next step to search for the answer? Provide a suggested query in the `suggested_query` field.

```json
{{
    "answer": "",
    "explanation": "No answer found, suggest a different search query",
    "suggested_query": "your suggested query here"
}}
```
"""
    print(prompt)
    res = llm_model.generate_from_text(
        data, prompt, advanced=True
    )
    if res:
        print("[green]Final answer from LLM[/green]", res)
        final_answers.add_answer(
            AnswerResult(
                text=str(res["answer"]),
                explanation=[res.get("explanation", "No explanation provided")],
                evidence=res.get("evidence", []),
            )
        )
    return final_answers
