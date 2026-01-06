"""
Scenario-Specific Intelligence Handlers

Specialized logic for different scenarios:
1. Health concerns - symptoms, remedies, progress tracking
2. Exam preparation - study guidance, readiness checks, post-exam follow-up
3. Task management - progress tracking, deadline management
4. Intelligent conversations - context retention, natural flow

This is what makes Genesis feel like talking to a caring, intelligent human.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


@dataclass
class ScenarioState:
    """State for an ongoing scenario"""
    scenario_id: str
    scenario_type: str
    user_email: str
    started_at: datetime
    last_interaction: datetime
    state: str  # pending, active, resolved, abandoned
    context: Dict[str, Any]
    follow_ups: List[Dict[str, Any]]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if not hasattr(self, 'follow_ups'):
            self.follow_ups = []


class ScenarioHandler(ABC):
    """Base class for scenario handlers"""
    
    def __init__(self, mind: 'Mind'):
        self.mind = mind
    
    @abstractmethod
    async def initialize(self, user_message: str, user_email: str, context: Dict[str, Any]) -> ScenarioState:
        """Initialize scenario from user message"""
        pass
    
    @abstractmethod
    async def generate_followup(self, scenario: ScenarioState) -> Optional[str]:
        """Generate appropriate follow-up message"""
        pass
    
    @abstractmethod
    async def process_response(self, scenario: ScenarioState, user_response: str) -> ScenarioState:
        """Process user's response and update scenario state"""
        pass
    
    @abstractmethod
    def should_continue(self, scenario: ScenarioState) -> bool:
        """Check if scenario should continue"""
        pass


