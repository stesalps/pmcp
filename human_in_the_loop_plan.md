# Human-in-the-Loop Chat Integration Plan

## Overview

This plan outlines the implementation of a human-in-the-loop chat system that can work with both Google's local models and the Ollama setup. The system will allow human operators to review, modify, and approve AI-generated responses before they are sent to the user.

## Architecture

The human-in-the-loop system will consist of the following components:

1. **Chat Router**: Routes messages between users, AI models, and human operators
2. **Model Adapter**: Provides a unified interface for different AI models (Google, Ollama)
3. **Human Review Interface**: GUI and API for human operators to review and modify responses
4. **Message Queue**: Manages pending messages awaiting human review
5. **Notification System**: Alerts human operators when messages need review

## Core Components

### 1. Chat Router

```python
class ChatRouter:
    def __init__(self, model_adapter, human_review_enabled=True, auto_approve_threshold=0.8):
        self.model_adapter = model_adapter
        self.human_review_enabled = human_review_enabled
        self.auto_approve_threshold = auto_approve_threshold
        self.message_queue = MessageQueue()
        self.notification_system = NotificationSystem()
    
    async def process_message(self, user_id, message, conversation_id=None):
        """Process an incoming user message."""
        # Generate AI response
        ai_response, confidence = await self.model_adapter.generate_response(message, conversation_id)
        
        if not self.human_review_enabled or confidence >= self.auto_approve_threshold:
            # Auto-approve high-confidence responses
            return ai_response
        
        # Queue for human review
        review_id = self.message_queue.add_message(
            user_id=user_id,
            message=message,
            ai_response=ai_response,
            confidence=confidence,
            conversation_id=conversation_id
        )
        
        # Notify human operators
        self.notification_system.notify_new_message(review_id)
        
        # Return a temporary response
        return {"status": "pending_review", "review_id": review_id}
    
    async def get_pending_reviews(self, limit=10):
        """Get pending messages awaiting human review."""
        return self.message_queue.get_pending_messages(limit)
    
    async def submit_human_review(self, review_id, approved, modified_response=None):
        """Submit human review for a message."""
        message = self.message_queue.get_message(review_id)
        if not message:
            return {"error": "Message not found"}
        
        final_response = modified_response if modified_response else message["ai_response"]
        
        # Update message status
        self.message_queue.update_message(
            review_id=review_id,
            status="approved" if approved else "rejected",
            final_response=final_response
        )
        
        # If approved, send the response to the user
        if approved:
            # In a real implementation, this would send the response to the user
            pass
        
        return {"status": "success", "approved": approved}
```

### 2. Model Adapter

```python
class ModelAdapter:
    def __init__(self, default_model="google", google_model="google/gemini-2.5-pro", ollama_model="llama3"):
        self.default_model = default_model
        self.google_model = google_model
        self.ollama_model = ollama_model
        
        # Initialize Google models
        try:
            from google.colab import ai
            self.google_ai_available = True
        except ImportError:
            self.google_ai_available = False
        
        # Initialize Ollama
        try:
            import requests
            self.ollama_available = True
            self.ollama_url = "http://localhost:11434/api/generate"
        except ImportError:
            self.ollama_available = False
    
    async def generate_response(self, message, conversation_id=None, model_type=None):
        """Generate a response using the specified model."""
        model = model_type or self.default_model
        
        if model == "google" and self.google_ai_available:
            return await self._generate_google_response(message, conversation_id)
        elif model == "ollama" and self.ollama_available:
            return await self._generate_ollama_response(message, conversation_id)
        else:
            # Fallback to available model
            if self.google_ai_available:
                return await self._generate_google_response(message, conversation_id)
            elif self.ollama_available:
                return await self._generate_ollama_response(message, conversation_id)
            else:
                return "No AI models available", 0.0
    
    async def _generate_google_response(self, message, conversation_id=None):
        """Generate a response using Google's models."""
        try:
            from google.colab import ai
            
            # In a real implementation, we would include conversation history
            response = ai.generate_text(message, model_name=self.google_model)
            
            # For demonstration, we're using a fixed confidence
            confidence = 0.9
            
            return response, confidence
        except Exception as e:
            return f"Error generating response: {str(e)}", 0.0
    
    async def _generate_ollama_response(self, message, conversation_id=None):
        """Generate a response using Ollama."""
        try:
            import requests
            import json
            
            # Prepare the request
            payload = {
                "model": self.ollama_model,
                "prompt": message,
                "stream": False
            }
            
            # Send the request
            response = requests.post(self.ollama_url, json=payload)
            response_json = response.json()
            
            # Extract the response text
            response_text = response_json.get("response", "")
            
            # For demonstration, we're using a fixed confidence
            confidence = 0.8
            
            return response_text, confidence
        except Exception as e:
            return f"Error generating response: {str(e)}", 0.0
    
    def list_available_models(self):
        """List all available models."""
        models = []
        
        if self.google_ai_available:
            try:
                from google.colab import ai
                google_models = ai.list_models()
                models.extend([{"name": model, "type": "google"} for model in google_models])
            except:
                pass
        
        if self.ollama_available:
            try:
                import requests
                response = requests.get("http://localhost:11434/api/tags")
                ollama_models = response.json().get("models", [])
                models.extend([{"name": model["name"], "type": "ollama"} for model in ollama_models])
            except:
                pass
        
        return models
```

