# Step 1. Import Libraries

import streamlit as st
import pdfplumber
import pandas as pd
from io import BytesIO
import time
import ollama
import re

# Step 2. Configure Streamlit Page
st.set_page_config(
    page_title="Financial Document Q&A Assistant",
    page_icon="📊",
    layout="wide"
)

# Step 3. Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "processed_text" not in st.session_state:
    st.session_state.processed_text = ""
if "metrics" not in st.session_state:
    st.session_state.metrics = {}

# Step 4. Display App Title
st.title("📊 Financial Document Q&A Assistant")




# Step 5. Define Helper Functions
def extract_text_from_pdf(uploaded_file):
    text = ""
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except Exception as e:
        st.error(f"Error processing PDF: {e}")
        return None

def extract_text_from_excel(uploaded_file):
    text = ""
    try:
        excel_file = pd.ExcelFile(BytesIO(uploaded_file.read()))
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            text += f"\n--- Sheet: '{sheet_name}' ---\n"
            text += df.to_string(index=False) + "\n"
        return text
    except Exception as e:
        st.error(f"Error processing Excel file: {e}")
        return None

def is_financial_document(text):
    keywords = ['assets', 'liabilities', 'equity', 'revenue', 'expenses']
    return any(keyword in text.lower() for keyword in keywords)

def extract_key_metrics(text):
    metrics = {}
    patterns = {
        'Total Assets': r'Total Assets.*?\$([\d,]+)',
        'Total Current Liabilities': r'Total Current Liabilities.*?\$([\d,]+)',
        'Retained Earnings': r'Retained Earnings.*?\$([\d,]+)',
        'Net Property, Plant, and Equipment': r'Property, Plant, and Equipment.*?\$([\d,]+).*?Accumulated Depreciation.*?\$[\(\d,]+'
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            metrics[key] = match.group(1).replace(',', '')
    return metrics



# Step 6. Sidebar – Upload & Process Documents
with st.sidebar:
    st.header("📁 Upload Documents")
    st.write("Upload financial statements in PDF or Excel format.")
    uploaded_files = st.file_uploader(
        "Choose files",
        type=['pdf', 'xlsx'],
        accept_multiple_files=True,
        help="Select one or more PDF or Excel files to process."
    )
    process_btn = st.button("🚀 Process Documents", type="primary")

    if process_btn and uploaded_files:
        with st.spinner("Processing documents..."):
            all_extracted_text = ""
            for file in uploaded_files:
                st.write(f"Processing {file.name}...")
                if file.type == "application/pdf":
                    extracted_text = extract_text_from_pdf(file)
                elif file.type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                    extracted_text = extract_text_from_excel(file)
                else:
                    extracted_text = None
                if extracted_text and is_financial_document(extracted_text):
                    all_extracted_text += f"\n--- {file.name} ---\n{extracted_text}\n"
                else:
                    st.warning(f"File {file.name} does not appear to be a financial document.streamlit run app.py")
            if all_extracted_text:
                st.session_state.processed_text = all_extracted_text
                st.session_state.metrics = extract_key_metrics(all_extracted_text)
                st.success("✅ Documents processed successfully!")
                with st.expander("📋 Preview Extracted Text"):
                    st.text_area("Extracted Content",
                                 st.session_state.processed_text[:2000] + "..." if len(
                                     st.session_state.processed_text) > 2000 else st.session_state.processed_text,
                                 height=200)
                with st.expander("📊 Extracted Metrics"):
                    st.write(st.session_state.metrics)
            else:
                st.error("❌ Failed to extract text from the documents.")



# Step 7. Chat Interface – Q&A with Documents
st.header("💬 Chat with Your Documents")
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a question about your financial documents..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        if not st.session_state.processed_text:
            full_response = "Please upload and process documents first before asking questions."
        else:
            try:
                response = ollama.generate(
                    model='llama3',
                    prompt=f"Context: {st.session_state.processed_text}\n\nQuestion: {prompt}\nAnswer concisely based on the context."
                )
                full_response = response['response']
            except Exception as e:
                full_response = f"Error querying LLM: {e}"
        for chunk in full_response.split():
            full_response += chunk + " "
            time.sleep(0.05)
            message_placeholder.markdown(full_response + "▌")
        if 'Error' in full_response:
            st.error(full_response)
        else:
            message_placeholder.markdown(full_response)
    st.session_state.messages.append({"role": "assistant", "content": full_response})