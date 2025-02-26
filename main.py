import streamlit as st
import pdfplumber
import PyPDF2
from gtts import gTTS
import os
from pathlib import Path
import time
from deep_translator import GoogleTranslator
import torch
from transformers import pipeline
import tempfile

# Run the application using Streamlit: streamlit run main.py

# Set page configuration
st.set_page_config(
    page_title="PDF Voice - Modern PDF to Speech Converter",
    page_icon="🔊",
    layout="wide"
)

# Custom CSS for modern UI
st.markdown("""
    <style>
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .main {
        background-color: #f5f5f5;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        padding: 15px 32px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    </style>
""", unsafe_allow_html=True)

class PDFVoiceConverter:
    def __init__(self):
        self.supported_languages = {
            'English': 'en', 'Spanish': 'es', 'French': 'fr',
            'German': 'de', 'Italian': 'it', 'Portuguese': 'pt',
            'Russian': 'ru', 'Japanese': 'ja', 'Korean': 'ko',
            'Chinese': 'zh-cn'
        }
        
        # Initialize text-to-speech model
        if torch.cuda.is_available():
            self.tts_model = pipeline("text-to-speech", "microsoft/speecht5_tts")
        
    def get_pdf_pages_count(self, pdf_file):
        """Get total number of pages in PDF"""
        with pdfplumber.open(pdf_file) as pdf:
            return len(pdf.pages)

    def extract_text_from_pdf(self, pdf_file, start_page=None, end_page=None):
        """Extract text from PDF with page range support"""
        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            # Adjust page numbers to 0-based index
            start = (start_page - 1) if start_page else 0
            end = end_page if end_page else len(pdf.pages)
            
            # Ensure page ranges are valid
            start = max(0, start)
            end = min(len(pdf.pages), end)
            
            # Extract text from selected pages
            for page_num in range(start, end):
                page = pdf.pages[page_num]
                text += (page.extract_text() or "") + "\n"
        return text.strip()

    def translate_text(self, text, target_lang):
        translator = GoogleTranslator(source='auto', target=target_lang)
        return translator.translate(text)

    def convert_to_speech(self, text, language='en'):
        try:
            # Create temporary directory for audio files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir) / "output.mp3"
                
                if torch.cuda.is_available():
                    # Use advanced TTS model if GPU is available
                    speech = self.tts_model(text)
                    with open(temp_path, "wb") as f:
                        f.write(speech["audio"])
                else:
                    # Fallback to gTTS if no GPU
                    tts = gTTS(text=text, lang=language, slow=False)
                    tts.save(str(temp_path))
                
                with open(temp_path, "rb") as f:
                    audio_bytes = f.read()
                
                return audio_bytes
        except Exception as e:
            st.error(f"Error in speech conversion: {str(e)}")
            return None

def main():
    converter = PDFVoiceConverter()
    
    # Header
    st.title("🎧 PDF Voice Converter")
    st.markdown("### Transform your PDFs into natural speech with advanced AI")
    
    # Sidebar configuration
    with st.sidebar:
        st.header("Settings")
        target_language = st.selectbox(
            "Select Output Language",
            options=list(converter.supported_languages.keys())
        )
        
        voice_speed = st.slider(
            "Speech Rate",
            min_value=0.5,
            max_value=2.0,
            value=1.0,
            step=0.1
        )
        
        st.markdown("---")
        st.markdown("### About")
        st.markdown("""
        This app uses advanced AI to convert PDF documents into natural-sounding speech.
        Features:
        - Multiple language support
        - Page range selection
        - Advanced text processing
        - Neural TTS (when GPU available)
        - Adjustable speech rate
        """)

    # Main content
    uploaded_file = st.file_uploader(
        "Upload your PDF file",
        type="pdf",
        help="Upload a PDF file to convert to speech"
    )

    if uploaded_file is not None:
        # Get total pages
        total_pages = converter.get_pdf_pages_count(uploaded_file)
        st.info(f"PDF has {total_pages} pages")

        # Page range selection
        col1, col2 = st.columns(2)
        with col1:
            start_page = st.number_input(
                "Start Page",
                min_value=1,
                max_value=total_pages,
                value=1
            )
        with col2:
            end_page = st.number_input(
                "End Page",
                min_value=start_page,
                max_value=total_pages,
                value=min(start_page + 4, total_pages)
            )

        # Process button
        if st.button("Convert to Speech"):
            with st.spinner(f"Processing pages {start_page} to {end_page}..."):
                # Create progress bar
                progress_bar = st.progress(0)
                
                # Extract text with page range
                text = converter.extract_text_from_pdf(
                    uploaded_file,
                    start_page,
                    end_page
                )
                progress_bar.progress(33)
                
                # Translate if needed
                if target_language != "English":
                    text = converter.translate_text(
                        text,
                        converter.supported_languages[target_language]
                    )
                progress_bar.progress(66)
                
                # Convert to speech
                audio_bytes = converter.convert_to_speech(
                    text,
                    converter.supported_languages[target_language]
                )
                progress_bar.progress(100)
                
                if audio_bytes:
                    st.success("Conversion completed successfully!")
                    
                    # Display text content
                    with st.expander("Show extracted text"):
                        st.markdown(text)
                    
                    # Audio player
                    st.audio(audio_bytes, format='audio/mp3')
                    
                    # Download button with page range in filename
                    st.download_button(
                        label="Download Audio",
                        data=audio_bytes,
                        file_name=f"pdf_audio_pages_{start_page}-{end_page}.mp3",
                        mime="audio/mp3"
                    )

if __name__ == "__main__":
    main()
