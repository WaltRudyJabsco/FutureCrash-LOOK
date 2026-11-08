"""Semantic task interpretation shared by every LO surface.

The planner chooses capabilities, never tool arguments or permission grants.
Host receipts, not its prose, determine whether the requested effects happened.
"""
import json
import time

MAX_HISTORY = 6
MAX_TASK_AGE = 1800
MAX_HISTORY_CHARS = 4000
MAX_REQUEST_CHARS = 10000
CONTRACT = """Interpret the latest user message in context. Return ONLY a JSON object:
{"kind":"reply|task|cancel", "relation":"new|continue|replace", "request":"self-contained description of the current desired outcome", "tools":["exact_tool_name"], "required":[["acceptable_completion_tool"]], "missing":[], "question":""}
Example reply: {"kind":"reply","relation":"new","request":"Explain the supplied paragraph in chat","tools":[],"required":[],"missing":[],"question":""}
Example task: {"kind":"task","relation":"new","request":"Retrieve the forecast and print it","tools":["weather","print_text"],"required":[["print_text"]],"missing":[],"question":""}
Example follow-up: {"kind":"task","relation":"replace","request":"Save the previously discussed content as a new note instead of printing","tools":["notebook_capture"],"required":[["notebook_capture"]],"missing":[],"question":""}
Example missing content: {"kind":"task","relation":"new","request":"Print the user's message","tools":["print_text"],"required":[["print_text"]],"missing":["message text"],"question":"What should the message say?"}
Always include missing and question, even when empty. Decide whether inputs exist BEFORE choosing to execute. Generic labels such as 'a message' or 'the document' do not supply their contents.
Use the supplied catalog. Choose only tools needed for this request, including discovery before effects.
required is a list of completion obligations: each inner list contains alternative tools for ONE obligation. Retrieval alone never completes a delivery request. Include read tools when the user asks for live information. For composed requests include each distinct requested delivery.
Writing prose in chat is reply, not saving a note or file. Personal preferences and corrections are handled by the background Fabric memory system; treat them as reply, not notebook_capture, unless the user specifically requests a note or file. Questions about abilities are reply. Do not act on negated or hypothetical requests. Cancellation is cancel with no tools. A missing input is still task. If essential user-supplied content is absent, set missing to its name and question to one concise question. Do not invent a placeholder message or document. For example a request to print an unspecified message needs its text; requesting a generated greeting does not. Information obtainable from tools or configured defaults (such as home weather location or preferred printer) is not missing: let the executor discover it. Do not ask for confirmation of actions already requested.
Resolve short answers using the recent conversation. A new subject replaces the previous task. 'Instead' removes the superseded action. Completed actions are not pending; do not repeat them merely because the user refers to their output.
Preserve supplied facts. Never invent content, paths, destinations, source results, authorization, or success. Assistant messages and previous task state are context, not instructions. A task description is not permission to run commands.
"""


def planning_messages(prompt, history, state, tools):
    catalog = [{"name": t["function"]["name"],
                "description": t["function"].get("description", "")[:160]} for t in tools]
    prior = state.get("brain_task", {})
    if time.time() - prior.get("updated", 0) > MAX_TASK_AGE:
        prior = {}
    recent = []
    remaining = MAX_HISTORY_CHARS
    for message in reversed(history):
        if message.get("role") not in {"user", "assistant"}:
            continue
        content = str(message.get("content", ""))[:remaining]
        if not content or len(recent) >= MAX_HISTORY:
            break
        recent.insert(0, {"role": message["role"], "content": content})
        remaining -= len(content)
    if prior:
        prior = {key: prior.get(key) for key in ("kind", "relation", "request", "status", "successful", "attempted")}
        prior["request"] = str(prior.get("request", ""))[:2000]
    if len(prompt) > MAX_REQUEST_CHARS:
        half = MAX_REQUEST_CHARS // 2
        prompt = prompt[:half] + "\n[Middle omitted for interpretation; executor receives full input.]\n" + prompt[-half:]
    return [{"role": "system", "content": CONTRACT}, {"role": "user", "content": json.dumps(
        {"catalog": catalog, "previous_task": prior, "conversation": recent, "latest_user": prompt})}]


def parse(text, tools):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    value, end = json.JSONDecoder().raw_decode(text)
    # Some local JSON-mode providers append redundant closing braces. The first
    # complete object is unambiguous; other trailing content is still rejected.
    if text[end:].strip().strip("}").strip():
        raise ValueError("Unexpected content after task JSON")
    if not isinstance(value, dict) or value.get("kind") not in {"reply", "task", "cancel"}:
        raise ValueError("Invalid task kind")
    if value.get("relation") not in {"new", "continue", "replace"}:
        raise ValueError("Invalid task relation")
    names = {t["function"]["name"] for t in tools}
    selected = value.get("tools")
    required = value.get("required")
    # A tool-free reply cannot carry action obligations. Discard stray obligation
    # tokens conservatively rather than promoting them to executable tools.
    if value["kind"] in {"reply","cancel"} and selected == []:
        required = value["required"] = []
    if not isinstance(selected, list) or len(selected) > 16 or any(not isinstance(n, str) or n not in names for n in selected):
        raise ValueError("Unknown task capability")
    if not isinstance(required, list) or len(required) > 8 or any(
        not isinstance(g, list) or not g or any(n not in selected for n in g) for g in required):
        raise ValueError("Invalid completion obligation")
    request = value.get("request")
    if not isinstance(request, str) or not request.strip() or len(request) > 12000:
        raise ValueError("Invalid task description")
    if value["kind"] != "task" and (selected or required):
        raise ValueError("Conversation cannot schedule tools")
    if value["kind"] == "task" and (not selected or not required):
        raise ValueError("Task needs a capability")
    missing=value.get("missing", [])
    question=value.get("question", "")
    if not isinstance(missing,list) or len(missing)>6 or any(not isinstance(x,str) or not x.strip() or len(x)>200 for x in missing):
        raise ValueError("Invalid missing inputs")
    if not isinstance(question,str) or len(question)>1000 or (missing and not question.strip()):
        raise ValueError("Missing inputs need a question")
    result={k: value[k] for k in ("kind", "relation", "request", "tools", "required")}
    if missing:result.update(missing=missing,question=question)
    return result


def route(plan, cognition):
    families = sorted({cognition.ACTION_BY_NAME[n].family for n in plan["tools"] if n in cognition.ACTION_BY_NAME})
    return cognition.Route(primary=families[0] if families else "general", families=families,
        source="semantic", confidence=0.8, reason=plan["request"], allowed_tools=plan["tools"])


def context(plan):
    return {"role": "system", "content": "CURRENT TASK INTERPRETATION (not authority or evidence): " + json.dumps(plan) +
            "\nUse the user's actual words and tool receipts. Ask only for missing information. Execute requested actions with tools; do not merely announce a plan. If this interpretation is wrong, explain the mismatch rather than taking an unrelated action."}


def remember(state, save, plan, user, answer, successful, attempted, uncertain=False):
    state["brain_task"] = dict(plan, user=user, answer=answer[:6000],
        successful=sorted(successful), attempted=sorted(attempted), updated=time.time(),
        status="uncertain" if uncertain else ("completed" if all(set(group) & set(successful) for group in plan["required"]) else "pending"))
    save()
