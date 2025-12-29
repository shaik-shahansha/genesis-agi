"""
Autonomous Reasoner - Planning, reflection, and learning.

The "thinking brain" that:
- Understands user requests
- Creates execution plans
- Reflects on results
- Learns from experience
"""

import json
import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from genesis.core.mind import Mind
    from genesis.core.autonomous_orchestrator import UploadedFile, ExecutionPlan, ExecutionStep, StepType


class AutonomousReasoner:
    """
    Multi-step planning with reflection and learning.
    
    This is NOT hardcoded workflows - it's genuine reasoning!
    """
    
    def __init__(self, mind: 'Mind'):
        """Initialize reasoner."""
        self.mind = mind
    
    async def understand_request(
        self,
        request: str,
        files: Optional[List['UploadedFile']],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Deeply understand user's intent.
        
        Returns:
            Understanding dict with intent, entities, requirements
        """
        
        prompt = f"""Analyze this user request and extract key information:

Request: {request}

Files attached: {[f.name for f in files] if files else "None"}

Context: {json.dumps(context, indent=2)}

Extract:
1. Primary intent (what does user want to achieve?)
2. Key entities (people, products, topics, etc.)
3. Requirements (specific constraints, formats, etc.)
4. Approach (code generation, browser, search, file processing?)

Return JSON:
{{
    "intent": "brief description",
    "entities": ["entity1", "entity2"],
    "requirements": ["req1", "req2"],
    "suggested_approach": ["code", "browser", "search", "file_processing"],
    "complexity": "low|medium|high"
}}
"""
        
        response = await self.mind.think(prompt)
        
        try:
            # Try to parse JSON
            understanding = json.loads(response)
        except Exception:
            # Fallback if not valid JSON
            understanding = {
                "intent": request,
                "entities": [],
                "requirements": [],
                "suggested_approach": ["code"],
                "complexity": "medium"
            }
        
        return understanding
    
    async def create_plan(
        self,
        request: str,
        understanding: Dict[str, Any],
        past_solutions: List[Dict],
        available_files: Optional[List['UploadedFile']]
    ) -> 'ExecutionPlan':
        """
        Generate execution plan with steps.
        
        Returns:
            ExecutionPlan with ordered steps
        """
        from genesis.core.autonomous_orchestrator import ExecutionPlan, ExecutionStep, StepType
        
        prompt = f"""Create a step-by-step execution plan for this task:

Task: {request}

Understanding:
{json.dumps(understanding, indent=2)}

Files available: {[f.name for f in available_files] if available_files else "None"}

Past similar solutions:
{json.dumps(past_solutions[:2], indent=2) if past_solutions else "None"}

Create a plan with these step types:
- "code_execution": Generate and run Python code
- "browser_task": Use browser automation
- "file_processing": Process uploaded files
- "search": Search the internet
- "think": Deep reasoning/analysis

Return JSON array of steps:
[
    {{
        "type": "step_type",
        "description": "what this step does",
        "timeout": 60,
        "dependencies": []
    }},
    ...
]

Make the plan efficient and logical. Typically 1-5 steps.
"""
        
        response = await self.mind.think(prompt)
        
        try:
            steps_data = json.loads(response)
            if not isinstance(steps_data, list):
                steps_data = [steps_data]
        except Exception:
            # Fallback: single code execution step
            steps_data = [{
                "type": "code_execution",
                "description": request,
                "timeout": 60
            }]
        
        # Convert to ExecutionStep objects
        steps = []
        for i, step_data in enumerate(steps_data):
            step = ExecutionStep(
                step_id=f"step_{i+1}",
                type=StepType(step_data.get("type", "code_execution")),
                description=step_data.get("description", request),
                context={},
                timeout=step_data.get("timeout", 60)
            )
            steps.append(step)
        
        plan_id = f"PLAN-{secrets.token_hex(6).upper()}"
        
        return ExecutionPlan(
            plan_id=plan_id,
            task=request,
            steps=steps,
            estimated_time=sum(s.timeout for s in steps),
            confidence=0.8,
            created_at=datetime.now()
        )
    
    async def reflect_on_execution(
        self,
        task: str,
        plan: 'ExecutionPlan',
        results: List[Any]
    ):
        """
        Reflect on execution and learn.
        
        Stores insights in memory for future improvement.
        """
        
        # Analyze success/failure
        success_count = sum(1 for step in plan.steps if step.success)
        total_steps = len(plan.steps)
        
        reflection = f"""Task: {task}
Plan ID: {plan.plan_id}
Steps: {success_count}/{total_steps} successful

"""
        
        # Add insights about what worked/failed
        for i, step in enumerate(plan.steps):
            if step.success:
                reflection += f"✓ Step {i+1}: {step.description}\n"
            else:
                reflection += f"✗ Step {i+1}: {step.description} - Error: {step.error}\n"
        
        # Store reflection in memory
        try:
            await self.mind.memory.add_episodic_memory(
                context=f"Task execution reflection: {task}",
                content=reflection,
                metadata={
                    "type": "execution_reflection",
                    "success_rate": success_count / total_steps if total_steps > 0 else 0,
                    "plan_id": plan.plan_id
                }
            )
        except Exception as e:
            self.mind.logger.warning(f"Could not store reflection: {e}")
