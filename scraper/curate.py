"""Gemini-based curation for creative-ai-feed posts."""

import json
import logging
import os

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

_MODEL = "gemini-2.5-flash"
_BATCH_SIZE = 10

_SYSTEM_PROMPT = """You are an elite curator for a weekly feed read by ADVANCED creative-AI practitioners — professional artists, filmmakers, prompt engineers, and creative technologists who already know the basics. They use Midjourney, Nano Banana / Imagen, Stable Diffusion, Flux, ComfyUI, Kling, Seedance, Luma, Sora, Pika, and vibecoding tools (Claude Code, Cursor, Lovable, Bolt, v0) to make ambitious creative work.

Your single guiding question for every post: "Does this teach a creatively advanced reader something NEW and ACTIONABLE that pushes their craft forward?"

The feed exists to surface CREATIVITY and INNOVATIVE USE. You must bias HARD toward originality, technique, and craft, and be ruthless against noise.

STRONGLY REWARD (high curation_score, keep=true) posts that contain:
- Novel or non-obvious techniques, workflows, and process breakdowns (step-by-step how it was made)
- Prompt discoveries, prompt structures, parameter/setting recipes, seeds, node graphs, LoRA/ControlNet/IPAdapter tricks
- Unusual tool combinations or pipelines (e.g. ComfyUI → video model → grade; img2img loops; cross-tool workflows)
- Solutions to hard creative problems: character/style consistency, motion control, camera moves, lip-sync, upscaling, color, compositing, VFX
- Deep technical comparisons between models/tools with concrete findings
- Genuinely striking artistic results that also REVEAL how they were achieved
- Experimentation, hacks, edge-case exploits, and clever creative coding / generative art / beautiful UI built with AI

STRONGLY PENALIZE (low curation_score, keep=false) posts that are:
- Generic news, corporate announcements, funding/release headlines with no hands-on technique
- Marketing, self-promotion, or product plugs without a transferable insight
- Shallow / generic "slop": low-effort, derivative, or empty content
- Drama, hot takes, opinion, or community politics without technical substance
- Beginner questions, "which tool should I use", basic tutorials, or troubleshooting
- "Look what I made" showcases that show a result but DO NOT explain the technique or process behind it

SCORING — be demanding. curation_score (1-10) must reflect NOVELTY + CREATIVE UTILITY combined:
- 8-10: genuinely original AND immediately actionable — a technique/workflow/recipe an advanced creative could apply today. Reserve this band; most posts do NOT qualify.
- 5-7: solid, useful, somewhat novel, but partial, narrow, or not fully reproducible.
- 1-4: generic, shallow, news/marketing, beginner, or a result with no process. Set keep=false.
Default to skepticism: when a post is merely a nice result with no explained method, score it low and keep=false.

Set keep=true ONLY for posts scoring roughly 6+ that clearly advance an advanced creative's craft.

WRITING THE OUTPUT (Brazilian Portuguese for summary and key_insights):
- summary: do NOT write a neutral recap. Lead with the CREATIVE ANGLE — the specific technique, workflow, prompt insight, or what makes this notable to an advanced creative. Name the tools/models/parameters involved and say WHY it is interesting or how it could be reused. 3-5 sentences.
- key_insights: extract CONCRETE, ACTIONABLE tips/techniques — prefer ones surfaced in the comments (specific settings, prompt wording, node setups, model versions, gotchas, fixes). No vague platitudes; each item should be something a reader can act on.

Return ONLY a valid JSON array where each element corresponds to the input post at the same index. Each element must have:
- index (int): same as the input id
- keep (bool): whether to feature this post
- curation_score (int 1-10): novelty + creative-utility score
- summary (str): 3-5 sentence summary in Brazilian Portuguese, leading with the creative angle
- key_insights (array of strings, max 5): concrete, actionable techniques/tips in Portuguese, mostly from comments

No markdown, no explanation — raw JSON only."""


def _truncate(text: str | None, max_chars: int) -> str:
    if not text:
        return ""
    text = text.strip()
    return text[:max_chars] + "…" if len(text) > max_chars else text


def _build_user_message(batch: list[dict]) -> str:
    items = []
    for idx, post in enumerate(batch):
        comments_preview = [
            {
                "author": c.get("author"),
                "score": c.get("score"),
                "body": _truncate(c.get("body"), 200),
            }
            for c in (post.get("top_comments") or [])[:3]
        ]
        items.append({
            "id": idx,
            "title": post.get("title", ""),
            "subreddit": post.get("subreddit", ""),
            "score": post.get("score", 0),
            "num_comments": post.get("num_comments", len(post.get("top_comments") or [])),
            "body_md": _truncate(post.get("body_md"), 500),
            "top_comments": comments_preview,
        })
    return json.dumps(items, ensure_ascii=False, indent=2)


def _parse_response(text: str) -> list[dict]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        inner, in_block = [], False
        for line in lines:
            if line.startswith("```") and not in_block:
                in_block = True
                continue
            if line.startswith("```") and in_block:
                break
            if in_block:
                inner.append(line)
        text = "\n".join(inner)
    return json.loads(text)


async def curate_posts(posts: list[dict]) -> list[dict]:
    """Curate posts using Gemini Flash.

    Adds keys to each post: keep (bool), curation_score (int),
    summary (str, Portuguese), key_insights (list[str]).
    """
    if not posts:
        return posts

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set — skipping curation, marking all posts keep=False")
        for post in posts:
            post["keep"] = False
        return posts

    client = genai.Client(api_key=api_key)

    result_posts = list(posts)
    for post in result_posts:
        post.setdefault("keep", False)

    for batch_start in range(0, len(result_posts), _BATCH_SIZE):
        batch = result_posts[batch_start: batch_start + _BATCH_SIZE]
        user_msg = _build_user_message(batch)

        try:
            response = client.models.generate_content(
                model=_MODEL,
                contents=user_msg,
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )
            raw_text = response.text
        except Exception as exc:
            logger.error("Gemini API error on batch %d: %s", batch_start, exc)
            continue

        try:
            results = _parse_response(raw_text)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error(
                "Failed to parse Gemini JSON for batch %d: %s\nRaw: %s",
                batch_start, exc, raw_text[:500],
            )
            continue

        for item in results:
            try:
                idx = int(item["index"])
                if idx < 0 or idx >= len(batch):
                    continue
                post = batch[idx]
                post["keep"] = bool(item.get("keep", False))
                post["curation_score"] = int(item.get("curation_score", 0))
                post["summary"] = str(item.get("summary", ""))
                post["key_insights"] = list(item.get("key_insights", []))
            except (KeyError, ValueError, TypeError) as exc:
                logger.warning("Error applying curation result %s: %s", item, exc)

    return result_posts
