import streamlit as st
import json
from typing import Dict

st.set_page_config(page_title="Business Model Canvas — Visual", layout="wide")

CARD_STYLE = """
background: linear-gradient(180deg, #ffffff 0%, #f7f9fc 100%);
border-radius: 10px;
padding: 12px;
box-shadow: 0 2px 6px rgba(20,20,40,0.06);
border: 1px solid rgba(35,47,79,0.06);
min-height: 140px;
"""

HEADER_STYLE = "font-weight:700; font-size:16px; margin-bottom:6px;"

DEFAULT_BMC = {
    "Customer Segments": ["Who are the customers?"],
    "Value Propositions": ["What value do we deliver?"],
    "Channels": ["How do we reach customers?"],
    "Customer Relationships": ["What type of relationships?"],
    "Revenue Streams": ["How do we earn revenue?"],
    "Key Activities": ["Most important activities"],
    "Key Resources": ["Key assets & resources"],
    "Key Partners": ["Main partners & suppliers"],
    "Cost Structure": ["Major cost drivers"]
}


def render_card(title: str, items, key: str):
    st.markdown(f"<div style='{CARD_STYLE}'>", unsafe_allow_html=True)
    st.markdown(f"<div style='{HEADER_STYLE}'>{title}</div>", unsafe_allow_html=True)
    if isinstance(items, list):
        for i, it in enumerate(items):
            st.markdown(f"- {it}")
    else:
        st.markdown(str(items))
    st.markdown("</div>", unsafe_allow_html=True)


st.title("📋 Visual Business Model Canvas")
st.write("Paste a Business Model Canvas JSON on the left or use the sample. The canvas updates live.")

col_left, col_right = st.columns([1, 2])

with col_left:
    st.subheader("Input / Edit BMC")
    bmc_input = st.text_area("Paste JSON here (keys must match the 9 BMC blocks)", value=json.dumps(DEFAULT_BMC, indent=2), height=420)
    if st.button("Load sample"):
        bmc_input = json.dumps(DEFAULT_BMC, indent=2)
        st.experimental_rerun()

    download_name = st.text_input("Export filename (optional)", value="BMC_Report.txt")
    if st.button("Download as .txt"):
        try:
            data = json.loads(bmc_input)
            txt = []
            for k, v in data.items():
                txt.append(f"## {k}\n")
                if isinstance(v, list):
                    for it in v:
                        txt.append(f"- {it}\n")
                else:
                    txt.append(str(v) + "\n")
                txt.append("\n")
            st.download_button(label="Download BMC Report", data=''.join(txt), file_name=download_name, mime='text/plain')
        except Exception as e:
            st.error(f"Can't export: {e}")

with col_right:
    st.subheader("Canvas Preview")
    try:
        bmc_data = json.loads(bmc_input)
    except Exception:
        st.error("Invalid JSON — please fix the input on the left.")
        bmc_data = DEFAULT_BMC

    # Layout: Top row (Customer Segments | Value Propositions | Channels)
    r1_c1, r1_c2, r1_c3 = st.columns([1.2, 1.6, 1.0])
    with r1_c1:
        render_card("Customer Segments", bmc_data.get("Customer Segments", []), "cs")
    with r1_c2:
        render_card("Value Propositions", bmc_data.get("Value Propositions", []), "vp")
    with r1_c3:
        render_card("Channels", bmc_data.get("Channels", []), "ch")

    # Middle row (Customer Relationships | Revenue Streams)
    st.write("")
    r2_c1, r2_c2 = st.columns([1.4, 1.0])
    with r2_c1:
        render_card("Customer Relationships", bmc_data.get("Customer Relationships", []), "cr")
    with r2_c2:
        render_card("Revenue Streams", bmc_data.get("Revenue Streams", []), "rs")

    # Bottom grid: Key Activities | Key Resources | Key Partners | Cost Structure
    st.write("")
    kb1, kb2, kb3, kb4 = st.columns(4)
    with kb1:
        render_card("Key Activities", bmc_data.get("Key Activities", []), "ka")
    with kb2:
        render_card("Key Resources", bmc_data.get("Key Resources", []), "kr")
    with kb3:
        render_card("Key Partners", bmc_data.get("Key Partners", []), "kp")
    with kb4:
        render_card("Cost Structure", bmc_data.get("Cost Structure", []), "cs2")

    st.caption("Tip: Edit the JSON on the left to update the canvas. Use the Download button to export a simple text report.")


# Footer
st.markdown("---")
st.write("Built with Streamlit — adapt the layout or styles as needed.")
