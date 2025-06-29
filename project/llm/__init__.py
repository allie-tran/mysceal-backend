from configs import USE_GROQ
from .models import gpt_llm_model
from .groq import groq_llm_model, small_groq_llm_model

llm_model = groq_llm_model if USE_GROQ else gpt_llm_model
small_llm_model = small_groq_llm_model
vllm_model = gpt_llm_model

