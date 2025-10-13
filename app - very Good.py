# app.py
import streamlit as st
import google.generativeai as genai
import os
import json

# -------------------------------
# Configure Gemini API
# -------------------------------
if "GEMINI_API_KEY" not in st.secrets:
    st.error("❌ Please add your Gemini API key in Streamlit Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-2.0-flash")

# -------------------------------
# Define new workflow steps
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
Return JSON:
{
  "focuses": [
    {"driver":"People","focus":"...","rationale":"..."},
    {"driver":"Planet","focus":"...","rationale":"..."},
    {"driver":"Prosperity","focus":"...","rationale":"..."}
  ]
}""",

    "Issues Generation": """Given the focus areas (and drivers), list 3–6 issues for each focus area that stem from it.
Return JSON:
{
  "issues_by_focus": [
    {"focus":"...","driver":"...","issues":[{"issue":"...","explain":"..."}]}
  ]
}""",

    "Tension Matrix": """Given the issues across focuses, generate a tension matrix describing conflicts or tradeoffs between issues.
Return JSON:
{
  "tensions":[
    {"issue_a":"...","issue_b":"...","tension":"...","why":"..."}
  ]
}""",

    "Dilemmas & Ranking": """From the tension matrix, generate dilemmas phrased as tradeoffs.
Each dilemma should include a title, description, affected drivers, and an importance score (1–10).
Return JSON:
{
  "dilemmas":[
    {"title":"...","description":"...","drivers":["People","Planet"],"score":8}
  ]
}""",

    "Value Propositions": """For the top dilemmas, propose 2–5 concrete value propositions (solutions) addressing the dilemmas while balancing drivers.
Return JSON:
{
  "value_propositions":[
    {"title":"...","explain":"...","dilemmas":["..."],"benefits":["..."]}
  ]
}""",

    "SWOT Analysis": """Perform a SWOT analysis on each provided value proposition.
Return JSON:
{
  "swot":[
    {"title":"...","S":["..."],"W":["..."],"O":["..."],"T":["..."],"recommendation":"..."}
  ]
}""",

    "Business Model Canvas": """Generate a Business Model Canvas (9 blocks) for each value proposition.
Return JSON:
{
  "bmc":[
    {"value_proposition":"...","canvas":{
      "Customer Segments":["..."],
      "Value Propositions":["..."],
      "Channels":["..."],
      "Customer Relationships":["..."],
      "Revenue Streams":["..."],
      "Key Activities":["..."],
      "Key Resources":["..."],
      "Key Partners":["..."],
      "Cost Structure":["..."]
    }}
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
# Step 2–8: Auto-generated using previous outputs
# -------------------------------
else:
    # If response for this step not yet generated, generate it
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

    # Display existing steps
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
                        st.success("🎉 All steps completed!")

        else:
            st.caption("✅ Step completed")

# -------------------------------
# Save final output
# -------------------------------
if st.session_state.step_index == len(STEPS) - 1 and st.button("💾 Save Final Report"):
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
