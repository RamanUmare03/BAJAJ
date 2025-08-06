from langchain_groq import ChatGroq
import os

# Initialize LLM
llm = ChatGroq(
    api_key=os.getenv("GROK_API_KEY"),
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    temperature=0,
)

async def process_single_query(ensemble_retriever, query: str) -> str:
    """
    Retrieves context using ensemble retriever and answers with LLM.
    """
    docs = await ensemble_retriever.ainvoke(query)
    relevant_docs = "\n\n---\n\n".join([doc.page_content for doc in docs])

    prompt_template = f"""
    You are an assistant that answers questions strictly from the provided context.
    Rules:
    - Use ONLY the given context. Do not use external knowledge.
    - Answer in ONE sentence, including all important conditions.
    - If the answer is not found, reply: "Information not available in the document."

    Context:
    {relevant_docs}

    Question:
    {query}

    *Answer:*
    """

    answer = await llm.ainvoke(prompt_template)
    return answer.content
