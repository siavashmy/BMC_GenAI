# app.py
import streamlit as st
import google.generativeai as genai
import os

# -------------------------------
# Configure Gemini API
# -------------------------------
if "GEMINI_API_KEY" not in st.secrets:
    st.error("❌ Please add your Gemini API key in Streamlit Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-2.0-flash")

# -------------------------------
# Define workflow steps
# -------------------------------
STEPS = [
    "Story Input",
    "Focus Generation",
    "Issues Generation",
    "Tension Matrix",
    "Dilemmas & Ranking",
    "Value Propositions",
    "SWOT Analysis",
    "Business Model Canvas"
]

# -------------------------------
# Predefined prompt templates
# -------------------------------
PROMPTS = {
    "Focus Generation": """You are given the user's story below. Apply the Dilemma Triangle methodology (People, Planet, Prosperity) to extract focus areas.
For each driver, produce 1–3 specific focus areas and a short rationale (1–2 sentences).
Return only valid JSON and nothing else:
{
  "focuses": [
    {"driver":"People","focus":"...","rationale":"..."},
    {"driver":"Planet","focus":"...","rationale":"..."},
    {"driver":"Prosperity","focus":"...","rationale":"..."}
  ]
}""",

    "Issues Generation": """Given the focus areas (and drivers), list 3–6 issues for each focus area that stem from it.
Return only valid JSON and nothing else:
{
  "issues_by_focus": [
    {"focus":"...","driver":"...","issues":[{"issue":"...","explain":"..."}]}
  ]
}""",

    "Tension Matrix": """Given the issues across focuses, generate a tension matrix describing conflicts or tradeoffs between issues.
Return only valid JSON and nothing else:
{
  "tensions":[
    {"issue_a":"...","issue_b":"...","tension":"...","why":"..."}
  ]
}""",

    "Dilemmas & Ranking": """From the tension matrix, generate dilemmas phrased as tradeoffs.
Each dilemma should include a title, description, affected drivers, and an importance score (1–10).
Return only valid JSON and nothing else:
{
  "dilemmas":[
    {"title":"...","description":"...","drivers":["People","Planet"],"score":8}
  ]
}""",

    "Value Propositions": """For the top dilemmas, propose 2–5 concrete only 2 or 3 value propositions (solutions) addressing the dilemmas while balancing drivers.
Return only valid JSON and nothing else:
{
  "value_propositions":[
    {"title":"...","explain":"...","dilemmas":["..."],"benefits":["..."]}
  ]
}""",

    "SWOT Analysis": """Perform a SWOT analysis on each provided value proposition.
Return only valid JSON and nothing else:
{
  "swot":[
    {"title":"...","S":["..."],"W":["..."],"O":["..."],"T":["..."]}
  ]
}""",

"Business Model Canvas": """Generate a Business Model Canvas (9 blocks) for each value proposition.
Return only valid JSON and nothing else. Make sure to include all 9 blocks with the exact keys:
- key_partners
- key_activities
- key_resources
- value_propositions
- customer_relationships
- channels
- customer_segments
- revenue_streams
- cost_structure

JSON format example:
{
  "bmc":[
    {
      "value_proposition":"<Title of Value Proposition>",
      "canvas":{
        "key_partners":["..."],
        "key_activities":["..."],
        "key_resources":["..."],
        "value_propositions":["..."],
        "customer_relationships":["..."],
        "channels":["..."],
        "customer_segments":["..."],
        "revenue_streams":["..."],
        "cost_structure":["..."]
      }
    }
  ]
}"""
}

# -------------------------------
# Initialize session state
# -------------------------------
if "step_index" not in st.session_state:
    st.session_state.step_index = 0
if "conversation" not in st.session_state:
    st.session_state.conversation = []
if "story" not in st.session_state:
    st.session_state.story = ""
if "completed" not in st.session_state:
    st.session_state.completed = False  # New flag for final completion

# -------------------------------
# Current step
# -------------------------------
current_step = STEPS[st.session_state.step_index]
st.title("🌍 Dilemma Triangle → Business Model Canvas")
st.header(f"Step {st.session_state.step_index + 1}: {current_step}")

# -------------------------------
# Step 1: Story input
# -------------------------------
if current_step == "Story Input":
    user_story = st.text_area("✏️ Please provide the full story or context:", value=st.session_state.story, height=200)
    if st.button("Submit Story"):
        if user_story.strip():
            st.session_state.story = user_story.strip()
            st.session_state.conversation.append({
                "step": "Story Input",
                "prompt": user_story.strip(),
                "response": "✅ Story saved successfully.",
                "feedback": ""
            })
            st.session_state.step_index += 1
            st.success("Story submitted. Proceeding to Focus Generation.")
            st.rerun()
        else:
            st.warning("Please enter the story before continuing.")