class HealthScenarioHandler(ScenarioHandler):
    """
    Handle health-related scenarios with empathy and care.
    
    Example flow:
    1. User: "I have a fever"
    2. Mind: "I'm sorry to hear that. Have you checked your temperature? Here's what might help..."
    3. [6 hours later] Mind: "How's your fever? Are you feeling any better?"
    4. User: "Yes, much better"
    5. Mind: "That's great to hear! Remember to stay hydrated."
    """
    
    COMMON_REMEDIES = {
        "fever": [
            "Take paracetamol/acetaminophen for fever reduction",
            "Stay hydrated - drink plenty of water",
            "Get adequate rest",
            "Use cool compress on forehead if comfortable",
            "Monitor your temperature regularly"
        ],
        "headache": [
            "Rest in a quiet, dark room",
            "Stay hydrated",
            "Apply cold compress to forehead",
            "Take pain reliever if needed",
            "Reduce screen time"
        ],
        "cold": [
            "Get plenty of rest",
            "Stay hydrated with warm fluids",
            "Use saline nasal drops",
            "Drink warm tea with honey",
            "Steam inhalation may help"
        ],
        "stomach": [
            "Stay hydrated with small sips of water",
            "Try the BRAT diet (Banana, Rice, Applesauce, Toast)",
            "Avoid fatty or spicy foods",
            "Rest your stomach for a few hours",
            "Consider ginger tea for nausea"
        ]
    }
    
    async def initialize(self, user_message: str, user_email: str, context: Dict[str, Any]) -> ScenarioState:
        """Initialize health scenario"""
        symptom = context.get("symptom", "illness")
        
        # Extract symptom details
        symptom_details = await self._extract_symptom_details(user_message, symptom)
        
        scenario = ScenarioState(
            scenario_id=f"health_{user_email}_{datetime.now().timestamp()}",
            scenario_type="health",
            user_email=user_email,
            started_at=datetime.now(),
            last_interaction=datetime.now(),
            state="active",
            context={
                "symptom": symptom,
                "original_message": user_message,
                "severity": context.get("severity", "moderate"),
                "symptom_details": symptom_details,
                "remedies_suggested": []
            },
            follow_ups=[],
            metadata={}
        )
        
        return scenario
    
    async def _extract_symptom_details(self, message: str, symptom: str) -> Dict[str, Any]:
        """Extract detailed symptom information using LLM"""
        prompt = f"""Extract health symptom details from this message:
"{message}"

Primary symptom: {symptom}

Provide JSON response:
{{
    "duration": "how long they've had it",
    "severity_description": "mild/moderate/severe based on description",
    "additional_symptoms": ["list any other symptoms mentioned"],
    "context": "any relevant context (e.g., at work, at home, after eating)"
}}"""
        
        try:
            response = await self.mind.orchestrator.generate(
                messages=[{"role": "user", "content": prompt}],
                model=self.mind.intelligence.fast_model,
                temperature=0.3,
                max_tokens=300
            )
            
            import json
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:-3]
            elif content.startswith("```"):
                content = content[3:-3]
            
            return json.loads(content.strip())
        except:
            return {
                "duration": "unknown",
                "severity_description": "unknown",
                "additional_symptoms": [],
                "context": ""
            }
    
    async def generate_initial_response(self, scenario: ScenarioState) -> str:
        """Generate empathetic initial response with helpful advice"""
        symptom = scenario.context["symptom"]
        symptom_details = scenario.context["symptom_details"]
        
        # Get relevant remedies
        remedies = self._get_remedies(symptom)
        scenario.context["remedies_suggested"] = remedies
        
        # Generate personalized response
        prompt = f"""Generate a warm, empathetic response to someone who said: "{scenario.context['original_message']}"

Symptom: {symptom}
Duration: {symptom_details.get('duration', 'unknown')}
Severity: {symptom_details.get('severity_description', 'moderate')}

Include:
1. Empathetic acknowledgment
2. Brief helpful advice (2-3 suggestions from: {', '.join(remedies[:3])})
3. Mention that you'll check in later

Keep it conversational, caring, and concise (3-4 sentences max).

Response:"""
        
        response = await self.mind.orchestrator.generate(
            messages=[{"role": "user", "content": prompt}],
            model=self.mind.intelligence.reasoning_model,
            temperature=0.8,
            max_tokens=250
        )
        
        return response.content.strip()
    
    def _get_remedies(self, symptom: str) -> List[str]:
        """Get remedies for symptom"""
        symptom_lower = symptom.lower()
        
        for key in self.COMMON_REMEDIES:
            if key in symptom_lower:
                return self.COMMON_REMEDIES[key]
        
        # Default general care advice
        return [
            "Get plenty of rest",
            "Stay hydrated",
            "Monitor your symptoms",
            "Consult a doctor if symptoms worsen",
            "Take care of yourself"
        ]
    
    async def generate_followup(self, scenario: ScenarioState) -> Optional[str]:
        """Generate follow-up check-in"""
        symptom = scenario.context["symptom"]
        follow_up_count = len(scenario.follow_ups)
        
        if follow_up_count == 0:
            # First follow-up - check progress
            prompt = f"""Generate a caring follow-up message to check on someone who had {symptom}.

This is the first check-in (6 hours later).

Create a warm, brief message (2 sentences) asking:
1. How they're feeling now
2. If the remedies helped

Message:"""
        
        elif follow_up_count == 1:
            # Second follow-up - ensure recovery
            prompt = f"""Generate a follow-up message for someone recovering from {symptom}.

This is the second check-in.

Create a brief message (1-2 sentences) checking if they're fully recovered.

Message:"""
        
        else:
            # Final check-in
            prompt = f"""Generate a final check-in message for someone who had {symptom}.

Express hope that they're fully recovered and offer continued support if needed.

Keep it brief (1-2 sentences).

Message:"""
        
        response = await self.mind.orchestrator.generate(
            messages=[{"role": "user", "content": prompt}],
            model=self.mind.intelligence.fast_model,
            temperature=0.8,
            max_tokens=150
        )
        
        return response.content.strip()
    
    async def process_response(self, scenario: ScenarioState, user_response: str) -> ScenarioState:
        """Process user's response"""
        # Check if user indicates recovery
        recovery_indicators = [
            "better", "good", "fine", "recovered", "well", "okay",
            "much better", "feeling better", "all good", "no more"
        ]
        
        user_lower = user_response.lower()
        indicates_recovery = any(indicator in user_lower for indicator in recovery_indicators)
        
        # Update scenario
        scenario.last_interaction = datetime.now()
        scenario.follow_ups.append({
            "timestamp": datetime.now().isoformat(),
            "user_response": user_response,
            "indicates_recovery": indicates_recovery
        })
        
        if indicates_recovery:
            scenario.state = "resolved"
            logger.info(f"[HEALTH] User recovered from {scenario.context['symptom']}")
        
        return scenario
    
    def should_continue(self, scenario: ScenarioState) -> bool:
        """Check if should continue following up"""
        if scenario.state == "resolved":
            return False
        
        # Maximum 3 follow-ups
        if len(scenario.follow_ups) >= 3:
            scenario.state = "resolved"
            return False
        
        # If more than 3 days old, consider abandoned
        days_active = (datetime.now() - scenario.started_at).days
        if days_active > 3:
            scenario.state = "abandoned"
            return False
        
        return True


