import time
import logging
from typing import List, Dict, Any, Tuple
from app.config import settings
from app.core.vector_store import vector_store_manager
from app.core.llm_provider import llm_provider, LLMProviderError
from app.models.schemas import SourceReference

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are DocuIntel AI, an elite and authoritative Document Intelligence Research Assistant.
Your sole mission is to analyze, synthesize, and answer questions STRICTLY based on the provided context retrieved from uploaded documents.

CRITICAL OPERATIONAL RULES:
1. GROUNDING & FIDELITY: You must answer ONLY using information directly mentioned in the provided Context. Do NOT use prior knowledge, speculation, or unverified assumptions.
2. ABSOLUTE REJECTION RULE: If the provided Context does not contain the answer, or if the context is insufficient or irrelevant, you MUST respond EXACTLY with this sentence:
"I couldn't find this information in the uploaded documents. Please upload a relevant document or ask a question related to the available knowledge base."
Do not attempt to answer partially or creatively if the facts are missing.
3. NO HALLUCINATIONS: Never fabricate citations, page numbers, statistics, names, or quotes.
4. STRUCTURED RESPONSE FORMAT: When the information IS present in the context, format your answer clearly with the following sections:
   - **Direct Answer**: A direct, crisp 1-2 sentence answer to the user's question.
   - **Detailed Explanation**: Thorough explanation synthesizing the details found in the documents.
   - **Key Takeaways / Highlights**: Bulleted list of the most critical facts, numbers, or rules from the context.
   - **Source Attribution**: Specify the document filename and page/section where this information was retrieved.

FEW-SHOT EXAMPLES:

--- Example 1 (Supported Question) ---
Context:
[Doc: Cybersecurity_Policy_2024.pdf, Page: 4]
"All employees must update passwords every 90 days. Passwords must be at least 14 characters long and include an uppercase letter, a number, and a special symbol. MFA is mandatory for all remote access logins."

User Question: What is the company password policy and is MFA required?

Assistant:
**Direct Answer**:
Employees must update passwords every 90 days with a minimum length of 14 characters, and Multi-Factor Authentication (MFA) is strictly mandatory for all remote logins.

**Detailed Explanation**:
According to the company policy, passwords require complexity including uppercase characters, numbers, and special symbols, and must be rotated quarterly (every 90 days). In addition, remote access requires mandatory MFA enforcement.

**Key Takeaways / Highlights**:
- Password rotation cycle: Every 90 days
- Minimum length: 14 characters (with uppercase, number, symbol)
- MFA: Required for all remote access connections

**Source Attribution**:
* Cybersecurity_Policy_2024.pdf (Page 4)

--- Example 2 (Unsupported Question - Rejection) ---
Context:
[Doc: Annual_Financial_Report.pdf, Page: 12]
"The company achieved a 15% revenue increase in Q3 2023, driven primarily by enterprise software subscriptions."

User Question: Who is the Chief Executive Officer of the company?

Assistant:
I couldn't find this information in the uploaded documents. Please upload a relevant document or ask a question related to the available knowledge base.
"""

USER_PROMPT_TEMPLATE = """CONTEXT FROM UPLOADED DOCUMENTS:
----------------------------------------
{context_block}
----------------------------------------

CURRENT USER QUESTION:
{question}

Provide your structured answer strictly following the operational guidelines."""

class RAGPipeline:
    """
    Orchestrates the full end-to-end RAG pipeline:
    Query -> Semantic Retrieval -> Context Assembly -> LLM Grounded Generation -> Source Citation.
    """

    def __init__(self):
        self.vector_store = vector_store_manager
        self.llm = llm_provider

    def query(
        self,
        question: str,
        conversation_history: List[Dict[str, str]] = None,
        top_k: int = None
    ) -> Dict[str, Any]:
        """
        Executes a RAG query:
        1. Checks knowledge base status
        2. Retrieves top-k semantically relevant chunks
        3. If no chunks pass threshold, returns standard refusal
        4. Synthesizes context with metadata
        5. Calls LLM with few-shot grounding prompt
        6. Returns structured answer and verified source citations
        """
        start_time = time.time()
        
        # Check if vector store has any documents
        stats = self.vector_store.get_stats()
        if stats["total_documents"] == 0 or stats["total_chunks"] == 0:
            return {
                "answer": "No documents have been uploaded to the knowledge base yet. Please upload a PDF, DOCX, or TXT document using the upload panel to begin asking questions.",
                "sources": [],
                "retrieved_chunks_count": 0,
                "latency_ms": round((time.time() - start_time) * 1000, 2),
                "model_used": "none",
                "provider_used": settings.LLM_PROVIDER
            }

        # Step 1: Semantic Retrieval
        retrieved_chunks = self.vector_store.similarity_search(
            query=question,
            top_k=top_k or settings.TOP_K_RETRIEVAL,
            score_threshold=settings.SIMILARITY_THRESHOLD
        )

        # Fallback if no relevant chunks meet the similarity threshold
        if not retrieved_chunks:
            return {
                "answer": "I couldn't find this information in the uploaded documents. Please upload a relevant document or ask a question related to the available knowledge base.",
                "sources": [],
                "retrieved_chunks_count": 0,
                "latency_ms": round((time.time() - start_time) * 1000, 2),
                "model_used": self.llm.gemini_model if self.llm.provider == "gemini" else self.llm.openai_model,
                "provider_used": self.llm.provider
            }

        # Step 2: Build Structured Context Block
        context_parts = []
        sources_list: List[SourceReference] = []

        for idx, chunk in enumerate(retrieved_chunks, 1):
            doc_name = chunk.get("filename", "Unknown Document")
            page_num = chunk.get("page", 1)
            score = chunk.get("score", 0.0)
            text = chunk.get("text", "")

            context_parts.append(
                f"[Source {idx} | File: {doc_name} | Page: {page_num} | Relevance: {score:.2f}]\n{text}"
            )

            # Create clean source reference object
            snippet = text[:250] + "..." if len(text) > 250 else text
            sources_list.append(SourceReference(
                document_id=chunk.get("document_id", ""),
                filename=doc_name,
                page=page_num,
                chunk_index=chunk.get("chunk_index", 0),
                score=score,
                snippet=snippet
            ))

        context_block = "\n\n".join(context_parts)
        user_prompt = USER_PROMPT_TEMPLATE.format(
            context_block=context_block,
            question=question
        )

        # Step 3: LLM Generation
        model_name = self.llm.gemini_model if self.llm.provider == "gemini" else self.llm.openai_model
        
        try:
            answer_text = self.llm.generate_response(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                conversation_history=conversation_history,
                temperature=0.15
            )
        except LLMProviderError as e:
            # Re-raise to let API handler return proper HTTP status or friendly explanation
            raise e

        latency_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "answer": answer_text,
            "sources": sources_list,
            "retrieved_chunks_count": len(retrieved_chunks),
            "latency_ms": latency_ms,
            "model_used": model_name,
            "provider_used": self.llm.provider
        }

# Global singleton
rag_pipeline = RAGPipeline()
