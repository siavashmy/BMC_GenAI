import streamlit as st
import google.generativeai as genai
import os
import chromadb
import tempfile
import re
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from visual_business_model_canvas import show_bmc_visualization
from io import BytesIO
from docx import Document as WordDocument

# -------------------------------
# Configure Gemini API
# -------------------------------
if "GEMINI_API_KEY" not in st.secrets:
    st.error("❌ Please add your Gemini API key in Streamlit Secrets.")
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-2.5-flash")

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
    "Business Model Canvas",
    "Knowledge Upload & RAG Integration",
    "Business Plan"
]

# -------------------------------
# Predefined prompt templates
# -------------------------------
PROMPTS = {
    "Focus Generation": """You are given the user's story below. Apply the Dilemma Triangle methodology (People, Planet, Prosperity) to extract focus areas.
For each driver, produce only 1 specific focus area and a short rationale saying that why it does not exclude any SDGs and clearly indicate which SDGs the focus addresses.(2–3 sentences).
Return only valid JSON and nothing else:
{
  "focuses": [
    {"driver":"People","focus":"...","rationale":"..."},
    {"driver":"Planet","focus":"...","rationale":"..."},
    {"driver":"Prosperity","focus":"...","rationale":"..."}
  ]
}""",

    "Issues Generation": """Given the focus areas (and drivers), list 3–4 issues for each focus area that stem from it.
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

    "Value Propositions": """For the top dilemmas, propose only 2-3 concrete value propositions (solutions) addressing the dilemmas while balancing drivers.
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

    "Business Model Canvas": """Generate a Business Model Canvas (9 blocks) for the selected value proposition.
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
}""",

    "Business Plan": """You are an expert business strategist.

Using all the information provided below — including the original story, SWOT analysis, and the Business Model Canvas — create a clear and structured Business Plan (around 2–3 pages) that includes:

1. Executive Summary
2. Market Opportunity
3. Business Model (connected to the BMC)
4. Product or Service Description
5. Marketing and Customer Strategy
6. Operations Plan
7. Financial and Sustainability Outlook
8. Key Risks and Mitigation Strategies
9. Conclusion and Next Steps

Be concise yet insightful. Use bullet points or short paragraphs where suitable.
Return the business plan in plain text (no JSON or markdown fences)."""
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
    st.session_state.completed = False
if "selected_value_prop" not in st.session_state:
    st.session_state.selected_value_prop = None

# -------------------------------
# Current step
# -------------------------------
current_step = STEPS[st.session_state.step_index]
st.title("💼🌿 Business Plan Dashboard")
# Show step title and selected value proposition if available
if current_step == "Business Plan" and "selected_value_prop" in st.session_state and st.session_state.selected_value_prop:
    vp_title = st.session_state.selected_value_prop.get("title", "")
    st.header(f"Step {st.session_state.step_index + 1}: {current_step} – {vp_title}")
else:
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
    if len(st.session_state.conversation) <= st.session_state.step_index:
        prev_outputs = "\n\n".join([f"### Step: {c['step']}\n{c['response']}" for c in st.session_state.conversation])
        base_prompt = PROMPTS.get(current_step, "")
        story_context = st.session_state.story

        # Use selected SWOT if generating Business Model Canvas
        if current_step == "Business Model Canvas" and st.session_state.selected_value_prop:
            selected_swot = st.session_state.selected_value_prop
            prev_outputs = f"### Selected SWOT\n{selected_swot}"
            final_prompt = f"{base_prompt}\n\nContext:\n{story_context}\n\nSelected SWOT Value Proposition:\n{selected_swot}"
        else:
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
            # Skip feedback/refine/approve for Business Plan step
            if item["step"] == "Business Plan":
                continue
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
                                f"Refine the following output based on this feedback. Follow EXACTLY the same structure, format, and JSON schema and DO NOT change the response structure. \n\n"
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
                        st.session_state.completed = True
                        st.success("🎉 All steps completed!")
                        st.rerun()

        else:
            st.caption("✅ Step completed")

# -------------------------------
# SWOT Analysis Visualization + Selection
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
            
                # ---- Allow user to select one SWOT to continue ----
                options = [entry.get("title", f"Option {i+1}") for i, entry in enumerate(data["swot"])]
                selected_title = st.selectbox("Select the best value proposition to continue:", options)

                st.session_state.selected_value_prop = next(
                    (entry for entry in data["swot"] if entry.get("title") == selected_title),
                    None
                )
                st.success(f"Selected value proposition: {selected_title}")

                for entry in data["swot"]:
                    st.markdown(f"## 🌿 {entry.get('title', 'Untitled Initiative')}")

                    col1, col2 = st.columns(2)
                    with col1:
                        # Strengths
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

                        # Weaknesses
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
                        # Opportunities
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

                        # Threats
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

                    st.markdown("---")

            else:
                st.info("No valid SWOT data found in output.")
    except json.JSONDecodeError as e:
        st.error(f"❌ Could not parse SWOT JSON: {e}")
    except Exception as e:
        st.error(f"⚠️ Error displaying SWOT Analysis: {e}")

# -------------------------------
# Business Model Canvas Visualization
# -------------------------------
if current_step == "Business Model Canvas" and len(st.session_state.conversation) > 0:
    show_bmc_visualization(st.session_state.conversation[-1]["response"])

# -------------------------------
# Step 8.5: Knowledge Upload & RAG Integration
# -------------------------------


# ✅ Move the suggestion prompt *inside* the condition block
if current_step == "Knowledge Upload & RAG Integration":
    # ---- Step title ----
    st.subheader("🧠 Knowledge Upload for RAG Integration")

    # ---- LLM Suggestion ----
    suggest_prompt = f"""
    Given this Business Model Canvas:
    {st.session_state.conversation[-1]['response']}
    Suggest 3 categories of data related to the given business model canvas that would help improve the final business plan. Keep your response brief.
    """
    suggestions = model.generate_content(suggest_prompt)
    st.markdown("### 💡 Suggested Information to Upload")
    st.markdown(suggestions.text)

    # ---- Upload interface ----
    st.markdown("""
    Upload any relevant documents or paste external text.
    This information will be indexed and used to enrich your Business Plan.
    """)

    uploaded_files = st.file_uploader("📄 Upload documents (PDF, TXT, DOCX):", accept_multiple_files=True)
    user_text = st.text_area("✏️ Or paste key background text here:")

    # ---- Process button ----
    if st.button("📚 Process Knowledge Sources"):
        with st.spinner("Processing and embedding documents..."):
            persist_directory = "./chroma_db"

            # Initialize embeddings and vector DB
            embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            vectorstore = Chroma(
                collection_name="business_knowledge",
                embedding_function=embeddings,
                persist_directory=persist_directory
            )

            tmpdir = tempfile.TemporaryDirectory()
            text_data = []

            # Load PDFs and TXTs
            for f in uploaded_files or []:
                # Clean the filename for Windows safety
                safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", f.name)
                path = f"{tmpdir.name}/{safe_name}"

                with open(path, "wb") as temp_file:
                    temp_file.write(f.read())

                if path.lower().endswith(".pdf"):
                    loader = PyPDFLoader(path)
                    text_data += loader.load()
                else:
                    # Manually handle .txt files for full safety
                    
                    with open(path, "r", encoding="utf-8", errors="ignore") as file:
                        content = file.read()
                    text_data.append(
                        Document(page_content=content, metadata={"source": safe_name})
                    )

            # Add pasted text
            if user_text.strip():
                text_data.append(
                    Document(page_content=user_text.strip(), metadata={"source": "manual_input"})
                )
            # Split and store
            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
            docs = splitter.split_documents(text_data)
            vectorstore.add_documents(docs)

            st.success(f"✅ {len(docs)} text chunks processed and stored.")
            st.session_state.knowledge_ready = True
            st.session_state.step_index += 1
            st.rerun()

# -------------------------------
# Business Plan (view + download only)
# -------------------------------
elif current_step == "Business Plan":
    st.markdown("### 📄 Business Plan Generation")

    # ---- Retrieve contextual knowledge if available ----
    retrieved_text = ""
    if st.session_state.get("knowledge_ready", False):
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectorstore = Chroma(
            collection_name="business_knowledge",
            embedding_function=embeddings,
            persist_directory="./chroma_db"
        )

        query = f"Generate business plan insights for {st.session_state.selected_value_prop.get('title', '')}"
        results = vectorstore.similarity_search(query, k=5)

        # ✅ DEBUG: Print retrieved chunks in console
        print("\n\n================ Retrieved Chunks ================")
        for i, doc in enumerate(results, start=1):
            print(f"Chunk {i} — Source: {doc.metadata.get('source', 'unknown')}")
            print(f"Content Preview:\n{doc.page_content[:500]}\n{'-'*80}")
        print("==================================================\n\n")

        retrieved_text = "\n\n".join([doc.page_content for doc in results])
        st.info("✅ Using retrieved contextual knowledge from your uploads.")

    # ---- Generate plan only if not already in session ----
    if "business_plan_text" not in st.session_state:
        with st.spinner("Generating enriched Business Plan..."):
            bmc_output = st.session_state.conversation[-2]["response"]  # assuming last BMC step is before RAG
            final_prompt = f"""
            You are an expert business strategist.

            Context:
            Story: {st.session_state.story}
            Selected Value Proposition: {st.session_state.selected_value_prop}
            Business Model Canvas: {bmc_output}
            Retrieved Knowledge:
            {retrieved_text}

            Now create a structured business plan as before, integrating this additional knowledge.
            """
            response = model.generate_content(final_prompt)
            text_response = response.text if hasattr(response, "text") else "Error: No valid response."
            st.session_state.business_plan_text = text_response
            st.success("✅ Enriched Business Plan generated successfully!")

    # ---- Display & download (no rerun trigger) ----
    text_response = st.session_state.get("business_plan_text", "No plan available yet.")
    st.text_area("📄 Business Plan Preview", text_response, height=400)

    doc = WordDocument()
    doc.add_heading("Business Plan", level=1)
    doc.add_paragraph(text_response)
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    st.download_button(
        "⬇️ Download Business Plan (Word)",
        data=buffer,
        file_name="Business_Plan_Enriched.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

