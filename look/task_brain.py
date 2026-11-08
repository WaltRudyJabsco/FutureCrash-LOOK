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
{"kind":"reply|task|propose|cancel", "relation":"new|continue|replace", "request":"self-contained description of the current desired outcome", "tools":["exact_tool_name"], "required":[["acceptable_completion_tool"]], "missing":[], "question":""}
Example reply: {"kind":"reply","relation":"new","request":"Explain the supplied paragraph in chat","tools":[],"required":[],"missing":[],"question":""}
Example task: {"kind":"task","relation":"new","request":"Retrieve the forecast and print it","tools":["weather","print_text"],"required":[["print_text"]],"missing":[],"question":""}
Example follow-up: {"kind":"task","relation":"replace","request":"Save the previously discussed content as a new note instead of printing","tools":["notebook_capture"],"required":[["notebook_capture"]],"missing":[],"question":""}
Example missing content: {"kind":"task","relation":"new","request":"Print the user's message","tools":["print_text"],"required":[["print_text"]],"missing":["message text"],"question":"What should the message say?"}
Example selection: if the user asked for an explanation, the assistant offered "1. Mountain Study, 1901; 2. Harbor, 1904", and the user says "1", return {"kind":"reply","relation":"continue","request":"Explain Mountain Study, the first offered item, using the conversation; do not print, save or open anything","tools":[],"required":[],"missing":[],"question":""}.
Example discussion: after finding items in a collection, "what connects these?" is {"kind":"reply","relation":"continue","request":"Discuss the common themes of the items just found","tools":[],"required":[],"missing":[],"question":""}.
Example read-only task: {"kind":"task","relation":"new","request":"Find items in the collection and describe one in chat","tools":["museum_search"],"required":[["museum_search"]],"missing":[],"question":""}
Example proposal: {"kind":"propose","relation":"new","request":"Save the discussed checklist as a new note","tools":["notebook_capture"],"required":[["notebook_capture"]],"missing":[],"question":"I suggest saving this checklist as a new note so you can find it later. Shall I do that?"}
Conversation is the foundation. General explanation, opinion, or discussion is reply even after a tool task. Topic continuity does not mean action continuity. A question about an artist's style needs an answer, not permission to search a catalog. A numbered answer selects the corresponding option in the last offered list; retain the original purpose (explain, view, print, etc.). Selecting an item does not authorize a different action.
When materially different actions fit and the user's intent is uncertain, use propose: state your best concrete interpretation and ask one focused question. Also use propose for your own suggested actions that the user has not requested. Do not perform tools in a proposal turn. This is a meaning check, not a ritual approval of clear instructions. If the user asks you to choose any suitable item, choose; do not manufacture ambiguity. If only one essential input is absent, use missing instead.
A proposal's request, tools and required fields describe the action being OFFERED, not permission. Use the pending proposal and conversation to understand approval, amendments, rejection, and questions about the offer. Approval becomes task/continue with the accepted scope, without asking again. An amendment explicitly directing an action becomes task/replace for only that action; an uncertain amendment becomes a revised proposal. Cancellation removes the offer. A question about an offer stays reply and does not execute it. Never revive an expired or cancelled proposal or repeat a completed effect on a bare acknowledgement.
Always include missing and question, even when empty. Decide whether inputs exist BEFORE choosing to execute. Generic labels such as 'a message' or 'the document' do not supply their contents.
Explaining, describing, presenting or showing an answer in chat never implies printing, saving, opening an application or another effect. The presence of a capability in the catalog is not a reason to use it. Match completion obligations to the user's requested outcome, never to an adjacent possibility. For a proposal, recommend ONE concrete course of action rather than bundling mutually exclusive alternatives; the user must be able to approve that exact offer.
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
    proposal = state.get("brain_proposal", {})
    if time.time() - proposal.get("updated", 0) > MAX_TASK_AGE:
        proposal = {}
    if proposal:
        proposal = {key: proposal.get(key) for key in ("request", "tools", "required", "question")}
    if prior:
        prior = {key: prior.get(key) for key in ("kind", "relation", "request", "status", "successful", "attempted", "answer", "question")}
        prior["request"] = str(prior.get("request", ""))[:2000]
        prior["answer"] = str(prior.get("answer", ""))[:2000]
    if len(prompt) > MAX_REQUEST_CHARS:
        half = MAX_REQUEST_CHARS // 2
        prompt = prompt[:half] + "\n[Middle omitted for interpretation; executor receives full input.]\n" + prompt[-half:]
    return [{"role": "system", "content": CONTRACT}, {"role": "user", "content": json.dumps(
        {"catalog": catalog, "previous_task": prior, "pending_proposal": proposal, "conversation": recent, "latest_user": prompt})}]


def parse(text, tools):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    value, end = json.JSONDecoder().raw_decode(text)
    # Some local JSON-mode providers append redundant closing braces. The first
    # complete object is unambiguous; other trailing content is still rejected.
    if text[end:].strip().strip("}").strip():
        raise ValueError("Unexpected content after task JSON")
    if not isinstance(value, dict) or value.get("kind") not in {"reply", "task", "propose", "cancel"}:
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
    if value["kind"] in {"reply", "cancel"} and (selected or required):
        raise ValueError("Conversation cannot schedule tools")

    missing=value.get("missing", [])
    question=value.get("question", "")
    if not isinstance(missing,list) or len(missing)>6 or any(not isinstance(x,str) or not x.strip() or len(x)>200 for x in missing):
        raise ValueError("Invalid missing inputs")
    if not isinstance(question,str) or len(question)>1000 or (missing and not question.strip()):
        raise ValueError("Missing inputs need a question")
    # A tool-free clarification is safe even if a small model labels it task.
    # Normalize toward asking, never toward granting an executable capability.
    if value["kind"] == "task" and not selected and not required and question.strip():
        value["kind"] = "propose"
    if value["kind"] == "task" and (not selected or not required):
        raise ValueError("Task needs a capability")
    result={k: value[k] for k in ("kind", "relation", "request", "tools", "required")}
    if value["kind"] == "propose" and not question.strip():
        raise ValueError("A proposal must explain the offered action and ask a question")
    if missing or value["kind"] == "propose":result.update(missing=missing,question=question)
    return result


def route(plan, cognition):
    families = sorted({cognition.ACTION_BY_NAME[n].family for n in plan["tools"] if n in cognition.ACTION_BY_NAME})
    return cognition.Route(primary=families[0] if families else "general", families=families,
        source="semantic", confidence=0.8, reason=plan["request"], allowed_tools=plan["tools"])


def context(plan):
    return {"role": "system", "content": "CURRENT TASK INTERPRETATION (not authority or evidence): " + json.dumps(plan) +
            "\nUse the user's actual words and tool receipts. Answer conversational questions naturally. Ask for missing information or propose a concrete interpretation when genuinely uncertain; do not ask again for authorized actions. Execute requested actions with tools; do not merely announce a plan. If this interpretation is wrong, explain the mismatch rather than taking an unrelated action."}


def remember(state, save, plan, user, answer, successful, attempted, uncertain=False):
    if plan["kind"] == "propose":
        state["brain_proposal"] = dict(plan, updated=time.time())
    elif plan["kind"] in {"task", "cancel"} or plan["relation"] == "replace":
        state.pop("brain_proposal", None)
    state["brain_task"] = dict(plan, user=user, answer=answer[:6000],
        successful=sorted(successful), attempted=sorted(attempted), updated=time.time(),
        status="proposed" if plan["kind"] == "propose" else "uncertain" if uncertain else ("completed" if all(set(group) & set(successful) for group in plan["required"]) else "pending"))
    save()