### 3. Message Queue

```python
class MessageQueue:
    def __init__(self):
        self.messages = {}
        self.next_id = 1
    
    def add_message(self, user_id, message, ai_response, confidence, conversation_id=None):
        """Add a message to the queue."""
        review_id = str(self.next_id)
        self.next_id += 1
        
        self.messages[review_id] = {
            "user_id": user_id,
            "message": message,
            "ai_response": ai_response,
            "confidence": confidence,
            "conversation_id": conversation_id,
            "status": "pending",
            "created_at": time.time(),
            "final_response": None
        }
        
        return review_id
    
    def get_message(self, review_id):
        """Get a message by ID."""
        return self.messages.get(review_id)
    
    def update_message(self, review_id, status, final_response=None):
        """Update a message's status and final response."""
        if review_id in self.messages:
            self.messages[review_id]["status"] = status
            if final_response:
                self.messages[review_id]["final_response"] = final_response
            self.messages[review_id]["updated_at"] = time.time()
            return True
        return False
    
    def get_pending_messages(self, limit=10):
        """Get pending messages awaiting review."""
        pending = [
            {"review_id": review_id, **message}
            for review_id, message in self.messages.items()
            if message["status"] == "pending"
        ]
        
        # Sort by creation time (oldest first)
        pending.sort(key=lambda x: x["created_at"])
        
        return pending[:limit]
```

### 4. Notification System

```python
class NotificationSystem:
    def __init__(self):
        self.subscribers = []
    
    def subscribe(self, callback):
        """Subscribe to notifications."""
        self.subscribers.append(callback)
    
    def notify_new_message(self, review_id):
        """Notify subscribers of a new message."""
        for callback in self.subscribers:
            try:
                callback({"type": "new_message", "review_id": review_id})
            except Exception as e:
                print(f"Error notifying subscriber: {e}")
```

## User Interface Components

### 1. Human Review GUI

