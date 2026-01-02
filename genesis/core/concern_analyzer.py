"""
LLM-Based Concern Analyzer for Proactive Consciousness

Uses LLM to intelligently detect and analyze concerns from conversation:
- Health issues (fever, sick, pain, etc.)
- Emotional distress (stressed, anxious, sad, etc.)
- Time-bound tasks with deadlines
- Relationship issues
- Any other matters requiring follow-up

Much more accurate and context-aware than regex patterns.
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ConcernAnalysis:
    """Result of analyzing a conversation for concerns."""
    has_concern: bool
    concern_type: str  # health, emotion, task, relationship, financial, personal, none
    confidence: float  # 0.0-1.0
    
    # Concern details
    description: str
    severity: str  # low, moderate, high, critical
    urgency: str  # low, normal, high, critical
    
    # Task-specific
    has_deadline: bool = False
    deadline_text: Optional[str] = None
    deadline_datetime: Optional[str] = None  # ISO format
    estimated_duration: Optional[str] = None
    
    # Follow-up details
    requires_followup: bool = True
    suggested_followup_hours: float = 6.0
    followup_message: str = ""
    
    # Context
    extracted_details: Dict[str, Any] = None
    user_emotion: Optional[str] = None
    
    def __post_init__(self):
        if self.extracted_details is None:
            self.extracted_details = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class LLMConcernAnalyzer:
    """
    Intelligent LLM-based concern detection and analysis.
    
    Replaces regex patterns with contextual understanding.
    """
    
    def __init__(self, mind: 'Mind'):
        """Initialize analyzer with mind."""
        self.mind = mind
    
    async def analyze_conversation(
        self,
        conversation_text: str,
        user_email: Optional[str] = None,
        conversation_context: Optional[str] = None
    ) -> ConcernAnalysis:
        """
        Analyze conversation for concerns requiring follow-up.
        
        Args:
            conversation_text: The conversation to analyze
            user_email: Who the user is (for context)
            conversation_context: Additional context
            
        Returns:
            ConcernAnalysis with all detected details
        """
        
        prompt = self._build_analysis_prompt(conversation_text, user_email, conversation_context)
        
        # Use fast model for quick analysis
        try:
            response = await self.mind.orchestrator.generate(
                messages=[{"role": "user", "content": prompt}],
                model=self.mind.intelligence.fast_model,
                temperature=0.3,  # Lower for consistent analysis
                max_tokens=1500
            )
            
            # Parse JSON response
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            data = json.loads(content)
            
            # Parse deadline if present
            if data.get("has_deadline") and data.get("deadline_datetime"):
                try:
                    # Keep as ISO string for now, will parse when creating concern
                    data["deadline_datetime"] = data["deadline_datetime"]
                except:
                    data["deadline_datetime"] = None
            
            return ConcernAnalysis(**{k: v for k, v in data.items() if k in ConcernAnalysis.__annotations__})
            
        except json.JSONDecodeError as e:
            logger.warning(f"[CONCERN] Failed to parse LLM response: {e}")
            logger.debug(f"[CONCERN] Response: {response.content[:500]}")
            return self._fallback_analysis(conversation_text)
        except Exception as e:
            logger.error(f"[CONCERN] Error analyzing conversation: {e}")
            return self._fallback_analysis(conversation_text)
    
    def _build_analysis_prompt(
        self,
        conversation_text: str,
        user_email: Optional[str],
        conversation_context: Optional[str]
    ) -> str:
        """Build comprehensive analysis prompt."""
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        prompt = f"""You are an empathetic AI analyzing conversations to identify matters requiring follow-up.

**Current Time:** {current_time}

**Conversation to Analyze:**
{conversation_text}

**User:** {user_email or "Unknown"}
{f"**Context:** {conversation_context}" if conversation_context else ""}

**Your Task:** Determine if this conversation contains ANY concern, issue, or task that would benefit from proactive follow-up.

**Concern Types:**
1. **health**: Physical health issues (fever, sick, pain, injury, medical, etc.)
2. **emotion**: Emotional distress (stressed, anxious, sad, worried, depressed, etc.)
3. **task**: Things user needs to do, especially with deadlines
4. **relationship**: Relationship problems or conflicts
5. **financial**: Money concerns, bills, financial stress
6. **personal**: Other personal matters needing support
7. **none**: No follow-up needed

**Response Format (JSON only, no markdown):**

{{
    "has_concern": boolean,
    "concern_type": "health|emotion|task|relationship|financial|personal|none",
    "confidence": 0.0-1.0,
    
    "description": "brief description of the concern",
    "severity": "low|moderate|high|critical",
    "urgency": "low|normal|high|critical",
    
    "has_deadline": boolean,
    "deadline_text": "original text about deadline (if any)",
    "deadline_datetime": "ISO format datetime (if deadline can be parsed)",
    "estimated_duration": "how long task might take (if task)",
    
    "requires_followup": boolean,
    "suggested_followup_hours": number (when to check in),
    "followup_message": "suggested message to send when checking in",
    
    "extracted_details": {{
        "symptom": "if health issue",
        "emotion_mentioned": "if emotional issue",
        "task_description": "if task",
        "time_constraint": "any time pressure mentioned"
    }},
    
    "user_emotion": "detected emotional state"
}}

**Guidelines:**

1. **Health Concerns**: ANY mention of illness, pain, symptoms → requires follow-up
   - "I have fever" → high severity, check in 6 hours
   - "Not feeling well" → moderate severity, check in 4 hours
   - "Bad headache" → moderate severity, check in 3 hours

