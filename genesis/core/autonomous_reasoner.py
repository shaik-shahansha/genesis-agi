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

Your task is to understand EXACTLY what the user wants. Be precise and literal.

DETECT REQUEST TYPE:
1. CREATION TASKS (create, generate, make, build document/presentation/report/file):
   - Intent: exactly what to create
   - Topic: what it's about
   - needs_internet: false (use existing knowledge)
   - approach: "code_only"
   - LLMs already know about most topics - no need to search!

2. RESEARCH TASKS (research, investigate, find information, search for, look up):
   - Intent: what to research
   - needs_internet: true
   - approach: "code_with_search"

3. ANALYSIS TASKS (analyze, examine, review files/data):
   - Intent: what to analyze
   - needs_internet: false
   - approach: "file_processing" or "code_only"

4. AUTOMATION TASKS (fill form, scrape website, extract data):
   - Intent: what to automate
   - approach: "browser" or "code_only"

Be smart: If user asks to "create document about X", they DON'T need internet research. Just create it using existing knowledge.

Extract:
1. Primary intent (EXACTLY what user wants - be literal)
2. Topic/subject (what it's about)
3. Output format (document, presentation, report, analysis, etc.)
4. Key requirements (specific details mentioned)
5. Approach (code_only, code_with_search, file_processing, browser)

Return ONLY this JSON (no other text):
{{
    "intent": "exact description of what to create/do",
    "topic": "subject matter",
    "output_format": "document|presentation|report|analysis|other",
    "output_filename": "suggested filename based on topic",
    "requirements": ["requirement1", "requirement2"],
    "suggested_approach": "code_only|code_with_search|file_processing|browser",
    "needs_internet": false,
    "complexity": "low|medium|high"
}}
"""
        
        response = await self.mind.think(prompt, skip_task_detection=True)
        
        try:
            # Try to parse JSON
            understanding = json.loads(response)
            
            # Ensure we have all required fields
            if "intent" not in understanding:
                understanding["intent"] = request
            if "topic" not in understanding:
                understanding["topic"] = request
            if "output_format" not in understanding:
                understanding["output_format"] = "other"
            if "output_filename" not in understanding:
                # Generate filename from topic
                topic = understanding.get("topic", "output")
                import re
                filename = re.sub(r'[^\w\s-]', '', topic.lower())
                filename = re.sub(r'[-\s]+', '_', filename)
                understanding["output_filename"] = filename[:50]
            if "suggested_approach" not in understanding:
                understanding["suggested_approach"] = "code_only"
            if "needs_internet" not in understanding:
                understanding["needs_internet"] = False
                
        except Exception as e:
            print(f"[ERROR reasoner] Failed to parse understanding: {e}")
            # Fallback if not valid JSON
            understanding = {
                "intent": request,
                "topic": request,
                "output_format": "other",
                "output_filename": "output",
                "requirements": [],
                "suggested_approach": "code_only",
                "needs_internet": False,
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
        
        # Check if this is a simple creation task that doesn't need research
        output_format = understanding.get("output_format", "other")
        needs_internet = understanding.get("needs_internet", False)
        approach = understanding.get("suggested_approach", "code_only")
        
        prompt = f"""Create a step-by-step execution plan for this task:

Task: {request}

Understanding:
{json.dumps(understanding, indent=2)}

Files available: {[f.name for f in available_files] if available_files else "None"}

Past similar solutions:
{json.dumps(past_solutions[:2], indent=2) if past_solutions else "None"}

INTELLIGENT PLANNING RULES:

1. CREATION TASKS (create/generate/make document/presentation/report):
   - Use ONLY "code_execution" step
   - DO NOT add "search" or "think" steps
   - LLMs have knowledge - just create the content directly
   - Example: "create document about AI" → ONE code_execution step

2. RESEARCH TASKS (research/investigate/find information):
   - Use "search" step to gather information
   - Then "code_execution" to compile results
   - Example: "research latest AI trends" → search + code_execution

3. ANALYSIS TASKS (analyze files/data):
   - Use "file_processing" if files attached
   - Use "code_execution" for analysis
   - Example: "analyze this CSV" → code_execution (with file)

4. WEB AUTOMATION (scrape/extract/fill forms):
   - Use "browser_task" for complex interactions
   - Use "code_execution" for simple API calls

KEEP IT SIMPLE: Most tasks need just ONE step!

Available step types:
- "code_execution": Generate and run Python code (USE THIS for documents, presentations, reports)
- "browser_task": Use browser automation (only if user wants to interact with websites)
- "file_processing": Process uploaded files (only if files are attached)
- "search": Search internet (ONLY if explicitly needed for research)
- "think": Deep reasoning/analysis (rarely needed)

For this task:
- Output format: {output_format}
- Needs internet: {needs_internet}
- Approach: {approach}

Return ONLY a JSON array of steps (no explanations, no markdown):
[
    {{
        "type": "code_execution",
        "description": "Generate {output_format} about {understanding.get('topic', 'the topic')}",
        "timeout": 90
    }}
]

Simpler is better. Most tasks need just ONE step.
"""
        
        try:
            response = await self.mind.think(prompt, skip_task_detection=True)
            print(f"[DEBUG reasoner] Plan generation response length: {len(response)}")
            print(f"[DEBUG reasoner] Response preview: {response[:200]}")
            
            if not response or len(response.strip()) == 0:
                print("[ERROR reasoner] Empty response from LLM for plan generation!")
                raise ValueError("Empty response from LLM")
            
            steps_data = json.loads(response)
            if not isinstance(steps_data, list):
                steps_data = [steps_data]
        except json.JSONDecodeError as e:
            print(f"[ERROR reasoner] Failed to parse plan as JSON: {e}")
            print(f"[ERROR reasoner] Response was: {response[:500]}")
            # Fallback: single code execution step
            steps_data = [{
                "type": "code_execution",
                "description": request,
                "timeout": 60
            }]
        except Exception as e:
            print(f"[ERROR reasoner] Plan generation failed: {e}")
            import traceback
            traceback.print_exc()
            # Fallback: single code execution step
            steps_data = [{
                "type": "code_execution",
                "description": request,
                "timeout": 120
            }]
        
        # INTELLIGENT FILTERING: Remove unnecessary steps based on request type
        # If this is a creation task (document, presentation, etc.) and doesn't need research,
        # filter out "search" and "think" steps that LLM might have added unnecessarily
        is_creation_task = output_format in ["document", "presentation", "report"]
        
        if is_creation_task and not needs_internet:
            print(f"[DEBUG reasoner] Creation task detected, filtering unnecessary steps")
            filtered_steps = []
            for step_data in steps_data:
                step_type = step_data.get("type", "code_execution")
                # Keep only code_execution and file_processing for creation tasks
                if step_type in ["code_execution", "file_processing"]:
                    filtered_steps.append(step_data)
                else:
                    print(f"[DEBUG reasoner] Filtered out unnecessary '{step_type}' step")
            steps_data = filtered_steps if filtered_steps else steps_data
        
        # Convert to ExecutionStep objects and inject understanding context
        steps = []
        for i, step_data in enumerate(steps_data):
            # Inject understanding context into each step so code generator has it
            step_context = {"understanding": understanding}
            
            step = ExecutionStep(
                step_id=f"step_{i+1}",
                type=StepType(step_data.get("type", "code_execution")),
                description=step_data.get("description", request),
                context=step_context,  # Pass understanding to code generator
                timeout=step_data.get("timeout", 90)
            )
            steps.append(step)
        
        # Ensure we have at least one step
        if not steps:
            print(f"[DEBUG reasoner] No steps after filtering, adding default code_execution step")
            steps = [
                ExecutionStep(
                    step_id="step_1",
                    type=StepType.CODE_EXECUTION,
                    description=request,
                    context={"understanding": understanding},
                    timeout=90
                )
            ]
        
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
