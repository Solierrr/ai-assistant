from langchain_groq import ChatGroq


def llm_groq(model="llama-3.3-70b-versatile", temperature=0.7):
    return ChatGroq(
        model=model,
        temperature=temperature,
    )
