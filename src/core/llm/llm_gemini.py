from langchain_google_genai import ChatGoogleGenerativeAI

def llm_gemini(model="gemini-2.5-flash", temperature=0.7):
    return ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
    )