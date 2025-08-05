"""
AI Chat API endpoints for real-time communication with frontend
Handles chat messages, product search, and real-time responses
"""

from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
import json
import asyncio
import logging
from sse_starlette.sse import EventSourceResponse

from infinitum.infrastructure.web.middleware.auth_middleware import get_current_user, get_optional_user
from ....external.ai.vertex_ai_client import ask_gemini
from ....external.search.semantic_search_client import semantic_search_service
from ....external.ai.vector_search_service import vector_search_service
from infinitum.infrastructure.persistence.firestore_client import db
from infinitum.infrastructure.monitoring.logging.config import get_agent_logger

logger = get_agent_logger("ai_chat")
router = APIRouter()

# Pydantic models for request/response
class ChatMessage(BaseModel):
    """Chat message model"""
    id: Optional[str] = None
    type: str = Field(..., description="Message type: 'user' or 'ai'")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

class ChatRequest(BaseModel):
    """Chat request model"""
    message: str = Field(..., description="User message", min_length=1, max_length=1000)
    conversation_id: Optional[str] = None
    user_context: Optional[Dict[str, Any]] = None

class ProductSearchResult(BaseModel):
    """Product search result model"""
    id: str
    name: str
    category: str
    brand: str
    price: str
    original_price: Optional[str] = None
    discount: Optional[int] = None
    rating: float
    review_count: int
    image: str
    tags: List[str]
    similarity_score: Optional[float] = None

class BundleResult(BaseModel):
    """Bundle result model"""
    id: str
    name: str
    category: str
    description: str
    bundle_type: str
    products: List[ProductSearchResult]
    total_price: str
    original_price: str
    discount: int
    savings: str
    features: List[str]

class ChatResponse(BaseModel):
    """Chat response model"""
    message: ChatMessage
    products: List[ProductSearchResult] = []
    bundles: List[BundleResult] = []
    suggestions: List[str] = []
    search_metadata: Optional[Dict[str, Any]] = None

class ConnectionManager:
    """WebSocket connection manager for real-time chat"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a new WebSocket"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"WebSocket connected for user: {user_id}")
    
    def disconnect(self, user_id: str):
        """Disconnect WebSocket"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"WebSocket disconnected for user: {user_id}")
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to specific user"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message to {user_id}: {e}")
                self.disconnect(user_id)

# Global connection manager
manager = ConnectionManager()

