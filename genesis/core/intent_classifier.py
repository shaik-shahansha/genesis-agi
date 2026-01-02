"""
Intelligent Intent Classifier - LLM-first approach for maximum intelligence.

This is the brain that understands EVERYTHING about a user's request:
- What they want to do
- How to do it
- What to create
- Where to save it
- What format to use
- Related suggestions
- Context and metadata

One LLM call extracts all information for scalability and consistency.
"""

import json
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from genesis.core.mind import Mind


@dataclass
class IntentClassification:
    """Complete intent analysis with everything needed for execution."""
    
    # Core Classification
    is_task: bool
    task_type: str  # conversation, create_document, create_presentation, analyze_data, research, web_automation, code_generation, etc.
    confidence: float
    
    # User Intent
    intent: str  # Clear description of what user wants
    original_request: str
    
    # Immediate Response
    initial_response: str  # What to tell user immediately
    requires_background: bool  # Should this run in background?
    
    # Task Execution Details (if is_task=True)
    task_details: Dict[str, Any]  # Everything needed to execute
    
    # Suggestions & Enhancements
    suggestions: List[str]  # Additional helpful suggestions
    related_actions: List[str]  # Related things user might want
    
    # Metadata
    estimated_duration: int  # Estimated seconds
    complexity: str  # low, medium, high
    requires_internet: bool
    requires_files: bool
    
    # Context for Follow-up
    context: Dict[str, Any]  # Context for next interaction
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class IntelligentIntentClassifier:
    """
    LLM-powered intent classifier that understands EVERYTHING.
    
    This is like having Copilot/Manus AI level intelligence:
    - Understands ambiguous requests
    - Extracts all parameters automatically
    - Suggests improvements
    - Provides context-aware responses
    - Scalable and consistent
    """
    
    def __init__(self, mind: 'Mind'):
        """Initialize classifier with mind."""
        self.mind = mind
    
    async def classify(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict]] = None,
        user_email: Optional[str] = None
    ) -> IntentClassification:
        """
        Classify user intent and extract EVERYTHING needed.
        
        This is the magic method that understands the user completely.
        
        Args:
            user_message: What the user said
            conversation_history: Recent conversation context
            user_email: Who the user is
            
        Returns:
            Complete intent classification with all details
        """
        
        # Build comprehensive prompt
        prompt = self._build_classification_prompt(
            user_message,
            conversation_history or [],
            user_email
        )
        
        # Call LLM (use fast model for classification)
        response = await self.mind.orchestrator.generate(
            messages=[{"role": "user", "content": prompt}],
            model=self.mind.intelligence.fast_model,  # Use fast model
            temperature=0.3,  # Lower temp for consistent classification
            max_tokens=2000  # Enough for detailed response
        )
        
        # Parse response
        try:
            # Clean response (remove markdown code blocks if present)
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]  # Remove ```json
            if content.startswith("```"):
                content = content[3:]  # Remove ```
            if content.endswith("```"):
                content = content[:-3]  # Remove trailing ```
            content = content.strip()
            
            classification_data = json.loads(content)
            return self._parse_classification(classification_data, user_message)
        except json.JSONDecodeError as e:
            print(f"[INTENT] Failed to parse classification: {e}")
            print(f"[INTENT] Response: {response.content[:500]}")
            # Fallback to simple conversation
            return self._fallback_classification(user_message)
    
    def _build_classification_prompt(
        self,
        user_message: str,
        conversation_history: List[Dict],
        user_email: Optional[str]
    ) -> str:
        """Build comprehensive classification prompt."""
        
        # Recent history context
        history_context = ""
        if conversation_history:
            recent = conversation_history[-3:]
            history_context = "\n\nRecent conversation:\n"
            for msg in recent:
                role = msg.get("role", "user")
                content = msg.get("content", "")[:100]
                history_context += f"{role}: {content}...\n"
        
        prompt = f"""You are an intelligent intent classifier for a Copilot/Manus AI style autonomous agent.

Analyze this user message and extract EVERYTHING needed:

**User Message:** {user_message}

**User:** {user_email or "Anonymous"}{history_context}

**Your Task:** Understand the user's intent completely and extract ALL information.

**Classification Guidelines:**

1. **TASK Types** (requires code execution/background processing):
   - create_document: Word/PDF documents
   - create_presentation: PowerPoint/slides
   - create_spreadsheet: Excel/CSV files
   - analyze_data: Data analysis, charts, reports
   - research: Internet research, information gathering
   - web_automation: Scraping, form filling, browser tasks
   - code_generation: Writing code/scripts
   - file_processing: Converting, merging, editing files
   - email_automation: Sending emails, scheduling
   - mixed_task: Multiple actions combined

2. **CONVERSATION Types** (just respond):
   - question: User asking for information
   - greeting: Hello, hi, how are you
   - clarification: Asking for details
   - feedback: Comments about previous response
   - chitchat: Casual conversation

**Extract EVERYTHING:**

For TASKS, provide:
- Exact filename (with proper naming conventions)
- File format/extension
- Topic/subject matter
- Content structure/outline
- Number of slides/pages/sections
- Style/tone (formal, casual, technical)
- Target audience
- Any specific requirements mentioned
- Related resources/references

For DOCUMENTS:
- Suggested title
- Section headings
- Key points to cover
- Length estimate (pages)
- Format (APA, MLA, business, etc.)

For PRESENTATIONS:
- Number of slides (smart default: 5-8)
- Slide titles
- Key points per slide
- Image descriptions for each slide
- Suggested color scheme/template
- Speaker notes if needed

Be CREATIVE and HELPFUL:
- Suggest improvements user didn't ask for
- Provide related actions they might need
- Think ahead about what they'll need next

Return ONLY this JSON (no other text):
```json
{{
    "is_task": boolean,
    "task_type": "conversation|create_document|create_presentation|etc",
    "confidence": 0.0-1.0,
    "intent": "clear one-sentence description of what user wants",
    "original_request": "{user_message}",
    "initial_response": "what to tell user immediately (enthusiastic and helpful)",
    "requires_background": boolean,
    
    "task_details": {{
        "action": "specific action to take",
        "topic": "subject matter",
        "filename": "exact_filename_to_use",
        "file_format": "docx|pptx|xlsx|pdf|etc",
        "output_type": "document|presentation|spreadsheet|etc",
        
        "content_structure": {{
            "title": "document/presentation title",
            "sections": ["section1", "section2", ...],
            "slides": [
                {{
                    "number": 1,
                    "title": "slide title",
                    "content": "key points",
                    "image_description": "description for Pollinations.ai"
                }},
                ...
            ],
            "pages": 5,
            "key_points": ["point1", "point2", ...]
        }},
        
        "style": {{
            "tone": "formal|casual|technical",
            "audience": "target audience",
            "format": "business|academic|creative"
        }},
        
        "requires_internet": boolean,
        "requires_files": boolean,
        "uploaded_files": []
    }},
    
    "suggestions": [
        "You might also want to...",
        "I can also help you...",
        "Consider adding..."
    ],
    
    "related_actions": [
        "create_summary",
        "export_to_pdf",
        "schedule_presentation"
    ],
    
    "estimated_duration": 30,
    "complexity": "low|medium|high",
    "requires_internet": boolean,
    "requires_files": boolean,
    
    "context": {{
        "topic": "for follow-up",
        "next_steps": ["what might come next"],
        "clarifications_needed": []
    }}
}}
```

**Examples:**

Input: "create word doc for human digital twins with benefits"
Output:
```json
{{
    "is_task": true,
    "task_type": "create_document",
    "confidence": 1.0,
    "intent": "Create a Word document about human digital twins highlighting benefits",
    "initial_response": "I'll create a comprehensive document about human digital twins for you! This will include an overview, key benefits, applications, and future implications.",
    "requires_background": true,
    "task_details": {{
        "action": "create_word_document",
        "topic": "human digital twins and their benefits",
        "filename": "Human_Digital_Twins_Benefits",
        "file_format": "docx",
        "output_type": "document",
        "content_structure": {{
            "title": "Human Digital Twins: Benefits and Applications",
            "sections": [
                "Introduction to Human Digital Twins",
                "Key Benefits",
                "Healthcare Applications",
                "Personalized Medicine",
                "Predictive Health Monitoring",
                "Future Implications",
                "Conclusion"
            ],
            "pages": 4,
            "key_points": [
                "Personalized healthcare monitoring",
                "Predictive disease detection",
                "Treatment optimization",
                "Real-time health tracking",
                "Data-driven medical decisions"
            ]
        }},
        "style": {{
            "tone": "professional",
            "audience": "healthcare professionals and tech enthusiasts",
            "format": "informative report"
        }},
        "requires_internet": false,
        "requires_files": false
    }},
    "suggestions": [
        "Would you like me to also create a presentation version for sharing?",
        "I can add case studies and research citations if needed",
        "Consider creating an executive summary for quick reference"
    ],
    "related_actions": [
        "create_presentation_version",
        "generate_infographic",
        "create_executive_summary"
    ],
    "estimated_duration": 45,
    "complexity": "medium",
    "requires_internet": false,
    "requires_files": false,
    "context": {{
        "topic": "human_digital_twins",
        "next_steps": ["might ask for presentation", "might request more details"],
        "clarifications_needed": []
    }}
}}
```

Input: "hello"
Output:
```json
{{
    "is_task": false,
    "task_type": "greeting",
    "confidence": 1.0,
    "intent": "User is greeting",
    "initial_response": "Hello! I'm here to help you with any tasks or questions you have. What would you like to work on today?",
    "requires_background": false,
    "task_details": {{}},
    "suggestions": [
        "I can create documents, presentations, and reports",
        "Ask me to research topics or analyze data",
        "Need help with any projects?"
    ],
    "related_actions": [],
    "estimated_duration": 0,
    "complexity": "low",
    "requires_internet": false,
    "requires_files": false,
    "context": {{
        "next_steps": ["waiting for user request"]
    }}
}}
```

Now analyze the user's message and provide comprehensive classification."""
        
        return prompt
    
    def _parse_classification(
        self,
        data: Dict[str, Any],
        original_request: str
    ) -> IntentClassification:
        """Parse LLM response into IntentClassification object."""
        
        return IntentClassification(
            is_task=data.get("is_task", False),
            task_type=data.get("task_type", "conversation"),
            confidence=data.get("confidence", 0.5),
            intent=data.get("intent", original_request),
            original_request=original_request,
            initial_response=data.get("initial_response", "I understand your request."),
            requires_background=data.get("requires_background", False),
            task_details=data.get("task_details", {}),
            suggestions=data.get("suggestions", []),
            related_actions=data.get("related_actions", []),
            estimated_duration=data.get("estimated_duration", 30),
            complexity=data.get("complexity", "medium"),
            requires_internet=data.get("requires_internet", False),
            requires_files=data.get("requires_files", False),
            context=data.get("context", {})
        )
    
    def _fallback_classification(self, user_message: str) -> IntentClassification:
        """Fallback classification if LLM fails."""
        
        # Simple keyword-based detection as fallback
        is_task = any(keyword in user_message.lower() for keyword in [
            "create", "generate", "make", "build", "analyze", "research", "find"
        ])
        
        return IntentClassification(
            is_task=is_task,
            task_type="create_document" if is_task else "question",
            confidence=0.7,
            intent=user_message,
            original_request=user_message,
            initial_response="I'll help you with that!" if is_task else "Let me answer your question.",
            requires_background=is_task,
            task_details={"action": user_message} if is_task else {},
            suggestions=[],
            related_actions=[],
            estimated_duration=30,
            complexity="medium",
            requires_internet=False,
            requires_files=False,
            context={}
        )
