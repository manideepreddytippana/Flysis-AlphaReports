import os
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from sarvamai import SarvamAI


from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    content: str
    tokens_used: int = 0
    model: str = "sarvam-105b"
    finish_reason: str = "stop"


class SarvamAIClient:
    
    BASE_URL = "https://api.sarvam.ai"
    
    SYSTEM_PROMPTS = {
        "research": """You are Filysis Business AI, an expert academic research assistant specialized in analyzing business reports, financial documents, and scientific papers. 

Your capabilities include:
- Extracting key findings and insights from dense technical content
- Identifying trends, patterns, and anomalies in data
- Comparing methodologies and results across studies
- Generating executive summaries with actionable recommendations
- Answering specific questions with citations to source material

When responding:
1. Be precise and data-driven
2. Cite specific sections or page numbers when referencing source material
3. Structure complex analyses with clear headings and bullet points
4. Highlight uncertainty or limitations in the data
5. Use domain-appropriate terminology

Always base your answers on the provided context. If the answer is not in the context, say so clearly.""",
        
        "summary": """You are an expert summarizer for business and research documents. 

Generate structured summaries that include:
1. Executive Overview (2-3 sentences)
2. Key Findings (bullet points)
3. Methodology notes
4. Quantitative highlights
5. Implications/Recommendations

Focus on actionable insights and data-driven conclusions.""",
        
        "analysis": """You are a quantitative research analyst. Analyze the provided data and extract:
1. Key metrics and their significance
2. Trends and patterns
3. Comparative statistics
4. Risk factors
5. Growth projections

Present findings in a structured format suitable for executive decision-making."""
    }
    
    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.sarvam_api_key
        self.client = SarvamAI(
            api_subscription_key=self.api_key,
            timeout=60.0,
        )

    @staticmethod
    def _get_value(item: Any, key: str, default: Any = None) -> Any:
        if isinstance(item, dict):
            return item.get(key, default)
        return getattr(item, key, default)

    @classmethod
    def _extract_completion(cls, response: Any) -> tuple[str, int, str]:
        choices = cls._get_value(response, "choices", []) or []
        if not choices:
            return "", 0, "stop"

        first_choice = choices[0]
        message = cls._get_value(first_choice, "message", {})
        usage = cls._get_value(response, "usage", {})

        return (
            cls._get_value(message, "content", "") or "",
            cls._get_value(usage, "total_tokens", 0) or 0,
            cls._get_value(first_choice, "finish_reason", "stop") or "stop",
        )

    @classmethod
    def _extract_stream_content(cls, chunk: Any) -> str:
        choices = cls._get_value(chunk, "choices", []) or []
        if not choices:
            return ""

        first_choice = choices[0]
        delta = cls._get_value(first_choice, "delta", {})
        return cls._get_value(delta, "content", "") or ""
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "sarvam-105b",
        temperature: float = 0.3,
        max_tokens: int = 4096,
        system_prompt_type: str = "research"
    ) -> LLMResponse:
        """
        Send a chat completion request to Sarvam AI.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name to use
            temperature: Sampling temperature (lower = more focused)
            max_tokens: Maximum response length
            system_prompt_type: Type of system prompt to use
        """

        system_msg = {
            "role": "system",
            "content": self.SYSTEM_PROMPTS.get(system_prompt_type, self.SYSTEM_PROMPTS["research"])
        }
        
        all_messages = [system_msg] + messages
        
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions,
                messages=all_messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content, tokens_used, finish_reason = self._extract_completion(response)
            
            return LLMResponse(
                content=content,
                tokens_used=tokens_used,
                model=model,
                finish_reason=finish_reason
            )
        
        except Exception as e:
            logger.error(f"Sarvam API error: {e}")
            raise
    
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "sarvam-105b",
        temperature: float = 0.3,
        system_prompt_type: str = "research"
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion from Sarvam AI.
        
        Yields content chunks as they arrive.
        """
        system_msg = {
            "role": "system",
            "content": self.SYSTEM_PROMPTS.get(system_prompt_type, self.SYSTEM_PROMPTS["research"])
        }
        
        all_messages = [system_msg] + messages
        
        try:
            stream = await asyncio.to_thread(
                self.client.chat.completions,
                messages=all_messages,
                model=model,
                temperature=temperature,
                stream=True,
            )

            queue: asyncio.Queue[Any] = asyncio.Queue()
            sentinel = object()
            loop = asyncio.get_running_loop()

            def _produce() -> None:
                try:
                    for chunk in stream:
                        content = self._extract_stream_content(chunk)
                        if content:
                            loop.call_soon_threadsafe(queue.put_nowait, content)
                except Exception as exc:
                    logger.error(f"Sarvam streaming error: {exc}")
                    loop.call_soon_threadsafe(queue.put_nowait, f"\n[Error: {str(exc)}]")
                finally:
                    loop.call_soon_threadsafe(queue.put_nowait, sentinel)

            producer_task = asyncio.create_task(asyncio.to_thread(_produce))

            while True:
                item = await queue.get()
                if item is sentinel:
                    break
                yield item

            await producer_task
        
        except Exception as e:
            logger.error(f"Sarvam streaming error: {e}")
            yield f"\n[Error: {str(e)}]"
    
    async def summarize(
        self,
        text: str,
        style: str = "detailed",
        focus_area: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a structured summary of document content.
        
        Args:
            text: Document text to summarize
            style: 'brief', 'detailed', or 'executive'
            focus_area: Optional area to focus on
        """
        style_instructions = {
            "brief": "Provide a concise 1-paragraph summary highlighting only the most critical points.",
            "detailed": "Provide a comprehensive summary with all key findings, methodology, and implications.",
            "executive": "Provide a C-suite focused summary emphasizing business impact, ROI, and strategic recommendations."
        }
        
        focus_text = f"\n\nSpecial focus area: {focus_area}" if focus_area else ""
        
        prompt = f"""Please summarize the following document.

Style: {style_instructions.get(style, style_instructions['detailed'])}{focus_text}

Document content:
{text[:15000]}  # Limit input to manage token usage

Please provide your response in this JSON format:
{{
    "summary": "Overall summary paragraph",
    "sections": [
        {{"title": "Section name", "content": "Section summary"}}
    ],
    "key_metrics": [
        {{"name": "Metric name", "value": "Value", "significance": "Why it matters"}}
    ],
    "recommendations": ["Rec 1", "Rec 2"]
}}"""
        
        messages = [{"role": "user", "content": prompt}]
        
        try:
            response = await self.chat(
                messages=messages,
                system_prompt_type="summary",
                temperature=0.2,
                max_tokens=4096
            )
            
            # Try to parse JSON from response
            content = response.content
            # Extract JSON if wrapped in code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            try:
                parsed = json.loads(content.strip())
                return {
                    "summary": parsed.get("summary", response.content),
                    "sections": parsed.get("sections", []),
                    "key_metrics": parsed.get("key_metrics", []),
                    "recommendations": parsed.get("recommendations", []),
                    "tokens_used": response.tokens_used
                }
            except json.JSONDecodeError:
                # Return raw content if JSON parsing fails
                return {
                    "summary": response.content,
                    "sections": [],
                    "key_metrics": [],
                    "recommendations": [],
                    "tokens_used": response.tokens_used
                }
        
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return {
                "summary": f"Error generating summary: {str(e)}",
                "sections": [],
                "key_metrics": [],
                "recommendations": [],
                "tokens_used": 0
            }
    
    async def analyze_quantitative(
        self,
        text: str,
        table_data: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Perform quantitative analysis on extracted data.
        
        Args:
            text: Context text from the document
            table_data: Optional structured table data
        """
        table_context = ""
        if table_data:
            table_context = "\n\nExtracted Tables:\n"
            for i, table in enumerate(table_data[:5]):  # Limit tables
                table_context += f"\nTable {i+1} (Page {table.get('page', 'N/A')}):\n"
                for row in table.get('data', [])[:20]:  # Limit rows
                    table_context += " | ".join(str(cell) for cell in row) + "\n"
        
        prompt = f"""Analyze the following quantitative data and provide insights.

Document Context:
{text[:8000]}
{table_context}

Please provide:
1. Key quantitative findings
2. Statistical highlights
3. Trend analysis
4. Comparative metrics
5. Risk assessment
6. Growth/projections if applicable

Respond in JSON format:
{{
    "analysis": "Overall analysis paragraph",
    "key_findings": ["finding 1", "finding 2"],
    "statistics": [{{"metric": "name", "value": "value", "context": "significance"}}],
    "trends": [{{"description": "trend", "direction": "up/down/stable", "confidence": "high/medium/low"}}],
    "risks": ["risk 1", "risk 2"],
    "recommendations": ["rec 1", "rec 2"]
}}"""
        
        messages = [{"role": "user", "content": prompt}]
        
        try:
            response = await self.chat(
                messages=messages,
                system_prompt_type="analysis",
                temperature=0.2,
                max_tokens=4096
            )
            
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            try:
                return json.loads(content.strip())
            except json.JSONDecodeError:
                return {"analysis": response.content, "raw_response": True}
        
        except Exception as e:
            logger.error(f"Quantitative analysis failed: {e}")
            return {"analysis": f"Error: {str(e)}", "error": True}


class RAGPipeline:
    """Retrieval-Augmented Generation pipeline using pgvector."""
    
    def __init__(self, vector_store, llm_client: SarvamAIClient):
        self.vector_store = vector_store
        self.llm = llm_client
    
    async def query(
        self,
        db,
        doc_id: int,
        question: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Execute RAG query: retrieve relevant chunks then generate answer.
        
        Args:
            db: SQLAlchemy database session
            doc_id: Document database ID (integer)
            question: User question
            top_k: Number of chunks to retrieve
        """
        start_time = asyncio.get_event_loop().time()
        
        chunks = await self.vector_store.search(db, doc_id, question, top_k=top_k)
        
        if not chunks:
            return {
                "answer": "I couldn't find relevant information in the document to answer your question. "
                         "Please try rephrasing or ask about a different topic.",
                "sources": [],
                "tokens_used": 0,
                "latency_ms": 0
            }
        
        context_parts = []
        for i, chunk in enumerate(chunks):
            context_parts.append(
                f"[Source {i+1}, Page {chunk.get('page', 'N/A')}]: {chunk['chunk']}"
            )
        
        context = "\n\n".join(context_parts)
        
        messages = [{
            "role": "user",
            "content": f"""Based on the following experts from a document, please answer the question.

Document excerpts:
{context}

Question: {question}

Please provide a comprehensive answer based on the document content. Cite the source numbers [Source N] when referencing specific information. If the answer isn't in the provided context, say so clearly."""
        }]
        
        llm_response = await self.llm.chat(messages, temperature=0.3)
        
        latency_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
        
        return {
            "answer": llm_response.content,
            "sources": [
                {
                    "page": c.get("page"),
                    "text_preview": c["chunk"][:200] + "...",
                    "relevance_score": c.get("score", 0)
                }
                for c in chunks
            ],
            "tokens_used": llm_response.tokens_used,
            "latency_ms": latency_ms
        }