```python
def create_human_review_gui(chat_router):
    """Create a GUI for human review of AI responses."""
    import ipywidgets as widgets
    from IPython.display import display, HTML, clear_output
    
    # Header
    header = widgets.HTML(
        value="<h2>🧠 Human-in-the-Loop Review Interface</h2>"
    )
    
    # Pending messages list
    pending_list = widgets.Select(
        options=[],
        description='Pending:',
        disabled=False,
        layout=widgets.Layout(width='100%', height='150px')
    )
    
    # Message details
    user_message = widgets.HTML(
        value="<p><strong>User Message:</strong> Select a message to review</p>"
    )
    
    ai_response = widgets.Textarea(
        value='',
        placeholder='AI response will appear here. You can edit it.',
        description='AI Response:',
        disabled=False,
        layout=widgets.Layout(width='100%', height='150px')
    )
    
    confidence = widgets.HTML(
        value="<p><strong>Confidence:</strong> N/A</p>"
    )
    
    # Action buttons
    approve_button = widgets.Button(
        description='Approve',
        disabled=True,
        button_style='success',
        tooltip='Approve this response',
        icon='check'
    )
    
    reject_button = widgets.Button(
        description='Reject',
        disabled=True,
        button_style='danger',
        tooltip='Reject this response',
        icon='times'
    )
    
    refresh_button = widgets.Button(
        description='Refresh',
        disabled=False,
        button_style='info',
        tooltip='Refresh the pending list',
        icon='refresh'
    )
    
    status = widgets.HTML(
        value="<p>Ready to review messages.</p>"
    )
    
    # Output area for debugging
    output = widgets.Output()
    
    # Layout
    buttons = widgets.HBox([approve_button, reject_button, refresh_button])
    details = widgets.VBox([user_message, ai_response, confidence, buttons, status])
    main_ui = widgets.VBox([header, pending_list, details, output])
    
    # Current review ID
    current_review_id = None
    
    # Event handlers
    async def refresh_pending_list(b=None):
        with output:
            clear_output()
            print("Refreshing pending messages...")
        
        pending_messages = await chat_router.get_pending_reviews()
        
        options = []
        for message in pending_messages:
            user_msg = message["message"]
            if len(user_msg) > 30:
                user_msg = user_msg[:30] + "..."
            options.append((f"{message['review_id']}: {user_msg}", message["review_id"]))
        
        pending_list.options = options
        
        with output:
            print(f"Found {len(pending_messages)} pending messages.")
    
    async def on_pending_selection(change):
        nonlocal current_review_id
        
        if not change["new"]:
            return
        
        review_id = change["new"]
        current_review_id = review_id
        
        with output:
            clear_output()
            print(f"Loading message {review_id}...")
        
        message = chat_router.message_queue.get_message(review_id)
        
        if not message:
            with output:
                print(f"Message {review_id} not found.")
            return
        
        user_message.value = f"<p><strong>User Message:</strong> {message['message']}</p>"
        ai_response.value = message["ai_response"]
        confidence.value = f"<p><strong>Confidence:</strong> {message['confidence']:.2f}</p>"
        
        approve_button.disabled = False
        reject_button.disabled = False
        
        with output:
            print(f"Loaded message {review_id}.")
    
    async def on_approve_clicked(b):
        if not current_review_id:
            return
        
        with output:
            clear_output()
            print(f"Approving message {current_review_id}...")
        
        result = await chat_router.submit_human_review(
            review_id=current_review_id,
            approved=True,
            modified_response=ai_response.value
        )
        
        status.value = f"<p>✅ Approved message {current_review_id}.</p>"
        approve_button.disabled = True
        reject_button.disabled = True
        
        await refresh_pending_list()
    
    async def on_reject_clicked(b):
        if not current_review_id:
            return
        
        with output:
            clear_output()
            print(f"Rejecting message {current_review_id}...")
        
        result = await chat_router.submit_human_review(
            review_id=current_review_id,
            approved=False
        )
        
        status.value = f"<p>❌ Rejected message {current_review_id}.</p>"
        approve_button.disabled = True
        reject_button.disabled = True
        
        await refresh_pending_list()
    
    # Connect event handlers
    pending_list.observe(on_pending_selection, names='value')
    approve_button.on_click(lambda b: asyncio.create_task(on_approve_clicked(b)))
    reject_button.on_click(lambda b: asyncio.create_task(on_reject_clicked(b)))
    refresh_button.on_click(lambda b: asyncio.create_task(refresh_pending_list(b)))
    
    # Initial refresh
    asyncio.create_task(refresh_pending_list())
    
    return main_ui
```

### 2. API Endpoints for Human Review

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

app = FastAPI()

# Models
class ReviewSubmission(BaseModel):
    review_id: str
    approved: bool
    modified_response: Optional[str] = None

class ReviewResponse(BaseModel):
    status: str
    approved: Optional[bool] = None
    error: Optional[str] = None

