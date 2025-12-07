"""
Mathematical Question Refinement Chatbot Backend
FastAPI + LangChain + OpenAI GPT + FAISS for semantic similarity
FULLY FIXED - All Dependencies Compatible
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import logging
from pathlib import Path
import os

# LangChain imports - FIXED
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

# FAISS and embeddings
import faiss
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Math Question Refinement Chatbot")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OPENAI_API_KEY = "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"
OPENAI_API_KEY = "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"
# Set environment variable for OpenAI
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

llm = None
embeddings = None
faiss_index = None
questions_data = []

# Pydantic models
class UserMessage(BaseModel):
    message: str
    session_id: Optional[str] = "default"

class ValidationResponse(BaseModel):
    is_valid: bool
    feedback: str
    next_step: str

class RefinementResponse(BaseModel):
    original_question: str
    refined_question: str
    message: str

class SimilarQuestion(BaseModel):
    id: int
    question: str
    domain: str
    subdomain: str
    similarity_score: float

class SimilarityResponse(BaseModel):
    similar_questions: List[SimilarQuestion]
    message: str

class FinalResponse(BaseModel):
    status: str
    message: str
    final_question: str
    similar_questions: List[SimilarQuestion]


# Session storage
sessions = {}


def initialize_llm():
    """Initialize LangChain LLM with OpenAI GPT"""
    global llm, embeddings
    try:
        # Initialize with your OpenAI API key
        llm = ChatOpenAI(
            model="gpt-5",
            temperature=0.3,
            api_key=OPENAI_API_KEY
        )
        logger.info("Model GPT 4")
        embeddings = OpenAIEmbeddings(
            api_key=OPENAI_API_KEY
        )
        
        logger.info("✅ LLM and Embeddings initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize LLM: {e}")
        raise


def load_questions_and_build_index():
    """Load questions from JSON and build FAISS index"""
    global questions_data, faiss_index
    
    try:
        # Load questions
        questions_file = Path("questions.json")
        with open(questions_file, 'r', encoding='utf-8') as f:
            questions_data = json.load(f)
        
        logger.info(f"✅ Loaded {len(questions_data)} questions from JSON")
        
        # Generate embeddings for all questions
        question_texts = [q['question'] for q in questions_data]
        question_embeddings = embeddings.embed_documents(question_texts)
        
        # Build FAISS index
        dimension = len(question_embeddings[0])
        faiss_index = faiss.IndexFlatIP(dimension)
        
        # Normalize embeddings for cosine similarity
        embeddings_array = np.array(question_embeddings).astype('float32')
        faiss.normalize_L2(embeddings_array)
        
        faiss_index.add(embeddings_array)
        logger.info(f"✅ FAISS index built with {faiss_index.ntotal} vectors")
        
    except Exception as e:
        logger.error(f"❌ Failed to load questions or build index: {e}")
        raise


@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup"""
    logger.info("🚀 Starting Mathematical Question Refinement Chatbot...")
    initialize_llm()
    load_questions_and_build_index()
    logger.info("✅ All systems ready!")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Math Question Refinement Chatbot",
        "endpoints": ["/validate", "/refine", "/check-similarity", "/finalize"]
    }


@app.post("/validate", response_model=ValidationResponse)
async def validate_question(user_input: UserMessage):
    """PHASE 1: Validate if the input is a mathematical question"""
    logger.info(f"📝 Validating question: {user_input.message[:50]}...")
    
    try:
        # Simple message format for ChatOpenAI
        system_msg = """You are a mathematical question validator. Your task is to determine if the given text is a valid mathematical question.

A valid mathematical question should:
1. Ask about mathematical concepts, calculations, proofs, or problem-solving
2. Be clear and understandable
3. Relate to mathematics (arithmetic, algebra, calculus, geometry, topology, analysis, etc.)
4. Have a clear question or task

Respond in this exact format:
VALID: [brief reason]
or
INVALID: [specific reason why it's not valid and what needs to be fixed]"""

        user_msg = f"Text to validate: {user_input.message}"
        
        # Create messages list
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ]
        
        # Get LLM response
        response = llm.invoke(messages)
        result = response.content.strip()
        
        logger.info(f"🔍 Validation result: {result[:100]}...")
        
        # Parse response
        if result.startswith("VALID:"):
            is_valid = True
            feedback = result.replace("VALID:", "").strip()
            next_step = "refinement"
            
            # Store in session
            if user_input.session_id not in sessions:
                sessions[user_input.session_id] = {}
            sessions[user_input.session_id]['original_question'] = user_input.message
            sessions[user_input.session_id]['status'] = 'validated'
            
        else:
            is_valid = False
            feedback = result.replace("INVALID:", "").strip()
            next_step = "revise"
        
        return ValidationResponse(
            is_valid=is_valid,
            feedback=feedback,
            next_step=next_step
        )
        
    except Exception as e:
        logger.error(f"❌ Validation error: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@app.post("/refine", response_model=RefinementResponse)
async def refine_question(user_input: UserMessage):
    """PHASE 2: Refine the validated question"""
    logger.info(f"✨ Refining question for session: {user_input.session_id}")
    
    try:
        session = sessions.get(user_input.session_id, {})
        original_question = session.get('original_question', user_input.message)
        
        # Check if user provided feedback
        refinement_context = ""
        if 'refined_question' in session and user_input.message != original_question:
            refinement_context = f"""
Previous refined version: {session['refined_question']}
User feedback: {user_input.message}

Please incorporate the user's feedback to further improve the question.
"""
        
        # Create refinement prompt
        system_msg = """You are a mathematical question editor. Your task is to refine mathematical questions for clarity, grammar, and proper formatting.

Please improve the question by:
1. Correcting any grammatical errors
2. Improving clarity and precision
3. Using proper mathematical notation and symbols
4. Ensuring the question is well-structured
5. Maintaining the original intent and difficulty level

Provide ONLY the refined question without any preamble or explanation."""

        user_msg = f"""Original question: {original_question}
{refinement_context}

Refined question:"""
        
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ]
        
        # Get LLM response
        response = llm.invoke(messages)
        refined_question = response.content.strip()
        
        logger.info(f"✅ Question refined successfully")
        
        # Update session
        sessions[user_input.session_id]['refined_question'] = refined_question
        sessions[user_input.session_id]['status'] = 'refined'
        
        return RefinementResponse(
            original_question=original_question,
            refined_question=refined_question,
            message="Question has been refined. Please review and either accept or request changes."
        )
        
    except Exception as e:
        logger.error(f"❌ Refinement error: {e}")
        raise HTTPException(status_code=500, detail=f"Refinement failed: {str(e)}")