# -------------------------------
# Step 2–8: LLM-driven steps
# -------------------------------
else:
    # Generate if not already done
    if len(st.session_state.conversation) <= st.session_state.step_index:
        prev_outputs = "\n\n".join([f"### Step: {c['step']}\n{c['response']}" for c in st.session_state.conversation])
        base_prompt = PROMPTS.get(current_step, "")
        story_context = st.session_state.story
        final_prompt = f"{base_prompt}\n\nContext:\n{story_context}\n\nPrevious Outputs:\n{prev_outputs}"

        with st.spinner(f"Generating {current_step}..."):
            response = model.generate_content(final_prompt)
            text_response = response.text if hasattr(response, "text") else "Error: No valid response."

        st.session_state.conversation.append({
            "step": current_step,
            "prompt": final_prompt,
            "response": text_response,
            "feedback": ""
        })
        st.success(f"✅ {current_step} generated successfully.")
        st.rerun()

    # Display conversation history
    for idx, item in enumerate(st.session_state.conversation):
        st.markdown(f"### {idx + 1}. {item['step']}")
        if item['step'] == "Story Input":
            st.info(f"📖 Story: {item['prompt']}")
        else:
            st.markdown(f"**🤖 LLM Output:**")
            with st.expander("View Output"):
                st.write(item['response'])

        if idx == st.session_state.step_index:
            feedback_key = f"feedback_{idx}"
            if feedback_key not in st.session_state:
                st.session_state[feedback_key] = item.get("feedback", "")

            feedback_text = st.text_input(
                f"Provide feedback for {item['step']}",
                value=st.session_state[feedback_key],
                key=feedback_key + "_input"
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"🔄 Refine {item['step']}", key=f"refine_{idx}"):
                    if feedback_text.strip():
                        with st.spinner("Refining response..."):
                            refine_prompt = (
                                f"Refine the following output based on this feedback.\n\n"
                                f"Feedback:\n{feedback_text}\n\nOriginal Output:\n{item['response']}"
                            )
                            refined = model.generate_content(refine_prompt)
                            refined_text = refined.text if hasattr(refined, "text") else "Error: No refined response."
                            st.session_state.conversation[idx]["response"] = refined_text
                            st.session_state.conversation[idx]["feedback"] = feedback_text
                        st.success("✅ Response refined successfully.")
                        st.rerun()
                    else:
                        st.warning("Please enter feedback before refining.")

            with col2:
                if st.button(f"✅ Approve {item['step']}", key=f"approve_{idx}"):
                    if st.session_state.step_index < len(STEPS) - 1:
                        st.session_state.step_index += 1
                        st.success(f"Step {idx + 1} approved. Moving to next step: {STEPS[st.session_state.step_index]}")
                        st.rerun()
                    else:
                        st.session_state.completed = True  # Mark process completed
                        st.success("🎉 All steps completed! You can now export the final report.")
                        st.rerun()

        else:
            st.caption("✅ Step completed")

# -------------------------------
# Final Export Button (only visible after last step approved)
# -------------------------------
if st.session_state.completed:
    st.markdown("---")
    if st.button("💾 Save Final Report"):
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        file_path = os.path.join(desktop_path, "BMC_Full_Report.txt")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                for c in st.session_state.conversation:
                    f.write(f"## {c['step']}\n")
                    f.write(f"### Prompt:\n{c['prompt']}\n\n")
                    f.write(f"### Response:\n{c['response']}\n\n")
                    if c.get("feedback"):
                        f.write(f"### Feedback:\n{c['feedback']}\n\n")
            st.success(f"✅ Saved successfully at: {file_path}")
        except Exception as e:
            st.error(f"❌ Error saving file: {e}")

