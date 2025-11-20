# visual_business_model_canvas.py
import streamlit as st
import json, re

def listify(value):
    """Convert string or list into a clean list."""
    if isinstance(value, list):
        return value
    elif isinstance(value, str):
        return [v.strip("-• ") for v in re.split(r"[\n,;]", value) if v.strip()]
    return []

def render_bullets(items):
    """Render a list of items as bullet points in Streamlit."""
    items = listify(items)
    if items:
        st.markdown("• " + "\n• ".join(items))
    else:
        st.markdown("—")  # display dash if empty

def show_bmc_visualization(response_text):
    st.markdown("---")
    st.subheader("🏗️ Business Model Canvas Visualization")

    # Extract JSON from text
    match = re.search(r"(\{(?:.|\n)*\})", response_text)
    json_str = match.group(1) if match else None
    if not json_str:
        st.warning("⚠️ No valid JSON found in BMC output.")
        return

    try:
        data = json.loads(json_str)
        if "bmc" not in data or not data["bmc"]:
            st.info("No BMC entries found in JSON.")
            return

        # Dropdown to select which BMC to view
        bmc_titles = [entry.get("value_proposition", f"BMC {i+1}") for i, entry in enumerate(data["bmc"])]
        selected_idx = st.selectbox(
            "Select Value Proposition / Canvas to View:",
            range(len(bmc_titles)),
            format_func=lambda x: bmc_titles[x],
        )
        entry = data["bmc"][selected_idx]
        canvas = entry.get("canvas", {})

        st.markdown(f"## 💡 {entry.get('value_proposition', 'Untitled Value Proposition')}")

        # -------- Top 3-column layout (classic 9 blocks) --------
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(
                '<div style="background-color:#e6f7ff;border-radius:10px;padding:10px;margin-bottom:8px;">'
                '<h5>🤝 Key Partners</h5></div>',
                unsafe_allow_html=True,
            )
            render_bullets(canvas.get("key_partners", []))

            st.markdown(
                '<div style="background-color:#ffe6e6;border-radius:10px;padding:10px;margin-bottom:8px;">'
                '<h5>⚙️ Key Activities</h5></div>',
                unsafe_allow_html=True,
            )
            render_bullets(canvas.get("key_activities", []))

            st.markdown(
                '<div style="background-color:#e6ffe6;border-radius:10px;padding:10px;margin-bottom:8px;">'
                '<h5>🧰 Key Resources</h5></div>',
                unsafe_allow_html=True,
            )
            render_bullets(canvas.get("key_resources", []))

        with col2:
            st.markdown(
                '<div style="background-color:#fff8e6;border-radius:10px;padding:10px;margin-bottom:8px;">'
                '<h5>🎁 Value Propositions</h5></div>',
                unsafe_allow_html=True,
            )
            render_bullets(canvas.get("value_propositions", []))

            st.markdown(
                '<div style="background-color:#f0f8ff;border-radius:10px;padding:10px;margin-bottom:8px;">'
                '<h5>💬 Customer Relationships</h5></div>',
                unsafe_allow_html=True,
            )
            render_bullets(canvas.get("customer_relationships", []))

            st.markdown(
                '<div style="background-color:#fff0f0;border-radius:10px;padding:10px;margin-bottom:8px;">'
                '<h5>🚚 Channels</h5></div>',
                unsafe_allow_html=True,
            )
            render_bullets(canvas.get("channels", []))

        with col3:
            st.markdown(
                '<div style="background-color:#e6ffe6;border-radius:10px;padding:10px;margin-bottom:8px;">'
                '<h5>👥 Customer Segments</h5></div>',
                unsafe_allow_html=True,
            )
            render_bullets(canvas.get("customer_segments", []))

            st.markdown(
                '<div style="background-color:#fff8e6;border-radius:10px;padding:10px;margin-bottom:8px;">'
                '<h5>💰 Revenue Streams</h5></div>',
                unsafe_allow_html=True,
            )
            render_bullets(canvas.get("revenue_streams", []))

            st.markdown(
                '<div style="background-color:#ffe6e6;border-radius:10px;padding:10px;margin-bottom:8px;">'
                '<h5>🧾 Cost Structure</h5></div>',
                unsafe_allow_html=True,
            )
            render_bullets(canvas.get("cost_structure", []))

        st.markdown("---")

        # -------- New row for the 2 additional blocks --------
        st.markdown("### 🌍 Social & Environmental Dimensions")

        col_b1, col_b2 = st.columns(2)

        with col_b1:
            st.markdown(
                '<div style="background-color:#e6ffe6;border-radius:10px;padding:10px;margin-bottom:8px;">'
                '<h5>✅ Social and Environmental Benefits</h5></div>',
                unsafe_allow_html=True,
            )
            render_bullets(canvas.get("Social and Environmental Benefits", []))

        with col_b2:
            st.markdown(
                '<div style="background-color:#fff0f0;border-radius:10px;padding:10px;margin-bottom:8px;">'
                '<h5>⚠️ Social and Environmental Costs</h5></div>',
                unsafe_allow_html=True,
            )
            render_bullets(canvas.get("Social and Environmental Costs", []))

        st.markdown("---")

    except Exception as e:
        st.error(f"❌ Error parsing BMC JSON: {e}")