@app.post("/check-similarity", response_model=SimilarityResponse)
async def check_similarity(user_input: UserMessage):
    """PHASE 3: Check semantic similarity using FAISS"""
    logger.info(f"🔎 Checking similarity for session: {user_input.session_id}")
    
    try:
        session = sessions.get(user_input.session_id, {})
        question_to_check = session.get('refined_question', user_input.message)
        
        # Generate embedding
        query_embedding = embeddings.embed_query(question_to_check)
        query_vector = np.array([query_embedding]).astype('float32')
        faiss.normalize_L2(query_vector)
        
        # Search
        k = min(5, faiss_index.ntotal)
        distances, indices = faiss_index.search(query_vector, k)
        
        # Filter by threshold
        similar_questions = []
        threshold = 0.80
        
        for distance, index in zip(distances[0], indices[0]):
            if distance >= threshold:
                q = questions_data[index]
                similar_questions.append(
                    SimilarQuestion(
                        id=q['id'],
                        question=q['question'],
                        domain=q['domain'],
                        subdomain=q['subdomain'],
                        similarity_score=float(distance)
                    )
                )
        
        logger.info(f"✅ Found {len(similar_questions)} similar questions")
        
        message = f"Found {len(similar_questions)} similar question(s) with >80% similarity." if similar_questions else "No highly similar questions found."
        
        return SimilarityResponse(
            similar_questions=similar_questions,
            message=message
        )
        
    except Exception as e:
        logger.error(f"❌ Similarity check error: {e}")
        raise HTTPException(status_code=500, detail=f"Similarity check failed: {str(e)}")


@app.post("/finalize", response_model=FinalResponse)
async def finalize_question(user_input: UserMessage):
    """Final step: Confirm and check duplicates"""
    logger.info(f"🎯 Finalizing question for session: {user_input.session_id}")
    
    try:
        session = sessions.get(user_input.session_id, {})
        final_question = session.get('refined_question', user_input.message)
        
        # Check similarity
        query_embedding = embeddings.embed_query(final_question)
        query_vector = np.array([query_embedding]).astype('float32')
        faiss.normalize_L2(query_vector)
        
        k = min(5, faiss_index.ntotal)
        distances, indices = faiss_index.search(query_vector, k)
        
        similar_questions = []
        threshold = 0.80
        
        for distance, index in zip(distances[0], indices[0]):
            if distance >= threshold:
                q = questions_data[index]
                similar_questions.append(
                    SimilarQuestion(
                        id=q['id'],
                        question=q['question'],
                        domain=q['domain'],
                        subdomain=q['subdomain'],
                        similarity_score=float(distance)
                    )
                )
        
        # Update session
        sessions[user_input.session_id]['status'] = 'finalized'
        sessions[user_input.session_id]['final_question'] = final_question
        
        logger.info(f"✅ Question finalized successfully")
        
        return FinalResponse(
            status="success",
            message="Your mathematical question has been successfully refined and finalized!",
            final_question=final_question,
            similar_questions=similar_questions
        )
        
    except Exception as e:
        logger.error(f"❌ Finalization error: {e}")
        raise HTTPException(status_code=500, detail=f"Finalization failed: {str(e)}")


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get current session state"""
    return sessions.get(session_id, {"message": "Session not found"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