# -------------------------------
# Visual SWOT Analysis
# -------------------------------
if current_step == "SWOT Analysis" and len(st.session_state.conversation) > 0:
    st.markdown("---")
    st.subheader("🧠 SWOT Analysis Dashboard")

    import json, re

    def listify(value):
        """Convert string or list into bullet list."""
        if isinstance(value, list):
            return value
        elif isinstance(value, str):
            return [v.strip("-• ") for v in re.split(r"[\n,;]", value) if v.strip()]
        return []

    try:
        last_output = st.session_state.conversation[-1]["response"]
        match = re.search(r"(\{(?:.|\n)*\})", last_output)
        json_str = match.group(1) if match else None

        if not json_str:
            st.warning("⚠️ No JSON object found in SWOT output.")
        else:
            data = json.loads(json_str)
            if "swot" in data and isinstance(data["swot"], list):
                for entry in data["swot"]:
                    st.markdown(f"## 🌿 {entry.get('title', 'Untitled Initiative')}")

                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(
                            """
                            <div style="background-color:#e6ffe6;border-radius:10px;padding:10px 16px;margin-bottom:8px;">
                                <h5>💪 Strengths</h5>
                                <ul style="margin-top:6px;">
                            """ +
                            "".join([f"<li>{s}</li>" for s in listify(entry.get("S"))]) +
                            "</ul></div>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            """
                            <div style="background-color:#fff0f0;border-radius:10px;padding:10px 16px;margin-bottom:8px;">
                                <h5>⚠️ Weaknesses</h5>
                                <ul style="margin-top:6px;">
                            """ +
                            "".join([f"<li>{w}</li>" for w in listify(entry.get("W"))]) +
                            "</ul></div>",
                            unsafe_allow_html=True,
                        )
                    with col2:
                        st.markdown(
                            """
                            <div style="background-color:#f0f8ff;border-radius:10px;padding:10px 16px;margin-bottom:8px;">
                                <h5>🚀 Opportunities</h5>
                                <ul style="margin-top:6px;">
                            """ +
                            "".join([f"<li>{o}</li>" for o in listify(entry.get("O"))]) +
                            "</ul></div>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            """
                            <div style="background-color:#fff8e6;border-radius:10px;padding:10px 16px;margin-bottom:8px;">
                                <h5>💣 Threats</h5>
                                <ul style="margin-top:6px;">
                            """ +
                            "".join([f"<li>{t}</li>" for t in listify(entry.get("T"))]) +
                            "</ul></div>",
                            unsafe_allow_html=True,
                        )

                    st.markdown(
                        f"""
                        <div style="background-color:#f9f9f9;border-radius:10px;padding:12px 16px;margin-top:8px;box-shadow:0 1px 3px rgba(0,0,0,0.1);">
                            <h5>💡 Recommendation</h5>
                            <p>{entry.get("recommendation", "No recommendation provided.")}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.markdown("---")

            else:
                st.info("No valid SWOT data found in output.")
    except json.JSONDecodeError as e:
        st.error(f"❌ Could not parse SWOT JSON: {e}")
    except Exception as e:
        st.error(f"⚠️ Error displaying SWOT Analysis: {e}")

# -------------------------------
# Visual Business Model Canvas (Fixed-size Blocks)
# -------------------------------
if current_step == "Business Model Canvas" and len(st.session_state.conversation) > 0:
    st.markdown("---")
    st.subheader("📊 Visual Business Model Canvas")

    import json, re

    # Normalize any list or string into a list of items
    def listify(value):
        if isinstance(value, list):
            return [v for v in value if v]
        elif isinstance(value, str):
            parts = [v.strip("-• ") for v in re.split(r"[\n,;]", value) if v.strip()]
            return parts
        return []

    # Render a block with fixed width and height
    def render_block(icon, title, items, width="250px", height="200px", color="#f8f9fa"):
        items_list = listify(items)
        if not items_list:
            items_list = ["—"]
        st.markdown(
            f"""
            <div style="
                width:{width};
                height:{height};
                overflow-y:auto;
                background-color:{color};
                border-radius:12px;
                padding:12px 16px;
                margin:8px;
                box-shadow:0 1px 8px rgba(0,0,0,0.15);
            ">
                <h5 style="margin:0; font-size:16px;">{icon} {title}</h5>
                <ul style="margin-top:4px; padding-left:20px;">
                    {''.join(f'<li>{x}</li>' for x in items_list)}
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    try:
        last_output = st.session_state.conversation[-1]["response"]
        match = re.search(r"(\{(?:.|\n)*\})", last_output)
        json_str = match.group(1) if match else None

        if not json_str:
            st.warning("⚠️ No JSON object found in model output.")
        else:
            data = json.loads(json_str)
            if "bmc" in data and isinstance(data["bmc"], list):
                for entry in data["bmc"]:
                    vp_title = entry.get("value_proposition", "Unnamed Value Proposition")
                    st.markdown(f"## 💡 {vp_title}")

                    canvas = entry.get("canvas", {})
                    normalized_canvas = {k.lower().replace(" ", "_").strip(): v for k, v in canvas.items()}

                    # Define a 3x3 grid for BMC
                    row1, row2, row3 = st.columns(3)
                    with row1:
                        render_block("5️⃣", "Key Partners", normalized_canvas.get("key_partners") or normalized_canvas.get("key_partnerships"))
                        render_block("6️⃣", "Key Activities", normalized_canvas.get("key_activities"))
                        render_block("7️⃣", "Key Resources", normalized_canvas.get("key_resources"))
                    with row2:
                        render_block("2️⃣", "Customer Segments", normalized_canvas.get("customer_segments"))
                        render_block("1️⃣", "Value Propositions", normalized_canvas.get("value_propositions"), width="300px", height="250px", color="#fffbe6")
                        render_block("3️⃣", "Customer Relationships", normalized_canvas.get("customer_relationships"))
                    with row3:
                        render_block("4️⃣", "Channels", normalized_canvas.get("channels"))
                        render_block("8️⃣", "Cost Structure", normalized_canvas.get("cost_structure"))
                        render_block("9️⃣", "Revenue Streams", normalized_canvas.get("revenue_streams"))

                    st.markdown("---")
            else:
                st.info("No valid Business Model Canvas data found in output.")
    except json.JSONDecodeError as e:
        st.error(f"❌ Could not parse Business Model Canvas JSON: {e}")
    except Exception as e:
        st.error(f"⚠️ Error displaying Business Model Canvas: {e}")

