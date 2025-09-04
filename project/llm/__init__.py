from configs import USE_GROQ

# from .models import gpt_llm_model
from .gemini import gemini, get_visual_content
from .groq import groq_llm_model, small_groq_llm_model

llm_model = groq_llm_model if USE_GROQ else gemini
small_llm_model = small_groq_llm_model
vllm_model = gemini

