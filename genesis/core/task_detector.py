"""
Task Detector - Identifies actionable tasks vs conversational queries.

Determines if user input requires background execution or just a conversational response.
"""

import re
from typing import Dict, Any
from enum import Enum


class TaskType(str, Enum):
    """Types of tasks that can be detected."""
    CREATE = "create"
    ANALYZE = "analyze"
    SEARCH = "search"
    PROCESS = "process"
    AUTOMATE = "automate"
    RESEARCH = "research"
    CONVERSATION = "conversation"


class TaskDetector:
    """
    Detects whether user input is an actionable task or conversation.
    
    Examples:
    - "create presentation on digital twins" -> TASK (create)
    - "analyze this CSV file" -> TASK (analyze)
    - "how are you?" -> CONVERSATION
    - "tell me about AI" -> CONVERSATION
    """
    
    def __init__(self):
        """Initialize task detector with patterns."""
        
        # Task keywords by type
        self.task_patterns = {
            TaskType.CREATE: [
                r'\b(create|make|build|generate|design|develop|produce|construct)\b',
                r'\b(presentation|document|report|chart|graph|spreadsheet|code|app|website)\b'
            ],
            TaskType.ANALYZE: [
                r'\b(analyze|analyse|examine|review|inspect|evaluate|assess|study)\b',
                r'\b(data|file|csv|excel|document|image|video)\b'
            ],
            TaskType.SEARCH: [
                r'\b(search|find|look up|discover|locate|research)\b',
                r'\b(internet|web|online|google|information)\b'
            ],
            TaskType.PROCESS: [
                r'\b(process|convert|transform|extract|parse|import|export)\b',
                r'\b(file|data|image|video|audio|document)\b'
            ],
            TaskType.AUTOMATE: [
                r'\b(automate|schedule|recurring|repeat|batch|bulk)\b',
                r'\b(task|process|workflow|job)\b'
            ],
            TaskType.RESEARCH: [
                r'\b(research|investigate|explore|compare|summarize)\b',
                r'\b(topic|subject|information|data|options)\b'
            ]
        }
        
        # Conversational indicators (negative signals)
        self.conversation_patterns = [
            r'^\s*(hi|hello|hey|greetings|good morning|good afternoon|good evening)\b',
            r'\b(how are you|what\'s up|how\'s it going)\b',
            r'\b(thank you|thanks|appreciate)\b',
            r'^\s*(who|what|when|where|why|how)\s+(are|is|was|were|do|does|did)\b',
            r'\b(tell me about|explain|describe|what is|who is)\b',
            r'\b(can you|could you|would you|will you)\s+(help|assist|tell|explain|describe)\b'
        ]
        
        # Internal LLM reasoning patterns (should ALWAYS skip task detection)
        self.internal_llm_patterns = [
            r'^\s*analyze\s+this\s+user\s+request',
            r'^\s*create\s+a\s+step-by-step\s+(execution\s+)?plan',
            r'^\s*brainstorm\s+(the|overall)',
            r'^\s*generate\s+python\s+code\s+to\s+accomplish',
            r'^\s*this\s+python\s+code\s+has\s+syntax\s+errors',
            r'^\s*fix\s+(them|the\s+following|these\s+errors)',
            r'^\s*review\s+(the|this)\s+(code|output|result)',
            r'^\s*extract\s+key\s+information',
            r'request:\s*\n.*\n.*task:',  # Multi-line internal prompts
            r'```python[\s\S]*```.*fix',  # Code blocks with fix instructions
        ]
    
    def detect(self, user_input: str) -> Dict[str, Any]:
        """
        Detect if input is a task or conversation.
        
        Args:
            user_input: User's input text
            
        Returns:
            Dict with:
            - is_task: bool
            - task_type: TaskType
            - confidence: float (0-1)
            - reasoning: str
        """
        user_input_lower = user_input.lower()
        
        # CRITICAL: Check for internal LLM reasoning first (highest priority)
        # These are internal orchestrator prompts that should NEVER trigger tasks
        for pattern in self.internal_llm_patterns:
            if re.search(pattern, user_input_lower, re.IGNORECASE | re.MULTILINE):
                return {
                    "is_task": False,
                    "task_type": TaskType.CONVERSATION,
                    "confidence": 1.0,
                    "reasoning": "Internal LLM reasoning prompt - skip task detection"
                }
        
        # Check for conversation patterns
        for pattern in self.conversation_patterns:
            if re.search(pattern, user_input_lower, re.IGNORECASE):
                return {
                    "is_task": False,
                    "task_type": TaskType.CONVERSATION,
                    "confidence": 0.9,
                    "reasoning": "Detected as conversational question"
                }
        
        # Check for task patterns
        best_match = None
        best_score = 0
        
        for task_type, patterns in self.task_patterns.items():
            score = 0
            matches = 0
            
            for pattern in patterns:
                if re.search(pattern, user_input_lower, re.IGNORECASE):
                    matches += 1
                    score += 0.5
            
            # Bonus if multiple patterns match
            if matches >= 2:
                score += 0.2
            
            if score > best_score:
                best_score = score
                best_match = task_type
        
        # Determine if it's a task
        if best_score >= 0.5:
            return {
                "is_task": True,
                "task_type": best_match.value,
                "confidence": min(best_score, 1.0),
                "reasoning": f"Detected {best_match.value} task with {int(best_score/0.5)} keyword matches"
            }
        else:
            # Default to conversation if no strong task signals
            return {
                "is_task": False,
                "task_type": TaskType.CONVERSATION,
                "confidence": 0.7,
                "reasoning": "No strong task indicators, treating as conversation"
            }
    
    def should_use_orchestrator(self, user_input: str) -> bool:
        """
        Quick check if orchestrator should be used.
        
        Returns True if the input likely requires autonomous orchestration.
        """
        detection = self.detect(user_input)
        return detection["is_task"] and detection["confidence"] >= 0.7