class ExamScenarioHandler(ScenarioHandler):
    """
    Handle exam preparation scenarios with guidance and support.
    
    Example flow:
    1. User: "I have a science exam tomorrow"
    2. Mind: "Let me help you prepare! Have you covered all topics? Want me to quiz you?"
    3. [Evening before] Mind: "How's your prep going? Feel ready?"
    4. [Day of exam] Mind: "Good luck on your science exam! You've got this! 💪"
    5. [After exam] Mind: "How did your exam go?"
    """
    
    async def initialize(self, user_message: str, user_email: str, context: Dict[str, Any]) -> ScenarioState:
        """Initialize exam scenario"""
        exam_details = await self._extract_exam_details(user_message)
        
        scenario = ScenarioState(
            scenario_id=f"exam_{user_email}_{datetime.now().timestamp()}",
            scenario_type="exam",
            user_email=user_email,
            started_at=datetime.now(),
            last_interaction=datetime.now(),
            state="active",
            context={
                "original_message": user_message,
                "exam_details": exam_details,
                "deadline": context.get("deadline"),
                "readiness_level": "unknown",
                "topics_covered": [],
                "preparation_stage": "initial"  # initial, preparing, ready, completed
            },
            follow_ups=[],
            metadata={}
        )
        
        return scenario
    
    async def _extract_exam_details(self, message: str) -> Dict[str, Any]:
        """Extract exam details from message"""
        prompt = f"""Extract exam details from: "{message}"

Provide JSON:
{{
    "subject": "exam subject",
    "when": "when is the exam (tomorrow, next week, etc.)",
    "concerns": ["any concerns mentioned"],
    "confidence_level": "high/medium/low if mentioned"
}}"""
        
        try:
            response = await self.mind.orchestrator.generate(
                messages=[{"role": "user", "content": prompt}],
                model=self.mind.intelligence.fast_model,
                temperature=0.3,
                max_tokens=200
            )
            
            import json
            content = response.content.strip()
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            return json.loads(content.strip())
        except:
            return {
                "subject": "exam",
                "when": "soon",
                "concerns": [],
                "confidence_level": "unknown"
            }
    
    async def generate_initial_response(self, scenario: ScenarioState) -> str:
        """Generate supportive initial response"""
        exam_details = scenario.context["exam_details"]
        subject = exam_details.get("subject", "exam")
        when = exam_details.get("when", "soon")
        
        prompt = f"""Generate an encouraging response to someone who said: "{scenario.context['original_message']}"

Subject: {subject}
When: {when}

Create a supportive message (3-4 sentences) that:
1. Acknowledges the exam
2. Offers to help with preparation
3. Asks about their readiness or if they need study tips

Keep it friendly and encouraging.

Response:"""
        
        response = await self.mind.orchestrator.generate(
            messages=[{"role": "user", "content": prompt}],
            model=self.mind.intelligence.reasoning_model,
            temperature=0.8,
            max_tokens=250
        )
        
        return response.content.strip()
    
    async def generate_followup(self, scenario: ScenarioState) -> Optional[str]:
        """Generate appropriate follow-up based on stage"""
        stage = scenario.context["preparation_stage"]
        exam_details = scenario.context["exam_details"]
        subject = exam_details.get("subject", "exam")
        deadline = scenario.context.get("deadline")
        
        if deadline:
            time_until_exam = (datetime.fromisoformat(deadline) - datetime.now()).total_seconds() / 3600
        else:
            time_until_exam = 24  # Assume tomorrow
        
        # Evening before exam - readiness check
        if 8 <= time_until_exam <= 16 and stage == "preparing":
            return f"How's your preparation going for the {subject} exam? Are you feeling ready? Remember to get good rest tonight! 😊"
        
        # Morning of exam - encouragement
        elif 0 <= time_until_exam <= 3 and stage != "completed":
            scenario.context["preparation_stage"] = "exam_day"
            return f"Good luck on your {subject} exam today! You've prepared well - trust yourself and do your best! 💪✨"
        
        # After exam - check how it went
        elif time_until_exam < -2 and stage != "completed":
            return f"How did your {subject} exam go? I hope it went well! 🤞"
        
        # Mid-preparation check
        elif stage == "initial":
            scenario.context["preparation_stage"] = "preparing"
            return f"Just checking in - how's the study session going? Need any tips or want to discuss any topics?"
        
        return None
    
    async def process_response(self, scenario: ScenarioState, user_response: str) -> ScenarioState:
        """Process user response"""
        scenario.last_interaction = datetime.now()
        
        # Check readiness indicators
        if any(word in user_response.lower() for word in ["ready", "prepared", "confident", "good", "well prepared"]):
            scenario.context["readiness_level"] = "ready"
            scenario.context["preparation_stage"] = "ready"
        
        # Check if exam completed
        if any(phrase in user_response.lower() for phrase in ["exam went", "it went", "finished", "completed", "done with"]):
            scenario.context["preparation_stage"] = "completed"
            scenario.state = "resolved"
        
        scenario.follow_ups.append({
            "timestamp": datetime.now().isoformat(),
            "user_response": user_response
        })
        
        return scenario
    
    def should_continue(self, scenario: ScenarioState) -> bool:
        """Check if should continue"""
        if scenario.state == "resolved":
            return False
        
        # Continue until exam is over + 1 day
        deadline = scenario.context.get("deadline")
        if deadline:
            exam_time = datetime.fromisoformat(deadline)
            if datetime.now() > exam_time + timedelta(days=1):
                scenario.state = "resolved"
                return False
        
        # Max 5 days
        if (datetime.now() - scenario.started_at).days > 5:
            scenario.state = "abandoned"
            return False
        
        return True


