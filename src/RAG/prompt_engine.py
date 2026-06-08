class PromptEngine:
    """Constructs strict prompt templates for the LLM based on retrieved context chunks and compliance rules."""
    
    SYSTEM_INSTRUCTIONS = """You are a compliant Mutual Fund FAQ Assistant for Groww. Your task is to answer the user query using ONLY the retrieved context.

You MUST follow these compliance rules strictly:
1. Speak strictly objectively. Never recommend any scheme, suggest investing, or offer financial advice.
2. Limit your answer to a maximum of 3 sentences.
3. Cite exactly one official source link from the context metadata (in format: [Source Name](URL)).
4. If the answer cannot be found in the context, politely refuse by saying: "I don't have that information in my verified sources" and provide a general SEBI link (https://www.sebi.gov.in).
5. Never speculate, estimate, or calculate returns.
6. Restrict your answer only to the facts directly stated in the context. Do not add outside knowledge.
"""

    @classmethod
    def build_prompt(cls, query: str, context_chunks: list[dict]) -> tuple[str, str]:
        """Builds and returns the system prompt and user prompt pair.
        
        Returns:
            tuple: (system_prompt_string, user_prompt_string)
        """
        # Format the retrieved context blocks
        formatted_blocks = []
        for idx, chunk in enumerate(context_chunks):
            doc_text = chunk.get("document", "").strip()
            meta = chunk.get("metadata", {})
            url = meta.get("url", "https://groww.in")
            title = meta.get("title", "Groww Mutual Fund Scheme")
            
            block = (
                f"Context Chunk {idx + 1}:\n"
                f"Source URL: {url}\n"
                f"Source Title: {title}\n"
                f"Content:\n{doc_text}\n"
                f"----------------------------------------"
            )
            formatted_blocks.append(block)
            
        context_str = "\n\n".join(formatted_blocks) if formatted_blocks else "NO MATCHING VERIFIED CONTEXT FOUND."
        
        system_prompt = cls.SYSTEM_INSTRUCTIONS
        
        user_prompt = (
            f"Retrieved Context:\n"
            f"========================================\n"
            f"{context_str}\n"
            f"========================================\n\n"
            f"User Query: {query}\n\n"
            f"Answer:"
        )
        
        return system_prompt, user_prompt
