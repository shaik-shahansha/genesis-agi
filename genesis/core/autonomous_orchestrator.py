"""
Autonomous Orchestrator - Master controller for Genesis Minds.

This is the CORE of autonomous agent capabilities:
- Handles ANY user request without pre-built tools
- Generates code dynamically for tasks
- Uses browser automation when needed
- Processes uploaded files of any type
- Plans, executes, reflects, and learns

No hardcoded workflows - pure autonomous reasoning!
"""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from genesis.core.mind import Mind


class StepType(str, Enum):
    """Types of execution steps."""
    CODE_EXECUTION = "code_execution"
    BROWSER_TASK = "browser_task"
    FILE_PROCESSING = "file_processing"
    SEARCH = "search"
    THINK = "think"


@dataclass
class UploadedFile:
    """Represents a file uploaded by user."""
    id: str
    name: str
    path: Path
    mime_type: str
    size: int


@dataclass
class ExecutionStep:
    """Single step in task execution plan."""
    step_id: str
    type: StepType
    description: str
    context: Dict[str, Any]
    timeout: int = 60
    url: Optional[str] = None
    file_path: Optional[Path] = None
    data: Optional[Dict] = None
    result: Optional[Any] = None
    success: bool = False
    error: Optional[str] = None


@dataclass
class ExecutionPlan:
    """Complete execution plan for a task."""
    plan_id: str
    task: str
    steps: List[ExecutionStep]
    estimated_time: int
    confidence: float
    created_at: datetime


@dataclass
class TaskResult:
    """Result of task execution."""
    success: bool
    results: List[Any]
    artifacts: List[Dict[str, Any]]
    error: Optional[str] = None
    execution_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "results": self.results,
            "artifacts": self.artifacts,
            "error": self.error,
            "execution_time": self.execution_time
        }


