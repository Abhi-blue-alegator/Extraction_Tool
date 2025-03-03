import streamlit as st
import json
from langchain_community.document_loaders import WebBaseLoader
from langchain_openai import ChatOpenAI

# Initialize session state
if "raw_content" not in st.session_state:
    st.session_state.raw_content = ""
if "extracted_info" not in st.session_state:
    st.session_state.extracted_info = None

# Streamlit UI
st.set_page_config(page_title="Healthcare Info Extractor", layout="wide")

# Sidebar for URL input
with st.sidebar:
    st.header("Configuration")
    urls = st.text_input(
        "Enter URLs (comma-separated)",
        placeholder="https://example1.com, https://example2.com"
    )
    process_urls = st.button("Scrape URLs")

# Main content area
st.title("Healthcare Professional Information Extractor")

# Process URLs when button is clicked
if process_urls and urls:
    url_list = [url.strip() for url in urls.split(",") if url.strip()]
    
    try:
        # Load and process documents
        loader = WebBaseLoader(url_list)
        docs = loader.load()
        
        # Combine all document content
        combined_content = "\n\n".join([doc.page_content for doc in docs])
        st.session_state.raw_content = combined_content
        st.sidebar.success(f"Scraped {len(docs)} pages with {len(combined_content)} characters!")
        
    except Exception as e:
        st.sidebar.error(f"Error scraping URLs: {str(e)}")

def format_for_word_doc(info):
    doc_content = []
    
    sections = [
        ("Professional Overview", "overview"),
        ("Medical Specialty", "specialty"),
        ("Clinical Expertise", "expertise"),
        ("Awards & Publications", "awards_publications"),
        ("Education & Qualifications", "qualifications"),
        ("Areas of Expertise", "areas_of_expertise"),
        ("Patient Testimonials", "patient_testimonials"),
        ("Frequently Asked Questions", "faqs")
    ]
    
    for title, key in sections:
        content = info.get(key, "Information not available")
        doc_content.append(f"{title}\n{'='*len(title)}\n")
        
        if isinstance(content, dict):  # For FAQs
            for q, a in content.items():
                doc_content.append(f"Q: {q}\nA: {a}\n")
        else:
            formatted_content = str(content).replace('\\n', '\n').replace('• ', '  • ')
            doc_content.append(formatted_content)
        
        doc_content.append("\n\n")
    
    return "\n".join(doc_content)

def extract_info():
    if not st.session_state.raw_content:
        st.error("Please scrape URLs first!")
        return
    
    try:
        # Verify secret exists
        if "openai_api_key" not in st.secrets:
            st.error("OpenAI API key not found in secrets!")
            return
            
        llm = ChatOpenAI(
            model_name="gpt-4",
            temperature=0,
            api_key=st.secrets["openai_api_key"]
        )

        extraction_prompt = f"""Extract and preserve EXACT text from these sections of the healthcare professional's website:
        {st.session_state.raw_content[:35000]}

        Return as JSON with these fields. PRESERVE ORIGINAL FORMATTING, LINE BREAKS, AND FULL TEXT:
        {{
            "overview": "Full text from 'About' section with all details",
            "specialty": "Complete specialties text with all subspecialties",
            "expertise": "Full expertise description text",
            "awards_publications": "Complete awards and publications text with all entries",
            "qualifications": "Full educational background including all degrees, certifications, and training programs",
            "areas_of_expertise": "Detailed practice areas text with all listed specialties",
            "patient_testimonials": "Complete testimonial texts with patient comments",
            "faqs": {{
                "Full question 1": "Full answer 1",
                "Full question 2": "Full answer 2"
            }}
        }}

        CRITICAL INSTRUCTIONS:
        1. Copy text verbatim without any summarization
        2. Preserve original paragraph structure and line breaks
        3. Include ALL details without exception
        4. Maintain exact wording from website including technical terms
        5. Never condense information into bullet points unless originally present
        6. Keep full certification names with issuing organizations
        7. Preserve any existing formatting like bullet points or numbering
        """

        response = llm.invoke(extraction_prompt)
        
        try:
            cleaned_response = response.content.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:-3].strip()
            info = json.loads(cleaned_response)
            st.session_state.extracted_info = info
        except Exception as e:
            st.error(f"Parsing error: {str(e)}")
            st.write("Raw response:", response.content)
        
    except Exception as e:
        st.error(f"Error extracting information: {str(e)}")

# Main extraction button
if st.button("Extract Information"):
    extract_info()

# Display results and download option
if st.session_state.extracted_info:
    formatted_output = format_for_word_doc(st.session_state.extracted_info)
    
    st.markdown("### Extracted Information (Complete Version)")
    st.markdown(f"```\n{formatted_output}\n```")
    
    st.download_button(
        label="Download as Text File",
        data=formatted_output,
        file_name="professional_profile.txt",
        mime="text/plain"
    )
