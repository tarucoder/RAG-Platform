import re
from src.infrastructure.config import Config
from src.infrastructure.logger import logger
from src.RAG.retriever import Retriever
from src.RAG.prompt_engine import PromptEngine

class Generator:
    """Orchestrates retrieved context chunks and invokes the LLM under strict compliance guardrails."""
    
    def __init__(self):
        self.retriever = Retriever()
        self.model_name = Config.GROQ_MODEL
        self.api_key = Config.GROQ_API_KEY
        self.use_mock = False
        
        if not self.api_key:
            logger.warning(
                "GROQ_API_KEY is not configured in environment/.env. "
                "The pipeline will gracefully operate in offline local Mock Mode."
            )
            self.use_mock = True
        else:
            try:
                # Load Groq dynamically
                # pyrefly: ignore [missing-import]
                from groq import Groq
                self.client = Groq(api_key=self.api_key)
                logger.info(f"Initialized Groq client using model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Groq client: {e}. Falling back to local Mock Mode.")
                self.use_mock = True

    def _generate_mock_answer(self, query: str, context_chunks: list[dict]) -> str:
        """Extracts facts from context chunks to construct a compliant mock response."""
        top_chunk = context_chunks[0]
        doc_text = top_chunk.get("document", "")
        
        # Split document text into paragraphs first, then sentences
        raw_sentences = []
        for paragraph in doc_text.split("\n"):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            p_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', paragraph) if s.strip()]
            raw_sentences.extend(p_sentences)
            
        sentences = []
        for s in raw_sentences:
            # Clean leading markdown symbols like headers and bullet points
            cleaned = re.sub(r'^[#\-\*\s\d\.\)]+', '', s).strip()
            # Skip if it is empty or is a standalone link pattern
            if cleaned and not (cleaned.startswith("[") and cleaned.endswith(")")):
                sentences.append(cleaned)
        
        # Look for sentences containing query keywords
        query_words = [w.lower() for w in re.findall(r'\w+', query) if len(w) > 3]
        
        # Priority terms to boost keyword scores
        priority_terms = {
            "exit", "load", "expense", "ratio", "tax", "aum", "manager", 
            "lock", "sip", "lumpsum", "objective", "benchmark", "nav", 
            "returns", "growth", "risk", "fee", "charge", "commission"
        }
        priority_query_words = [w for w in query_words if w in priority_terms]
        
        scored_sentences = []
        for s in sentences:
            if "|" in s or "---" in s:
                continue
            s_lower = s.lower()
            
            # Calculate match density
            matches = sum(1 for qw in query_words if qw in s_lower)
            if matches > 0:
                priority_matches = sum(2 for pqw in priority_query_words if pqw in s_lower)
                score = matches + priority_matches
                scored_sentences.append((score, s))
                
        # Sort sentences by match score descending
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        matched_sentences = [s for score, s in scored_sentences]
        
        # Fallback to first two sentences if no direct keyword match
        if not matched_sentences:
            matched_sentences = [s for s in sentences[:2] if "|" not in s and "---" not in s]
            
        selected = matched_sentences[:2]
        base_answer = " ".join(selected)
        
        url = top_chunk.get("metadata", {}).get("url", "https://groww.in")
        base_answer += f" Please check the [official scheme page]({url}) for detailed information."
        
        return base_answer

    def _validate_and_sanitize_response(self, answer: str, context_chunks: list[dict]) -> str:
        """Enforces strict constraints: max 3 sentences, exactly one citation URL from the context."""
        if not context_chunks:
            # Return SEBI refusal
            return "I don't have that information in my verified sources. Please refer to the [SEBI guidelines](https://www.sebi.gov.in)."
            
        citation_url = context_chunks[0].get("metadata", {}).get("url", "https://groww.in")
            
        # 1. Truncate to maximum 3 sentences
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', answer) if s.strip()]
        if len(sentences) > 3:
            logger.warning(f"Response exceeded 3 sentences ({len(sentences)}). Truncating.")
            answer = " ".join(sentences[:3])
            
        # 2. Check for markdown citation links [label](url)
        links = re.findall(r'\[([^\]]+)\]\((https?://[^\)]+)\)', answer)
        
        if not links:
            logger.warning("Response did not contain a citation link. Appending one.")
            if answer.endswith("."):
                answer = answer[:-1]
            answer += f" (Source: [official document]({citation_url}))."
        elif len(links) > 1:
            logger.warning(f"Response contained multiple links ({len(links)}). Sanitizing.")
            # Convert extra links to plain text labels
            first_link_found = False
            
            def replace_link(match):
                nonlocal first_link_found
                label, url = match.group(1), match.group(2)
                if not first_link_found:
                    first_link_found = True
                    return match.group(0)
                else:
                    return label
                    
            answer = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', replace_link, answer)
            
        return answer

    def generate(self, query: str) -> dict:
        """Generates RAG response conforming to all structural compliance guardrails."""
        # Step 1: Retrieve context chunks
        context_chunks = self.retriever.retrieve(query)
        
        # Step 2: Handle out-of-domain queries
        if not context_chunks:
            logger.info("Out-of-domain query detected. Returning standard SEBI refusal.")
            refusal_text = "I don't have that information in my verified sources. For official guidelines, please refer to the [SEBI website](https://www.sebi.gov.in)."
            return {
                "answer": refusal_text,
                "source": "https://www.sebi.gov.in",
                "last_updated": "01 Jun '26"
            }
            
        # Step 3: Construct prompts
        system_prompt, user_prompt = PromptEngine.build_prompt(query, context_chunks)
        
        # Step 4: Invoke live LLM or mock generator
        if self.use_mock:
            logger.info("Generating response in local Mock Mode...")
            raw_answer = self._generate_mock_answer(query, context_chunks)
        else:
            try:
                logger.info("Generating response using Groq API...")
                chat_completion = self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    model=self.model_name,
                    temperature=0.0,
                    max_tokens=256
                )
                raw_answer = chat_completion.choices[0].message.content
            except Exception as e:
                logger.error(f"Groq API call failed: {e}. Falling back to local Mock Mode.")
                raw_answer = self._generate_mock_answer(query, context_chunks)
                
        # Step 5: Validate and sanitize output
        sanitized_answer = self._validate_and_sanitize_response(raw_answer, context_chunks)
        
        # Extract metadata info
        top_meta = context_chunks[0].get("metadata", {})
        source_url = top_meta.get("url", "https://groww.in")
        
        return {
            "answer": sanitized_answer,
            "source": source_url,
            "last_updated": "01 Jun '26"
        }