class AutonomousOrchestrator:
    """
    Universal task solver using dynamic code generation.
    
    The HEART of Genesis autonomous capabilities.
    No pre-built tools - generates solutions on-the-fly!
    """
    
    def __init__(self, mind: 'Mind'):
        """
        Initialize orchestrator.
        
        Args:
            mind: The Mind this orchestrator belongs to
        """
        self.mind = mind
        
        # Lazy-load components to avoid circular imports
        self._code_generator = None
        self._code_executor = None
        self._browser_agent = None
        self._file_handler = None
        self._reasoner = None
        
    @property
    def code_generator(self):
        """Lazy-load code generator."""
        if self._code_generator is None:
            from genesis.core.code_generator import IntelligentCodeGenerator
            self._code_generator = IntelligentCodeGenerator(self.mind)
        return self._code_generator
    
    @property
    def code_executor(self):
        """Lazy-load code executor."""
        if self._code_executor is None:
            from genesis.core.code_executor import CodeExecutionEngine
            self._code_executor = CodeExecutionEngine(self.mind)
        return self._code_executor
    
    @property
    def browser_agent(self):
        """Lazy-load browser agent."""
        if self._browser_agent is None:
            # Try to use browser_use plugin if available
            plugin = self.mind.get_plugin("browser_use")
            if plugin:
                self._browser_agent = plugin
            else:
                # Fallback: create minimal browser agent
                from genesis.plugins.browser_use_plugin import BrowserUsePlugin
                self._browser_agent = BrowserUsePlugin()
                self._browser_agent.on_init(self.mind)
        return self._browser_agent
    
    @property
    def file_handler(self):
        """Lazy-load file handler."""
        if self._file_handler is None:
            from genesis.core.universal_file_handler import UniversalFileHandler
            self._file_handler = UniversalFileHandler(self.mind)
        return self._file_handler
    
    @property
    def reasoner(self):
        """Lazy-load reasoner."""
        if self._reasoner is None:
            from genesis.core.autonomous_reasoner import AutonomousReasoner
            self._reasoner = AutonomousReasoner(self.mind)
        return self._reasoner
    
    async def handle_request(
        self,
        user_request: str,
        uploaded_files: Optional[List[UploadedFile]] = None,
        context: Optional[Dict] = None
    ) -> TaskResult:
        """
        Handle ANY user request autonomously.
        
        This is the main entry point for autonomous task execution.
        
        Args:
            user_request: What the user wants
            uploaded_files: Files uploaded by user (optional)
            context: Additional context (conversation history, etc.)
            
        Returns:
            TaskResult with execution results and artifacts
            
        Examples:
            - "Find cheapest smart watch" → Web scraping code
            - "Analyze this CSV" → pandas + visualization code
            - "Fill this form with Excel data" → browser automation + pandas
            - "Generate presentation on AI" → python-pptx code
        """
        start_time = datetime.now()
        
        try:
            # Step 1: Understand request deeply
            self.mind.logger.action("orchestrator", f"Understanding request: {user_request}")
            understanding = await self.reasoner.understand_request(
                request=user_request,
                files=uploaded_files,
                context=context or {}
            )
            
            # Step 2: Search memory for similar past tasks
            self.mind.logger.action("orchestrator", "Searching for similar past solutions")
            similar_tasks = await self._search_similar_tasks(user_request)
            
            # Step 3: Generate execution plan
            self.mind.logger.action("orchestrator", "Generating execution plan")
            plan = await self.reasoner.create_plan(
                request=user_request,
                understanding=understanding,
                past_solutions=similar_tasks,
                available_files=uploaded_files
            )
            
            # Step 4: Execute plan step by step
            self.mind.logger.action("orchestrator", f"Executing {len(plan.steps)} steps")
            results = []
            
            for i, step in enumerate(plan.steps):
                self.mind.logger.action("orchestrator", f"Step {i+1}/{len(plan.steps)}: {step.description}")
                
                try:
                    if step.type == StepType.CODE_EXECUTION:
                        result = await self._execute_code_step(step, uploaded_files)
                    elif step.type == StepType.BROWSER_TASK:
                        result = await self._execute_browser_step(step)
                    elif step.type == StepType.FILE_PROCESSING:
                        result = await self._execute_file_step(step)
                    elif step.type == StepType.SEARCH:
                        result = await self._execute_search_step(step)
                    elif step.type == StepType.THINK:
                        result = await self._execute_think_step(step)
                    else:
                        result = {"error": f"Unknown step type: {step.type}"}
                        
                    step.result = result
                    step.success = True
                    results.append(result)
                    
                    # Update context for next step
                    if isinstance(result, dict):
                        step.context.update(result)
                    
                except Exception as e:
                    self.mind.logger.error("orchestrator_step", f"Step failed: {str(e)}")
                    step.error = str(e)
                    step.success = False
                    results.append({"error": str(e)})
                    
                    # Decide whether to continue or stop
                    if self._is_critical_step(step):
                        break
            
            # Step 5: Reflect and learn
            self.mind.logger.action("orchestrator", "Reflecting on execution")
            await self.reasoner.reflect_on_execution(
                task=user_request,
                plan=plan,
                results=results
            )
            
            # Step 6: Store successful solution
            if all(step.success for step in plan.steps):
                await self._store_solution(user_request, plan, results)
            
            # Collect artifacts (files, images, etc.)
            artifacts = self._collect_artifacts(results)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return TaskResult(
                success=all(step.success for step in plan.steps),
                results=results,
                artifacts=artifacts,
                execution_time=execution_time
            )
            
        except Exception as e:
            self.mind.logger.error("orchestrator_fatal", f"Fatal error: {str(e)}")
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return TaskResult(
                success=False,
                results=[],
                artifacts=[],
                error=str(e),
                execution_time=execution_time
            )
    
    async def _execute_code_step(
        self,
        step: ExecutionStep,
        uploaded_files: Optional[List[UploadedFile]]
    ) -> Dict[str, Any]:
        """Execute code generation and execution step."""
        
        # Generate code for this specific task
        code_result = await self.code_generator.generate_solution(
            task=step.description,
            context=step.context,
            files=uploaded_files
        )
        
        # Execute generated code
        exec_result = await self.code_executor.execute_code(
            code=code_result.source,
            language=code_result.language,
            timeout=step.timeout,
            files=[f.path for f in uploaded_files] if uploaded_files else None
        )
        
        return {
            "type": "code_execution",
            "generated_code": code_result.source,
            "execution_success": exec_result.success,
            "output": exec_result.stdout,
            "error": exec_result.stderr if not exec_result.success else None
        }
    
    async def _execute_browser_step(self, step: ExecutionStep) -> Dict[str, Any]:
        """Execute browser automation step."""
        
        result = await self.browser_agent.solve_browser_task(
            objective=step.description,
            starting_url=step.url,
            data=step.data
        )
        
        return {
            "type": "browser_task",
            "success": result.success,
            "extracted_data": result.extracted_data,
            "final_url": result.final_url
        }
    
    async def _execute_file_step(self, step: ExecutionStep) -> Dict[str, Any]:
        """Execute file processing step."""
        
        result = await self.file_handler.process_file(
            file_path=step.file_path,
            user_request=step.description
        )
        
        return {
            "type": "file_processing",
            "file_type": result.file_type,
            "data": result.data,
            "summary": result.summary
        }
    
    async def _execute_search_step(self, step: ExecutionStep) -> Dict[str, Any]:
        """Execute internet search step."""
        
        # Use Perplexity search if available
        try:
            from genesis.integrations.perplexity_search import PerplexitySearch
            search = PerplexitySearch(api_key=self.mind.intelligence.api_keys.get("perplexity"))
            result = await search.search(step.description)
            
            return {
                "type": "search",
                "query": step.description,
                "results": result
            }
        except Exception as e:
            # Fallback: ask LLM to search (it has internet access via some providers)
            result = await self.mind.think(f"Search the internet for: {step.description}")
            
            return {
                "type": "search",
                "query": step.description,
                "results": result
            }
    
    async def _execute_think_step(self, step: ExecutionStep) -> Dict[str, Any]:
        """Execute thinking/reasoning step."""
        
        result = await self.mind.think(step.description)
        
        return {
            "type": "think",
            "thought": result
        }
    
    async def _search_similar_tasks(self, task: str) -> List[Dict]:
        """Search memory for similar past tasks."""
        try:
            # Search procedural memory for similar solutions
            results = await self.mind.memory.search(
                query=task,
                memory_type="procedural",
                k=3
            )
            return results
        except Exception as e:
            self.mind.logger.error("orchestrator_search", f"Could not search similar tasks: {e}")
            return []
    
    async def _store_solution(
        self,
        task: str,
        plan: ExecutionPlan,
        results: List[Any]
    ):
        """Store successful solution in procedural memory."""
        try:
            await self.mind.memory.add_procedural_memory(
                context=f"Successfully completed task: {task}",
                content=json.dumps({
                    "task": task,
                    "plan": {
                        "steps": [{"type": s.type, "description": s.description} for s in plan.steps]
                    },
                    "success": True
                }),
                metadata={
                    "task_type": "autonomous_execution",
                    "steps_count": len(plan.steps),
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            self.mind.logger.error("orchestrator_storage", f"Could not store solution: {e}")
    
    def _is_critical_step(self, step: ExecutionStep) -> bool:
        """Determine if step failure should stop execution."""
        # For now, all steps are critical
        # Future: add continue_on_error flag
        return True
    
    def _collect_artifacts(self, results: List[Any]) -> List[Dict[str, Any]]:
        """Collect generated artifacts (files, images, etc.) from results."""
        artifacts = []
        
        for result in results:
            if isinstance(result, dict):
                # Check for file paths in results
                if "file_path" in result:
                    artifacts.append({
                        "type": "file",
                        "path": result["file_path"],
                        "name": Path(result["file_path"]).name
                    })
                
                # Check for generated images
                if "image_url" in result:
                    artifacts.append({
                        "type": "image",
                        "url": result["image_url"]
                    })
        
        return artifacts