async def process_ai_search(query: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Process AI search query and return results
    
    Args:
        query: User search query
        user_context: Optional user context for personalization
        
    Returns:
        Dict containing search results and AI response
    """
    try:
        logger.info(f"Processing AI search for query: '{query}'")
        
        # Use enhanced vector search for better results
        search_result = await semantic_search_service.enhanced_vector_search(
            user_query=query,
            user_context=user_context,
            limit=20,
            use_hybrid=True
        )
        
        # Generate AI response based on search results
        ai_prompt = f"""
        User is searching for: "{query}"
        
        Found {search_result['total_found']} products.
        
        Provide a helpful, conversational response about the search results.
        Be specific about what was found and offer suggestions.
        Keep the response under 200 words and friendly in tone.
        """
        
        ai_response = ask_gemini(ai_prompt)
        
        # Convert search results to frontend format with proper validation
        products = []
        for result in search_result.get('results', []):
            try:
                content = result.get('content', {})
                if not content or not isinstance(content, dict):
                    logger.warning(f"Invalid content structure for result {result.get('id', 'unknown')}")
                    continue
                    
                product = ProductSearchResult(
                    id=str(result.get('id', 'unknown')),
                    name=str(content.get('title', 'Unknown Product')),
                    category=str(content.get('category', 'General')),
                    brand=str(content.get('brand', 'Unknown')),
                    price=str(content.get('price', '0')),
                    original_price=str(content.get('original_price')) if content.get('original_price') else None,
                    discount=int(content.get('discount', 0)) if content.get('discount') else None,
                    rating=float(content.get('rating', 4.0)),
                    review_count=int(content.get('review_count', 0)),
                    image=str(content.get('image', '')),
                    tags=list(content.get('tags', [])) if isinstance(content.get('tags'), list) else [],
                    similarity_score=float(result.get('score', 0.0))
                )
                products.append(product)
            except (ValueError, TypeError) as e:
                logger.error(f"Failed to parse product result {result.get('id', 'unknown')}: {e}")
                continue
        
        return {
            'ai_response': ai_response,
            'products': products,
            'bundles': [],  # TODO: Implement bundle search
            'suggestions': search_result.get('suggestions', []),
            'search_metadata': search_result.get('search_metadata', {})
        }
        
    except Exception as e:
        logger.error(f"AI search processing failed: {e}")
        return {
            'ai_response': f"I encountered an issue while searching for '{query}'. Please try a different search term or try again later.",
            'products': [],
            'bundles': [],
            'suggestions': ["Try a more specific search", "Check your spelling", "Browse categories"],
            'search_metadata': {'error': str(e)}
        }

@router.post("/chat", response_model=ChatResponse)
async def send_chat_message(
    request: ChatRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """
    Send a chat message and get AI response with product search
    
    Args:
        request: Chat request with message and context
        current_user: Optional authenticated user
        
    Returns:
        ChatResponse with AI message and search results
    """
    try:
        logger.info(f"Chat message received: '{request.message[:100]}...'")
        
        # Create user message
        user_message = ChatMessage(
            id=f"user_{int(datetime.now().timestamp() * 1000)}",
            type="user",
            content=request.message,
            timestamp=datetime.now()
        )
        
        # Process AI search
        search_results = await process_ai_search(
            query=request.message,
            user_context=request.user_context
        )
        
        # Create AI response message
        ai_message = ChatMessage(
            id=f"ai_{int(datetime.now().timestamp() * 1000)}",
            type="ai",
            content=search_results['ai_response'],
            timestamp=datetime.now(),
            metadata={
                'products_found': len(search_results['products']),
                'search_metadata': search_results['search_metadata']
            }
        )
        
        # Save conversation to Firestore if user is authenticated
        if current_user:
            try:
                conversation_data = {
                    'user_id': current_user['uid'],
                    'conversation_id': request.conversation_id or f"conv_{int(datetime.now().timestamp())}",
                    'messages': [user_message.dict(), ai_message.dict()],
                    'products_found': len(search_results['products']),
                    'timestamp': datetime.now().isoformat(),
                    'query': request.message[:500]  # Limit query length for storage
                }
                
                # Add with retry logic for quota limits
                try:
                    db.collection('conversations').add(conversation_data)
                    logger.info(f"Conversation saved for user: {current_user['uid']}")
                except Exception as firestore_error:
                    if "quota" in str(firestore_error).lower():
                        logger.warning(f"Firestore quota exceeded, conversation not saved: {firestore_error}")
                    else:
                        raise firestore_error
                        
            except Exception as e:
                logger.error(f"Failed to save conversation: {e}")
        
        return ChatResponse(
            message=ai_message,
            products=search_results['products'],
            bundles=search_results['bundles'],
            suggestions=search_results['suggestions'],
            search_metadata=search_results['search_metadata']
        )
        
    except Exception as e:
        logger.error(f"Chat message processing failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat message: {str(e)}"
        )

@router.get("/chat/stream")
async def stream_chat_response(
    query: str,
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user)
):
    """
    Stream AI chat response using Server-Sent Events
    
    Args:
        query: Search query
        current_user: Optional authenticated user
        
    Returns:
        StreamingResponse with real-time AI response
    """
    async def generate_response():
        try:
            # Send initial status
            yield {
                "event": "status",
                "data": json.dumps({"status": "processing", "message": "Analyzing your request..."})
            }
            
            await asyncio.sleep(0.5)  # Simulate processing time
            
            # Send search status
            yield {
                "event": "status", 
                "data": json.dumps({"status": "searching", "message": "Searching products..."})
            }
            
            # Process search
            search_results = await process_ai_search(query)
            
            await asyncio.sleep(0.5)
            
            # Send AI response
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "ai",
                    "content": search_results['ai_response'],
                    "timestamp": datetime.now().isoformat()
                })
            }
            
            # Send products
            if search_results['products']:
                yield {
                    "event": "products",
                    "data": json.dumps([product.dict() for product in search_results['products']])
                }
            
            # Send completion
            yield {
                "event": "complete",
                "data": json.dumps({"status": "complete", "suggestions": search_results['suggestions']})
            }
            
        except Exception as e:
            logger.error(f"Streaming response failed: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)})
            }
    
    return EventSourceResponse(generate_response())

@router.websocket("/chat/ws/{user_id}")
async def websocket_chat_endpoint(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for real-time chat
    
    Args:
        websocket: WebSocket connection
        user_id: User identifier
    """
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            logger.info(f"WebSocket message from {user_id}: {message_data}")
            
            # Process the message
            if message_data.get('type') == 'chat':
                query = message_data.get('message', '')
                
                # Send processing status
                await manager.send_personal_message({
                    "type": "status",
                    "status": "processing",
                    "message": "Processing your request..."
                }, user_id)
                
                # Process AI search
                search_results = await process_ai_search(query)
                
                # Send AI response
                await manager.send_personal_message({
                    "type": "ai_response",
                    "message": search_results['ai_response'],
                    "products": [product.dict() for product in search_results['products']],
                    "suggestions": search_results['suggestions'],
                    "timestamp": datetime.now().isoformat()
                }, user_id)
            
    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(user_id)

@router.get("/chat/history")
async def get_chat_history(
    limit: int = 10,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get chat history for authenticated user
    
    Args:
        limit: Maximum number of conversations to return
        current_user: Authenticated user
        
    Returns:
        List of recent conversations
    """
    try:
        conversations = (
            db.collection('conversations')
            .where('user_id', '==', current_user['uid'])
            .order_by('timestamp', direction='DESCENDING')
            .limit(limit)
            .stream()
        )
        
        history = []
        for conv in conversations:
            conv_data = conv.to_dict()
            history.append({
                'conversation_id': conv_data.get('conversation_id'),
                'query': conv_data.get('query'),
                'timestamp': conv_data.get('timestamp'),
                'products_found': conv_data.get('products_found', 0),
                'messages': conv_data.get('messages', [])
            })
        
        return {"history": history}
        
    except Exception as e:
        logger.error(f"Failed to get chat history: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve chat history"
        )

@router.delete("/chat/history/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete a specific conversation
    
    Args:
        conversation_id: Conversation to delete
        current_user: Authenticated user
        
    Returns:
        Success message
    """
    try:
        # Find and delete the conversation
        conversations = (
            db.collection('conversations')
            .where('user_id', '==', current_user['uid'])
            .where('conversation_id', '==', conversation_id)
            .stream()
        )
        
        deleted_count = 0
        for conv in conversations:
            conv.reference.delete()
            deleted_count += 1
        
        if deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found"
            )
        
        return {"message": f"Conversation {conversation_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete conversation: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete conversation"
        )