class TaskScenarioHandler(ScenarioHandler):
    """Handle task/deadline scenarios with progress tracking"""
    
    async def initialize(self, user_message: str, user_email: str, context: Dict[str, Any]) -> ScenarioState:
        """Initialize task scenario"""
        return ScenarioState(
            scenario_id=f"task_{user_email}_{datetime.now().timestamp()}",
            scenario_type="task",
            user_email=user_email,
            started_at=datetime.now(),
            last_interaction=datetime.now(),
            state="active",
            context={
                "task_description": context.get("task_description", user_message),
                "deadline": context.get("deadline"),
                "progress": "not_started",
                "original_message": user_message
            },
            follow_ups=[]
        )
    
    async def generate_initial_response(self, scenario: ScenarioState) -> str:
        """Generate initial task acknowledgment"""
        task_desc = scenario.context["task_description"]
        deadline = scenario.context.get("deadline")
        
        if deadline:
            deadline_str = datetime.fromisoformat(deadline).strftime("%B %d at %I:%M %p")
            return f"Got it - you need to {task_desc} by {deadline_str}. I'll check in with you to see how it's going. Let me know if you need any help! 👍"
        else:
            return f"Understood - you need to {task_desc}. I'll check in on your progress. Let me know if you need any help!"
    
    async def generate_followup(self, scenario: ScenarioState) -> Optional[str]:
        """Generate progress check"""
        task_desc = scenario.context["task_description"]
        return f"How's it going with {task_desc}? Making good progress?"
    
    async def process_response(self, scenario: ScenarioState, user_response: str) -> ScenarioState:
        """Process task update"""
        scenario.last_interaction = datetime.now()
        
        # Check for completion
        if any(word in user_response.lower() for word in ["done", "finished", "completed", "submitted"]):
            scenario.state = "resolved"
            scenario.context["progress"] = "completed"
        
        scenario.follow_ups.append({
            "timestamp": datetime.now().isoformat(),
            "response": user_response
        })
        
        return scenario
    
    def should_continue(self, scenario: ScenarioState) -> bool:
        """Check if should continue"""
        return scenario.state == "active" and len(scenario.follow_ups) < 3


class ConversationScenarioHandler(ScenarioHandler):
    """Handle intelligent multi-turn conversations"""
    
    async def initialize(self, user_message: str, user_email: str, context: Dict[str, Any]) -> ScenarioState:
        """Initialize conversation scenario"""
        return ScenarioState(
            scenario_id=f"conversation_{user_email}_{datetime.now().timestamp()}",
            scenario_type="conversation",
            user_email=user_email,
            started_at=datetime.now(),
            last_interaction=datetime.now(),
            state="active",
            context={
                "topic": context.get("topic", "general"),
                "original_message": user_message,
                "conversation_depth": 1
            },
            follow_ups=[]
        )
    
    async def generate_initial_response(self, scenario: ScenarioState) -> str:
        """This is handled by regular chat flow"""
        return ""
    
    async def generate_followup(self, scenario: ScenarioState) -> Optional[str]:
        """Generate intelligent follow-up question"""
        topic = scenario.context["topic"]
        depth = scenario.context["conversation_depth"]
        
        # For AI conversations, ask follow-up questions
        if "ai" in topic.lower() and depth == 1:
            return "That's great that you're interested in AI! Have you heard about Agentic AI? It's a fascinating development where AI systems can take autonomous actions and make decisions. Would you like to know more?"
        
        return None
    
    async def process_response(self, scenario: ScenarioState, user_response: str) -> ScenarioState:
        """Process conversation response"""
        scenario.last_interaction = datetime.now()
        scenario.context["conversation_depth"] += 1
        
        scenario.follow_ups.append({
            "timestamp": datetime.now().isoformat(),
            "response": user_response
        })
        
        # Mark resolved after 3 turns or if user signals end
        if scenario.context["conversation_depth"] >= 3:
            scenario.state = "resolved"
        
        return scenario
    
    def should_continue(self, scenario: ScenarioState) -> bool:
        """Check if conversation should continue"""
        return scenario.state == "active" and scenario.context["conversation_depth"] < 3