2. **Emotional Concerns**: Stress, anxiety, sadness → requires empathetic follow-up
   - "Really stressed" → moderate severity, check in 3 hours
   - "Feeling depressed" → high severity, check in 2 hours
   - "So anxious" → moderate severity, check in 3 hours

3. **Tasks with Deadlines**: Parse time expressions intelligently
   - "in 5 minutes" → critical urgency, deadline = now + 5 min, check in 2 min
   - "in 2 hours" → high urgency, deadline = now + 2 hours, check in 1 hour
   - "by tonight" → high urgency, deadline = today 6 PM, check in 3 hours
   - "by tomorrow" → normal urgency, deadline = tomorrow 6 PM, check in 12 hours
   - "next week" → low urgency, deadline = next week, check in 2 days

4. **Severity Mapping**:
   - **critical**: Immediate danger or <1 hour deadline
   - **high**: Significant concern or <6 hour deadline
   - **moderate**: Notable issue or <24 hour deadline
   - **low**: Minor concern or >24 hour deadline

5. **Follow-up Timing**:
   - Critical: 0.05-0.5 hours (3-30 minutes)
   - High: 0.5-3 hours
   - Moderate: 3-6 hours
   - Low: 6-24 hours

**Examples:**

Input: "I have a bad fever and headache"
Output:
```json
{{
    "has_concern": true,
    "concern_type": "health",
    "confidence": 0.95,
    "description": "User has fever and headache",
    "severity": "high",
    "urgency": "high",
    "has_deadline": false,
    "deadline_text": null,
    "deadline_datetime": null,
    "estimated_duration": null,
    "requires_followup": true,
    "suggested_followup_hours": 6.0,
    "followup_message": "Hey, how are you feeling now? Did your fever go down? Hope you got some rest!",
    "extracted_details": {{
        "symptom": "fever and headache",
        "severity_mentioned": "bad"
    }},
    "user_emotion": "unwell"
}}
```

Input: "I have to finish the office work in 5 mins"
Output:
```json
{{
    "has_concern": true,
    "concern_type": "task",
    "confidence": 0.98,
    "description": "User needs to finish office work urgently",
    "severity": "critical",
    "urgency": "critical",
    "has_deadline": true,
    "deadline_text": "in 5 mins",
    "deadline_datetime": "{(datetime.now() + timedelta(minutes=5)).isoformat()}",
    "estimated_duration": "5 minutes",
    "requires_followup": true,
    "suggested_followup_hours": 0.1,
    "followup_message": "Hey! Did you manage to finish your office work? Hope it went well!",
    "extracted_details": {{
        "task_description": "finish office work",
        "time_constraint": "5 minutes",
        "urgency_keyword": "have to"
    }},
    "user_emotion": "stressed/pressured"
}}
```

Input: "Feeling really stressed about my project deadline tomorrow"
Output:
```json
{{
    "has_concern": true,
    "concern_type": "task",
    "confidence": 0.90,
    "description": "User stressed about project deadline tomorrow",
    "severity": "high",
    "urgency": "high",
    "has_deadline": true,
    "deadline_text": "tomorrow",
    "deadline_datetime": "{(datetime.now() + timedelta(days=1)).replace(hour=18, minute=0).isoformat()}",
    "estimated_duration": "unknown",
    "requires_followup": true,
    "suggested_followup_hours": 8.0,
    "followup_message": "How's the project going? Remember to take breaks! You've got this!",
    "extracted_details": {{
        "task_description": "project",
        "emotion_mentioned": "stressed",
        "time_constraint": "tomorrow"
    }},
    "user_emotion": "stressed"
}}
```

Input: "What's the weather like?"
Output:
```json
{{
    "has_concern": false,
    "concern_type": "none",
    "confidence": 1.0,
    "description": "Casual question about weather",
    "severity": "low",
    "urgency": "low",
    "has_deadline": false,
    "deadline_text": null,
    "deadline_datetime": null,
    "estimated_duration": null,
    "requires_followup": false,
    "suggested_followup_hours": 0,
    "followup_message": "",
    "extracted_details": {{}},
    "user_emotion": "neutral"
}}
```

Now analyze the conversation above and provide your response."""

        return prompt
    
    def _fallback_analysis(self, text: str) -> ConcernAnalysis:
        """Fallback analysis if LLM fails."""
        # Simple keyword-based fallback
        text_lower = text.lower()
        
        has_health = any(word in text_lower for word in ['fever', 'sick', 'pain', 'hurt', 'ill', 'headache'])
        has_emotion = any(word in text_lower for word in ['stressed', 'anxious', 'sad', 'depressed', 'worried'])
        has_task = any(word in text_lower for word in ['have to', 'need to', 'must', 'deadline', 'urgent'])
        
        if has_health:
            concern_type = "health"
            severity = "moderate"
        elif has_emotion:
            concern_type = "emotion"
            severity = "moderate"
        elif has_task:
            concern_type = "task"
            severity = "moderate"
        else:
            concern_type = "none"
            severity = "low"
        
        return ConcernAnalysis(
            has_concern=has_health or has_emotion or has_task,
            concern_type=concern_type,
            confidence=0.6,
            description=f"Detected {concern_type} concern",
            severity=severity,
            urgency="normal",
            requires_followup=has_health or has_emotion or has_task,
            suggested_followup_hours=6.0,
            followup_message="Checking in with you...",
            extracted_details={"text": text[:100]}
        )