# Endpoints
@app.get("/api/reviews/pending")
async def get_pending_reviews(limit: int = 10):
    """Get pending messages awaiting human review."""
    try:
        # In a real implementation, this would use the chat_router
        pending_messages = await chat_router.get_pending_reviews(limit)
        return {"reviews": pending_messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reviews/submit", response_model=ReviewResponse)
async def submit_review(submission: ReviewSubmission):
    """Submit a human review for a message."""
    try:
        result = await chat_router.submit_human_review(
            review_id=submission.review_id,
            approved=submission.approved,
            modified_response=submission.modified_response
        )
        
        if "error" in result:
            return {"status": "error", "error": result["error"]}
        
        return {"status": "success", "approved": submission.approved}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Integration with Existing System

### 1. Box 2 Modifications (Model Integration)

Add the following code to Box 2 to support model switching:

```python
# Model adapter for unified access to Google and Ollama models
class ModelAdapter:
    def __init__(self, default_model_type="google"):
        self.default_model_type = default_model_type
        self.google_model = default_model
        self.ollama_model = "llama3"  # Default Ollama model
        self.ollama_url = "http://localhost:11434/api/generate"
    
    async def generate_response(self, prompt, model_type=None, stream=False):
        model_type = model_type or self.default_model_type
        
        if model_type == "google" and GOOGLE_AI_AVAILABLE:
            return await self._generate_google_response(prompt, stream)
        elif model_type == "ollama":
            return await self._generate_ollama_response(prompt, stream)
        else:
            # Fallback
            if GOOGLE_AI_AVAILABLE:
                return await self._generate_google_response(prompt, stream)
            else:
                return await self._generate_ollama_response(prompt, stream)
    
    async def _generate_google_response(self, prompt, stream=False):
        try:
            if stream:
                return generate_text(prompt, self.google_model, stream=True)
            else:
                return generate_text(prompt, self.google_model)
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    async def _generate_ollama_response(self, prompt, stream=False):
        try:
            import requests
            import json
            
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": stream
            }
            
            if stream:
                # Streaming implementation
                async def stream_response():
                    response = requests.post(self.ollama_url, json=payload, stream=True)
                    for line in response.iter_lines():
                        if line:
                            data = json.loads(line)
                            yield data.get("response", "")
                
                return stream_response()
            else:
                # Non-streaming implementation
                response = requests.post(self.ollama_url, json=payload)
                response_json = response.json()
                return response_json.get("response", "")
        except Exception as e:
            return f"Error generating response: {str(e)}"

# Initialize the model adapter
model_adapter = ModelAdapter(default_model_type="google" if GOOGLE_AI_AVAILABLE else "ollama")
```

### 2. Box 4 Modifications (User Interface)

Add the following to Box 4 to support model switching in the UI:

```python
# Model selection dropdown
model_type_dropdown = widgets.Dropdown(
    options=[
        ("Google", "google"),
        ("Ollama", "ollama")
    ],
    value="google" if GOOGLE_AI_AVAILABLE else "ollama",
    description='Model Type:',
    disabled=False,
    style={'description_width': '100px'}
)

# Human review toggle
human_review_toggle = widgets.Checkbox(
    value=True,
    description='Enable Human Review',
    disabled=False
)

# Add to the main UI
model_controls = widgets.HBox([model_dropdown, model_type_dropdown, human_review_toggle])
main_ui = widgets.VBox([header, model_controls, tab])
```

### 3. Box 5 Modifications (API)

Add the following to Box 5 to support human-in-the-loop via API:

```python
# Human-in-the-loop chat endpoint
@app.post("/api/chat/human-review")
async def api_chat_with_review(request: ChatRequest):
    try:
        # Generate AI response
        ai_response = await chat(
            message=request.message,
            conversation_id=request.conversation_id,
            model_name=request.model_name
        )
        
        # Queue for human review
        review_id = chat_router.message_queue.add_message(
            user_id=request.user_id if hasattr(request, "user_id") else "anonymous",
            message=request.message,
            ai_response=ai_response,
            confidence=0.7,  # Example confidence
            conversation_id=request.conversation_id
        )
        
        # Notify human operators
        chat_router.notification_system.notify_new_message(review_id)
        
        return {
            "status": "pending_review",
            "review_id": review_id,
            "message": "Your message is being reviewed by a human operator."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Implementation Plan

### Phase 1: Core Components
1. Implement the `ModelAdapter` class to support both Google and Ollama models
2. Implement the `MessageQueue` and `NotificationSystem` classes
3. Implement the `ChatRouter` class to manage message flow

### Phase 2: User Interface
1. Create the human review GUI using Jupyter widgets
2. Add model selection controls to the main UI
3. Implement the human review toggle

### Phase 3: API Integration
1. Add API endpoints for human review
2. Implement the human-in-the-loop chat endpoint
3. Add webhook support for external notifications

### Phase 4: Testing and Refinement
1. Test with both Google and Ollama models
2. Test the human review workflow
3. Optimize performance and fix any issues

## Conclusion

The human-in-the-loop chat system will enhance the Manus-like system by allowing human operators to review and modify AI-generated responses. This will improve response quality, reduce errors, and provide a safety mechanism for sensitive or complex queries. The system is designed to work with both Google's local models and the Ollama setup, providing flexibility and redundancy.